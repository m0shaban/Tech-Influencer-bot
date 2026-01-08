"""
Debug Facebook Page Access Token
Check token validity and get correct Page ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

if not access_token:
    print("❌ FACEBOOK_PAGE_ACCESS_TOKEN not found in .env")
    exit(1)

print("=" * 70)
print("🔍 Facebook Token Debugger")
print("=" * 70)

# Step 1: Debug the token
print("\n1. Checking token validity...")
debug_url = "https://graph.facebook.com/v18.0/debug_token"
params = {"input_token": access_token, "access_token": access_token}

try:
    response = requests.get(debug_url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json().get("data", {})
        print(f"   ✓ Token Type: {data.get('type', 'Unknown')}")
        print(f"   ✓ Valid: {data.get('is_valid', False)}")
        print(
            f"   ✓ Expires: {data.get('expires_at', 'Never') if data.get('expires_at') == 0 else 'Check expiry'}"
        )
        print(f"   ✓ App ID: {data.get('app_id', 'Unknown')}")

        scopes = data.get("scopes", [])
        print(f"   ✓ Scopes: {', '.join(scopes) if scopes else 'None'}")

        if "pages_manage_posts" not in scopes and "pages_read_engagement" not in scopes:
            print("\n   ⚠️  Warning: Token missing page posting permissions!")
            print("   ⚠️  تحذير: التوكن ينقصه صلاحيات النشر!")
    else:
        print(f"   ✗ Failed to debug token: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Step 2: Get user's pages
print("\n2. Fetching your pages...")
pages_url = "https://graph.facebook.com/v18.0/me/accounts"
params = {"access_token": access_token}

try:
    response = requests.get(pages_url, params=params, timeout=10)
    if response.status_code == 200:
        pages = response.json().get("data", [])

        if pages:
            print(f"   ✓ Found {len(pages)} page(s):\n")
            for i, page in enumerate(pages, 1):
                print(f"   {i}. {page.get('name', 'Unknown')}")
                print(f"      ID: {page.get('id')}")
                print(f"      Access Token: {page.get('access_token')[:50]}...")
                print(f"      Category: {page.get('category', 'N/A')}")

                # Get page details
                page_id = page.get("id")
                page_token = page.get("access_token")

                page_url = f"https://graph.facebook.com/v18.0/{page_id}"
                page_params = {
                    "fields": "name,username,followers_count,fan_count",
                    "access_token": page_token,
                }

                try:
                    page_response = requests.get(
                        page_url, params=page_params, timeout=5
                    )
                    if page_response.status_code == 200:
                        page_data = page_response.json()
                        username = page_data.get("username", "N/A")
                        followers = page_data.get("followers_count") or page_data.get(
                            "fan_count", 0
                        )

                        if username != "N/A":
                            print(f"      Username: @{username}")
                        print(f"      Followers: {followers:,}")
                except:
                    pass

                print()

            print("=" * 70)
            print("✅ SOLUTION:")
            print("=" * 70)
            print("\nUse the PAGE ACCESS TOKEN (not user token) for posting:")
            print("استخدم PAGE ACCESS TOKEN (وليس user token) للنشر:\n")

            first_page = pages[0]
            print(f"FACEBOOK_PAGE_ACCESS_TOKEN={first_page.get('access_token')}")
            print(f"FACEBOOK_PAGE_ID={first_page.get('id')}")
            print("\n" + "=" * 70)

        else:
            print("   ✗ No pages found")
            print("   ✗ لم يتم العثور على صفحات")
            print("\n   Make sure:")
            print("   تأكد من:")
            print("   1. You manage at least one Facebook Page")
            print("   2. Token has 'pages_show_list' permission")
    else:
        print(f"   ✗ Failed to fetch pages: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 70)
print("📝 Next Steps:")
print("   1. Copy the correct PAGE ACCESS TOKEN above")
print("   2. Update your .env file with the values shown")
print("   3. Run: python facebook_publisher.py")
print("=" * 70)
