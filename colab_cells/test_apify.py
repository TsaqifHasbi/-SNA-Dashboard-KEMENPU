import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

apify_token = os.getenv("APIFY_API_TOKEN")
if not apify_token:
    print("APIFY_API_TOKEN not found!")
    exit(1)

client = ApifyClient(apify_token)

print("Mengetes koneksi ke Apify (apify/instagram-scraper)...")

# Input run untuk mencari hashtag via instagram-hashtag-scraper
run_input = {
    "hashtags": ["makanbergizigratis"],
    "resultsType": "posts",
    "resultsLimit": 100,
}

# Run the Actor
run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)

print(f"Actor run finished. ID: {run.id}")

# Fetch and print Actor results from the run's dataset (if there are any)
items = list(client.dataset(run.default_dataset_id).iterate_items())
print(f"Total hasil yang didapat: {len(items)}")

if items:
    first = items[0]
    print("\n--- SAMPLE ITEM ---")
    print(f"URL: {first.get('url')}")
    print(f"Likes: {first.get('likesCount')}")
    print(f"Comments: {first.get('commentsCount')}")
    print(f"Timestamp: {first.get('timestamp')}")
