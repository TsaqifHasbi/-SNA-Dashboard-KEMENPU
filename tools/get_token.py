import requests
import json

app_id = "1769835810951745"
app_secret = "1e055df472528ebd8941747b47293a7f"
redirect_uri = "https://example.com/"
code = "AQKpYPPRbpZLWhXjkmlDGvgMMqP2wxh12ZdPtyt48BDSE98Aor_Re1MlD2gvV00LMqZ8kh6btIO4AmVPDJHxqTDsW4-ZhXwjgV-B2oPawShuxwos2QFX-Y2e9lC4axm7moPM_uAK_gi2eLFxKjidNYXtid3ZlFGaHjwSK4BELpWjlLxwwjLntnxpUZgL1mX9N0kYdJ09fqpS3e2f7-zEbgqsPooXuh1AmlLjoKQ6rtWaTWpXzW-Ve3tZ1zKBLUnBBRktpOVJFdQNVE9XdTu8htlcyH5x72Scm6SgXGktRyZdDIdZjQHIdcGzmcwLmit7R01eaBq4NhnBPhvt3Kg6A_tl7SjLxBsIvHIHR_adiVXiqcVwcLnaW-vQECmAkNvad1pI-uumeLKbm_VU-hIjYlHQyDKp6F6T43bkUIyb-VRmPw"

# 1. Exchange code for token
token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
token_params = {
    "client_id": app_id,
    "redirect_uri": redirect_uri,
    "client_secret": app_secret,
    "code": code
}

print("Fetching token...")
token_res = requests.get(token_url, params=token_params)
token_data = token_res.json()

if "access_token" not in token_data:
    print("Error getting token:", token_data)
    exit(1)

access_token = token_data["access_token"]
print(f"Token obtained: {access_token[:10]}...")

# 2. Exchange short-lived token for long-lived token (optional but good)
long_token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
long_token_params = {
    "grant_type": "fb_exchange_token",
    "client_id": app_id,
    "client_secret": app_secret,
    "fb_exchange_token": access_token
}
long_res = requests.get(long_token_url, params=long_token_params)
long_data = long_res.json()
if "access_token" in long_data:
    access_token = long_data["access_token"]
    print("Upgraded to long-lived token.")

# 3. Get Instagram User ID
accounts_url = "https://graph.facebook.com/v18.0/me/accounts"
accounts_params = {
    "fields": "instagram_business_account",
    "access_token": access_token
}
print("Fetching accounts...")
acc_res = requests.get(accounts_url, params=accounts_params)
acc_data = acc_res.json()

ig_user_id = None
if "data" in acc_data:
    for page in acc_data["data"]:
        if "instagram_business_account" in page:
            ig_user_id = page["instagram_business_account"]["id"]
            break

if not ig_user_id:
    print("No Instagram Business Account found linked to the Pages. Data:", acc_data)
else:
    print(f"IG_USER_ID found: {ig_user_id}")
    
    # Save to .env
    with open(".env", "a") as f:
        f.write(f"\\nINSTAGRAM_ACCESS_TOKEN={access_token}\\n")
        f.write(f"INSTAGRAM_USER_ID={ig_user_id}\\n")
    print("Successfully written to .env!")

