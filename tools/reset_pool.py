import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
load_dotenv()

async def reset_pool():
    from twscrape import API
    api = API()
    username = os.environ.get("TWITTER_USERNAME")
    
    # Force delete the old account state
    try:
        await api.pool.delete_account(username)
        print(f"Deleted old state for {username}")
    except Exception as e:
        print("Delete failed:", e)

if __name__ == "__main__":
    asyncio.run(reset_pool())
