import asyncpg
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test():
    """Test database connection using environment variable"""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print('Error: DATABASE_URL environment variable is not set')
            print('Please set it in your .env file or environment')
            return

        # Convert SQLAlchemy URL format to asyncpg format if needed
        # e.g., postgresql+asyncpg://... -> postgresql://...
        if '+asyncpg' in database_url:
            database_url = database_url.replace('+asyncpg', '')

        conn = await asyncpg.connect(database_url)
        print('Connection successful!')
        await conn.close()
    except Exception as e:
        print(f'Connection failed: {e}')

if __name__ == '__main__':
    asyncio.run(test())
