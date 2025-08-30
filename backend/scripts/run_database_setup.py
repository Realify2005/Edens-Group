"""
Script to add vector support to existing database
Run this after PR 1 implementation
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to Python path so we can import from backend
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database import async_engine


async def add_vector_support():
    """Add pgvector extension and columns to existing table"""
    print("Adding vector support to existing database...")
    
    async with async_engine.begin() as conn:
        # Read and execute the SQL script
        with open("scripts/add_vector_support.sql", "r") as f:
            sql_commands = f.read()
        
        # Split by semicolon and execute each command
        for command in sql_commands.split(';'):
            command = command.strip()
            if command:
                try:
                    await conn.execute(text(command))
                    print(f"Executed: {command[:50]}...")
                except Exception as e:
                    print(f"Error executing command: {e}")
                    print(f"Command: {command}")
    
    print("Database setup completed!")


async def test_connection():
    """Test database connection and query existing data"""
    print("\nTesting database connection...")
    
    async with async_engine.begin() as conn:
        # Test basic connection
        result = await conn.execute(text("SELECT 1"))
        print("Database connection successful")
        
        # Check if vector extension is available
        result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        if result.fetchone():
            print("pgvector extension installed")
        else:
            print("pgvector extension not found")
        
        # Count existing services
        result = await conn.execute(text("SELECT COUNT(*) FROM service_search_view"))
        count = result.scalar()
        print(f"Found {count} mental health services in database")
        
        # Check if embedding column exists
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'service_search_view' 
            AND column_name = 'embedding'
        """))
        
        if result.fetchone():
            print("Embedding column exists")
        else:
            print("Embedding column not found")


async def main():
    """Run database setup and tests"""
    try:
        await add_vector_support()
        await test_connection()
    except Exception as e:
        print(f"Setup failed: {e}")
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())