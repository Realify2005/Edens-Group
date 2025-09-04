import os
import time
import json
import urllib.parse
import requests
import psycopg2
from psycopg2.extras import execute_values
from backend.config import get_settings
from urllib.parse import urlparse

# --- CONFIG ---
# DATABASE_URL = settings.heroku_postgresql_database_url
settings = get_settings()
DATABASE_URL = settings.local_postgresql_database_url
PROVIDER = settings.geocode_provider
API_KEY = settings.geocode_api_key

# Rate limiting: adjust to provider policy
REQUESTS_PER_SEC = 1.0
SLEEP = 1.0 / REQUESTS_PER_SEC
MAX_TRIES = 4

# ---------- utilities ----------

def _norm(x):
    """Return a trimmed string or None."""
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None

def _join_query(*parts, country="Australia"):
    """Join non-empty parts plus country into a geocoding query."""
    clean = [_norm(p) for p in parts]
    clean = [p for p in clean if p]
    if not clean:
        return None
    return ", ".join(clean + [country])

def build_query(address, suburb, state, postcode, country="Australia"):
    """
    Original 'richest' query builder (kept for clarity).
    Returns None if nothing usable.
    """
    return _join_query(address, suburb, state, postcode, country=country)

def geocode_mapbox(q):
    """
    Mapbox geocoding with retries. Returns (lat, lon, raw_json) or (None, None, raw_json).
    """
    if not API_KEY:
        # Early failure with a clear message
        return None, None, {"error": "GEOCODE_API_KEY not set for Mapbox"}

    for attempt in range(1, MAX_TRIES + 1):
        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{urllib.parse.quote(q)}.json"
            params = {"access_token": API_KEY, "limit": 1, "country": "AU"}  # bias to AU
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()

            feats = data.get("features", [])
            if feats:
                # Mapbox returns center = [lon, lat]
                center = feats[0].get("center", [])
                if len(center) == 2:
                    lat = float(center[1])
                    lon = float(center[0])
                    return lat, lon, data

            # No result
            return None, None, data

        except requests.RequestException as e:
            if attempt == MAX_TRIES:
                return None, None, {"error": str(e)}
            # simple backoff
            time.sleep(1.5 * attempt)
        finally:
            time.sleep(SLEEP)

def geocode_with_fallbacks(address, suburb, state, postcode):
    """
    Try progressively looser queries:
      1) address, suburb, state, postcode
      2) suburb, state, postcode
      3) suburb, state
      4) postcode, state
      5) state
    Returns (lat, lon, raw_json) or (None, None, raw_json).
    """
    # Normalize inputs (postcode may be int)
    address = _norm(address)
    suburb  = _norm(suburb)
    state   = _norm(state)
    postcode = _norm(postcode)

    candidates = [
        _join_query(address, suburb, state, postcode),
        _join_query(suburb, state, postcode),
        _join_query(suburb, state),
        _join_query(postcode, state),
        _join_query(state),
    ]

    for q in candidates:
        if not q:
            continue
        lat, lon, raw = geocode_mapbox(q)
        if lat is not None and lon is not None:
            return lat, lon, raw

    return None, None, {"note": "no result after fallbacks"}


def _should_require_ssl(db_url: str) -> bool:
    host = urlparse(db_url).hostname or ""
    # Require SSL for hosted DBs; disable for localhost/dev
    hosted_markers = ("amazonaws.com", "heroku", "render.com", "supabase", "neon.tech", "timescaledb.io")
    return any(m in host for m in hosted_markers)

# ---------- main workflow ----------

def main():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    if PROVIDER != "mapbox":
        raise RuntimeError(f"This script is configured for Mapbox only. PROVIDER={PROVIDER}")

    if _should_require_ssl(DATABASE_URL):
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        conn = psycopg2.connect(DATABASE_URL, sslmode="disable")
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1) Fetch rows needing geocode, but only if they have some address signal
        cur.execute("""
            SELECT id, address, suburb, state, postcode, address_key
            FROM service_search_view
            WHERE (latitude IS NULL OR longitude IS NULL)
              AND (
                NULLIF(TRIM(address), '') IS NOT NULL
                OR NULLIF(TRIM(suburb),  '') IS NOT NULL
                OR NULLIF(TRIM(postcode::text), '') IS NOT NULL
              )
            ORDER BY id
            LIMIT 1000;  -- batch size
        """)
        rows = cur.fetchall()
        if not rows:
            print("Nothing to geocode.")
            conn.commit()
            return
        
        # For console logs
        total = len(rows)
        start_time = time.time()
        print(f"Starting geocode batch: {total} rows, provider={PROVIDER}, rps={REQUESTS_PER_SEC}")

        # 2) Load cache (key -> (lat, lon)) so we can use existing results without re-calling API
        cur.execute("SELECT address_key, latitude, longitude FROM geocode_cache;")
        cache_rows = cur.fetchall()
        cache = {k: (lat, lon) for (k, lat, lon) in cache_rows}

        to_cache = []   # (address_key, lat, lon, provider, raw_json)
        to_update = []  # (lat, lon, id)

        for (rid, address, suburb, state, postcode, akey) in rows:
            if not akey:
                # no address_key => skip (or compute one in SQL first)
                continue

            # If we already cached this key, use it for an update (if coords exist) and skip API
            if akey in cache:
                lat, lon = cache[akey]
                if lat is not None and lon is not None:
                    to_update.append((lat, lon, rid))
                # if cached as negative (lat/lon None), we skip to avoid retry storms
                continue

            # At least one non-empty address component?
            if not any([_norm(address), _norm(suburb), _norm(postcode)]):
                print(f"    ⏩ skipped id={rid} (no usable address parts)", flush=True)
                continue

            # Geocode with fallbacks
            lat, lon, raw = geocode_with_fallbacks(address, suburb, state, postcode)
            if lat is not None and lon is not None:
                print(f"    ✅ ({lat:.6f}, {lon:.6f})", flush=True)
                to_cache.append((akey, lat, lon, PROVIDER, json.dumps(raw)))
                to_update.append((lat, lon, rid))
                # also update in our in-memory cache so subsequent rows with same akey benefit
                cache[akey] = (lat, lon)
            else:
                print("    ⚠️  no result (cached empty)", flush=True)
                to_cache.append((akey, None, None, PROVIDER, json.dumps(raw)))
                cache[akey] = (None, None)

        # 3) Upsert cache
        if to_cache:
            execute_values(cur, """
                INSERT INTO geocode_cache (address_key, latitude, longitude, provider, raw_json)
                VALUES %s
                ON CONFLICT (address_key) DO UPDATE
                  SET latitude   = EXCLUDED.latitude,
                      longitude  = EXCLUDED.longitude,
                      provider   = EXCLUDED.provider,
                      raw_json   = EXCLUDED.raw_json,
                      created_at = now();
            """, to_cache)

        # 4) Update coords in service_search_view (if it's a table; if it's a view, update your base table instead)
        if to_update:
            execute_values(cur, """
                UPDATE service_search_view AS s
                SET latitude  = v.lat,
                    longitude = v.lon
                FROM (VALUES %s) AS v(lat, lon, id)
                WHERE s.id = v.id::int;
            """, to_update)

        conn.commit()
        print(f"Updated {len(to_update)} rows. Cached {len(to_cache)} address keys.")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
