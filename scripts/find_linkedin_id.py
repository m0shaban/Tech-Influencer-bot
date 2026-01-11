#!/usr/bin/env python3
"""Find correct LinkedIn member ID for the access token"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("LINKEDIN_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json",
}

# Try posting with a test message - LinkedIn will tell us the correct ID in error
test_ids = ["569338843", "78llmg4hvagid4"]

print("Testing different member IDs...")
print("=" * 60)

for member_id in test_ids:
    payload = {
        "author": f"urn:li:member:{member_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "Test post from RoboBot"},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        json=payload,
        headers=headers,
        timeout=10,
    )

    print(f"\nTesting: urn:li:member:{member_id}")
    print(f"Status: {resp.status_code}")

    if resp.status_code == 201:
        print(f"[SUCCESS] Post created!")
        print(f"Correct URN: urn:li:member:{member_id}")
        print(f"Post ID: {resp.headers.get('X-RestLi-Id')}")
        break
    else:
        print(f"Response: {resp.text}")

print("\n" + "=" * 60)
