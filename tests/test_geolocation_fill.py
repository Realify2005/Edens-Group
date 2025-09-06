import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import requests
import psycopg2
from psycopg2.extras import execute_values

# Import your module - adjust the import path as needed
from backend.postgresql.geolocation_fill import (
    _norm,
    _join_query,
    build_query,
    geocode_mapbox,
    geocode_with_fallbacks,
    _should_require_ssl,
    main
)


class TestUtilityFunctions:
    """Test utility functions for data normalization and query building."""
    
    def test_norm_basic_cases(self):
        """Test _norm function with various inputs."""
        assert _norm("  hello  ") == "hello"
        assert _norm("") is None
        assert _norm("   ") is None
        assert _norm(None) is None
        assert _norm(123) == "123"
        assert _norm(0) == "0"

    def test_join_query_basic(self):
        """Test _join_query with standard inputs."""
        result = _join_query("123 Main St", "Sydney", "NSW", "2000")
        expected = "123 Main St, Sydney, NSW, 2000, Australia"
        assert result == expected

    def test_join_query_with_nones_and_empties(self):
        """Test _join_query handles None and empty values."""
        result = _join_query("123 Main St", None, "NSW", "", country="Australia")
        assert result == "123 Main St, NSW, Australia"

    def test_join_query_all_empty(self):
        """Test _join_query returns None when all parts are empty."""
        assert _join_query(None, "", "  ", None) is None

    def test_join_query_custom_country(self):
        """Test _join_query with custom country."""
        result = _join_query("Main St", country="Canada")
        assert result == "Main St, Canada"

    def test_build_query(self):
        """Test build_query function."""
        result = build_query("123 Main St", "Sydney", "NSW", "2000")
        expected = "123 Main St, Sydney, NSW, 2000, Australia"
        assert result == expected


class TestSSLRequirement:
    """Test SSL requirement logic for database connections."""
    
    @pytest.mark.parametrize("db_url,expected", [
        ("postgres://user:pass@localhost:5432/db", False),
        ("postgres://user:pass@127.0.0.1:5432/db", False),
        ("postgres://user:pass@host.amazonaws.com:5432/db", True),
        ("postgres://user:pass@app.heroku.com:5432/db", True),
        ("postgres://user:pass@db.render.com:5432/db", True),
        ("postgres://user:pass@db.supabase.co:5432/db", True),
        ("postgres://user:pass@db.neon.tech:5432/db", True),
        ("postgres://user:pass@db.timescaledb.io:5432/db", True),
    ])
    def test_should_require_ssl(self, db_url, expected):
        """Test SSL requirement detection for various database URLs."""
        assert _should_require_ssl(db_url) == expected


class TestGeocodeMapbox:
    """Test Mapbox geocoding functionality."""
    
    @patch('backend.postgresql.geolocation_fill.API_KEY', 'test_api_key')
    @patch('backend.postgresql.geolocation_fill.requests.get')
    @patch('backend.postgresql.geolocation_fill.time.sleep')
    def test_geocode_mapbox_success(self, mock_sleep, mock_get):
        """Test successful geocoding with Mapbox."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "features": [{
                "center": [151.2093, -33.8688]  # lon, lat for Sydney
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        lat, lon, raw = geocode_mapbox("Sydney, NSW, Australia")
        
        assert lat == -33.8688
        assert lon == 151.2093
        assert "features" in raw
        mock_get.assert_called_once()

    @patch('backend.postgresql.geolocation_fill.API_KEY', None)
    def test_geocode_mapbox_no_api_key(self):
        """Test geocoding fails gracefully without API key."""
        lat, lon, raw = geocode_mapbox("Sydney, NSW, Australia")
        
        assert lat is None
        assert lon is None
        assert "error" in raw
        assert "GEOCODE_API_KEY not set" in raw["error"]

    @patch('backend.postgresql.geolocation_fill.API_KEY', 'test_api_key')
    @patch('backend.postgresql.geolocation_fill.requests.get')
    @patch('backend.postgresql.geolocation_fill.time.sleep')
    def test_geocode_mapbox_no_results(self, mock_sleep, mock_get):
        """Test geocoding with no results from Mapbox."""
        mock_response = Mock()
        mock_response.json.return_value = {"features": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        lat, lon, raw = geocode_mapbox("NonExistentPlace")
        
        assert lat is None
        assert lon is None
        assert raw == {"features": []}

    @patch('backend.postgresql.geolocation_fill.API_KEY', 'test_api_key')
    @patch('backend.postgresql.geolocation_fill.requests.get')
    @patch('backend.postgresql.geolocation_fill.time.sleep')
    @patch('backend.postgresql.geolocation_fill.MAX_TRIES', 2)
    def test_geocode_mapbox_request_exception(self, mock_sleep, mock_get):
        """Test geocoding with request exceptions and retries."""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        lat, lon, raw = geocode_mapbox("Sydney, NSW, Australia")
        
        assert lat is None
        assert lon is None
        assert "error" in raw
        assert mock_get.call_count == 2  # MAX_TRIES

    @patch('backend.postgresql.geolocation_fill.API_KEY', 'test_api_key')
    @patch('backend.postgresql.geolocation_fill.requests.get')
    @patch('backend.postgresql.geolocation_fill.time.sleep')
    def test_geocode_mapbox_malformed_response(self, mock_sleep, mock_get):
        """Test geocoding with malformed API response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "features": [{
                "center": [151.2093]  # Missing latitude
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        lat, lon, raw = geocode_mapbox("Sydney, NSW, Australia")
        
        assert lat is None
        assert lon is None


class TestGeocodeWithFallbacks:
    """Test the fallback geocoding logic."""
    
    @patch('backend.postgresql.geolocation_fill.geocode_mapbox')
    def test_geocode_with_fallbacks_first_success(self, mock_geocode):
        """Test fallback stops at first successful result."""
        mock_geocode.return_value = (-33.8688, 151.2093, {"success": True})
        
        lat, lon, raw = geocode_with_fallbacks("123 Main St", "Sydney", "NSW", "2000")
        
        assert lat == -33.8688
        assert lon == 151.2093
        assert mock_geocode.call_count == 1

    @patch('backend.postgresql.geolocation_fill.geocode_mapbox')
    def test_geocode_with_fallbacks_multiple_attempts(self, mock_geocode):
        """Test fallback tries multiple queries before succeeding."""
        # First two calls fail, third succeeds
        mock_geocode.side_effect = [
            (None, None, {"error": "no result"}),
            (None, None, {"error": "no result"}),
            (-33.8688, 151.2093, {"success": True})
        ]
        
        lat, lon, raw = geocode_with_fallbacks("123 Main St", "Sydney", "NSW", "2000")
        
        assert lat == -33.8688
        assert lon == 151.2093
        assert mock_geocode.call_count == 3

    @patch('backend.postgresql.geolocation_fill.geocode_mapbox')
    def test_geocode_with_fallbacks_all_fail(self, mock_geocode):
        """Test fallback when all attempts fail."""
        mock_geocode.return_value = (None, None, {"error": "no result"})
        
        lat, lon, raw = geocode_with_fallbacks("BadAddress", "BadSuburb", "NSW", "9999")
        
        assert lat is None
        assert lon is None
        assert "no result after fallbacks" in raw["note"]

    @patch('backend.postgresql.geolocation_fill.geocode_mapbox')
    def test_geocode_with_fallbacks_normalize_inputs(self, mock_geocode):
        """Test fallback normalizes input parameters."""
        mock_geocode.return_value = (-33.8688, 151.2093, {"success": True})
        
        # Test with integer postcode and whitespace
        lat, lon, raw = geocode_with_fallbacks("  123 Main St  ", "Sydney", "NSW", 2000)
        
        assert lat == -33.8688
        assert lon == 151.2093
        # Verify the query was built correctly (check first call args)
        first_call_query = mock_geocode.call_args_list[0][0][0]
        assert "123 Main St, Sydney, NSW, 2000, Australia" == first_call_query


class TestMainWorkflow:
    """Test the main geocoding workflow."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        conn = Mock()
        cur = Mock()
        conn.cursor.return_value = cur
        conn.autocommit = False
        return conn, cur

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', 'postgres://test')
    @patch('backend.postgresql.geolocation_fill.PROVIDER', 'mapbox')
    @patch('backend.postgresql.geolocation_fill.psycopg2.connect')
    @patch('backend.postgresql.geolocation_fill._should_require_ssl', return_value=False)
    def test_main_no_rows_to_geocode(self, mock_ssl, mock_connect, mock_db_connection):
        """Test main function when no rows need geocoding."""
        conn, cur = mock_db_connection
        mock_connect.return_value = conn
        cur.fetchall.return_value = []
        
        with patch('builtins.print') as mock_print:
            main()
        
        mock_print.assert_called_with("Nothing to geocode.")
        conn.commit.assert_called_once()

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', None)
    def test_main_no_database_url(self):
        """Test main function raises error when DATABASE_URL is not set."""
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            main()

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', 'postgres://test')
    @patch('backend.postgresql.geolocation_fill.PROVIDER', 'google')
    def test_main_wrong_provider(self):
        """Test main function raises error for unsupported provider."""
        with pytest.raises(RuntimeError, match="This script is configured for Mapbox only"):
            main()

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', 'postgres://test')
    @patch('backend.postgresql.geolocation_fill.PROVIDER', 'mapbox')
    @patch('backend.postgresql.geolocation_fill.psycopg2.connect')
    @patch('backend.postgresql.geolocation_fill._should_require_ssl', return_value=False)
    @patch('backend.postgresql.geolocation_fill.geocode_with_fallbacks')
    @patch('backend.postgresql.geolocation_fill.execute_values')
    def test_main_full_workflow(self, mock_execute_values, mock_geocode, mock_ssl, mock_connect):
        """Test complete main workflow with successful geocoding."""
        # Setup mocks
        conn = Mock()
        cur = Mock()
        conn.cursor.return_value = cur
        mock_connect.return_value = conn
        
        # Mock database rows
        test_rows = [(1, "123 Main St", "Sydney", "NSW", "2000", "test_key_1")]
        cur.fetchall.side_effect = [test_rows, []]  # First call returns rows, second returns empty cache
        
        # Mock successful geocoding
        mock_geocode.return_value = (-33.8688, 151.2093, {"success": True})
        
        with patch('builtins.print'):
            main()
        
        # Verify geocoding was called
        mock_geocode.assert_called_once_with("123 Main St", "Sydney", "NSW", "2000")
        
        # Verify database operations
        assert mock_execute_values.call_count == 2  # Cache upsert and coordinate update
        conn.commit.assert_called_once()

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', 'postgres://test')
    @patch('backend.postgresql.geolocation_fill.PROVIDER', 'mapbox')
    @patch('backend.postgresql.geolocation_fill.psycopg2.connect')
    @patch('backend.postgresql.geolocation_fill._should_require_ssl', return_value=False)
    def test_main_database_exception_rollback(self, mock_ssl, mock_connect):
        """Test main function rolls back on database exceptions."""
        conn = Mock()
        cur = Mock()
        conn.cursor.return_value = cur
        mock_connect.return_value = conn
        
        # Make fetchall raise an exception
        cur.fetchall.side_effect = psycopg2.Error("Database error")
        
        with pytest.raises(psycopg2.Error):
            main()
        
        conn.rollback.assert_called_once()
        cur.close.assert_called_once()
        conn.close.assert_called_once()

    @patch('backend.postgresql.geolocation_fill.DATABASE_URL', 'postgres://test')
    @patch('backend.postgresql.geolocation_fill.PROVIDER', 'mapbox')
    @patch('backend.postgresql.geolocation_fill.psycopg2.connect')
    @patch('backend.postgresql.geolocation_fill._should_require_ssl', return_value=False)
    def test_main_with_cache_hits(self, mock_ssl, mock_connect):
        """Test main function uses cached geocoding results."""
        conn = Mock()
        cur = Mock()
        conn.cursor.return_value = cur
        mock_connect.return_value = conn
        
        # Mock database rows and cache
        test_rows = [(1, "123 Main St", "Sydney", "NSW", "2000", "cached_key")]
        cache_rows = [("cached_key", -33.8688, 151.2093)]
        cur.fetchall.side_effect = [test_rows, cache_rows]
        
        with patch('builtins.print') as mock_print, \
             patch('backend.postgresql.geolocation_fill.execute_values') as mock_execute_values:
            main()
        
        # Should not call geocoding API since we have cached result
        # Should still update coordinates in main table
        assert mock_execute_values.call_count == 1  # Only coordinate update, no cache insert


class TestIntegration:
    """Integration tests combining multiple components."""
    
    @patch('backend.postgresql.geolocation_fill.API_KEY', 'test_key')
    @patch('backend.postgresql.geolocation_fill.requests.get')
    @patch('backend.postgresql.geolocation_fill.time.sleep')
    def test_full_geocoding_pipeline(self, mock_sleep, mock_get):
        """Test the complete geocoding pipeline from input to result."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "features": [{
                "center": [151.2093, -33.8688]
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test the full pipeline
        query = build_query("123 Collins St", "Melbourne", "VIC", "3000")
        lat, lon, raw = geocode_with_fallbacks("123 Collins St", "Melbourne", "VIC", "3000")
        
        assert query == "123 Collins St, Melbourne, VIC, 3000, Australia"
        assert lat == -33.8688
        assert lon == 151.2093
        assert "features" in raw


# Fixtures for test data
@pytest.fixture
def sample_address_data():
    """Provide sample address data for testing."""
    return {
        "complete": ("123 Main St", "Sydney", "NSW", "2000"),
        "partial": ("", "Melbourne", "VIC", "3000"),
        "minimal": ("", "", "QLD", "4000"),
        "invalid": ("", "", "", ""),
    }


# Performance and edge case tests
class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_unicode_addresses(self):
        """Test handling of unicode characters in addresses."""
        result = build_query("123 Königstraße", "München", "Bayern", "80331", country="Germany")
        assert "Königstraße" in result
        assert "München" in result

    def test_very_long_addresses(self):
        """Test handling of very long address strings."""
        long_address = "A" * 1000
        result = _norm(long_address)
        assert len(result) == 1000

    @patch('backend.postgresql.geolocation_fill.geocode_mapbox')
    def test_fallback_with_empty_components(self, mock_geocode):
        """Test fallback behavior with various empty address components."""
        mock_geocode.return_value = (None, None, {"no_result": True})
        
        # Test with only state
        lat, lon, raw = geocode_with_fallbacks("", "", "NSW", "")
        assert lat is None
        assert lon is None
        
        # Should have tried at least the state-only query
        assert mock_geocode.called


if __name__ == "__main__":
    # Run tests with: python -m pytest test_geocoding.py -v
    pytest.main([__file__, "-v"])