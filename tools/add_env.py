import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
file_path = os.path.join(PROJECT_ROOT, '.env')
with open(file_path, 'a', encoding='utf-8') as f:
    f.write("\n# Akun Dummy untuk twscrape\n")
    f.write("TWITTER_USERNAME=\n")
    f.write("TWITTER_PASSWORD=\n")
    f.write("TWITTER_EMAIL=\n")
    f.write("TWITTER_EMAIL_PASSWORD=\n")

print("Added twscrape placeholders to .env")
