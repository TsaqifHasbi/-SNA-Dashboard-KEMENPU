import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
file_path = os.path.join(PROJECT_ROOT, '.env')

with open(file_path, 'a', encoding='utf-8') as f:
    f.write("\nTWITTER_AUTH_TOKEN=\n")
    f.write("TWITTER_CT0=\n")

print("Added cookie placeholders to .env")
