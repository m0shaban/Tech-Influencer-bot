"""
LinkedIn OAuth Helper - Get New Access Token
Run this script when your LinkedIn access token expires (every 2 months)
"""

import os
import webbrowser
from urllib.parse import urlencode, parse_qs
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "78llmg4hvagid4")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "https://www.linkedin.com/developers/tools/oauth/redirect"

# Required scopes for Share on LinkedIn
SCOPES = "r_liteprofile r_emailaddress w_member_social"


def step1_get_authorization_url():
    """Step 1: Get authorization URL to open in browser"""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }

    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    print("=" * 70)
    print("STEP 1: Get Authorization Code")
    print("=" * 70)
    print("\n1. Opening LinkedIn authorization page in your browser...")
    print(f"\nIf browser doesn't open, visit this URL:\n{auth_url}\n")

    webbrowser.open(auth_url)

    print("2. After authorizing, you'll be redirected to a URL like:")
    print("   https://www.linkedin.com/developers/tools/oauth/redirect?code=AQT...")
    print("\n3. Copy the FULL redirect URL and paste it below:")

    return input("\nPaste the redirect URL here: ").strip()


def step2_exchange_code_for_token(redirect_url):
    """Step 2: Exchange authorization code for access token"""
    # Extract code from redirect URL
    if "code=" not in redirect_url:
        raise ValueError("Invalid redirect URL. Must contain 'code=' parameter")

    # Parse URL to get code
    if "?" in redirect_url:
        query_string = redirect_url.split("?")[1]
        params = parse_qs(query_string)
        auth_code = params.get("code", [None])[0]
    else:
        raise ValueError("Invalid redirect URL format")

    if not auth_code:
        raise ValueError("Could not extract authorization code from URL")

    print("\n" + "=" * 70)
    print("STEP 2: Exchange Code for Access Token")
    print("=" * 70)
    print(f"\nAuthorization Code: {auth_code[:20]}...")

    # Exchange code for token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    print("\nRequesting access token...")
    response = requests.post(token_url, data=data, timeout=10)

    if response.status_code != 200:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

    token_data = response.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 0)

    print(f"\n✅ Success! Access token retrieved")
    print(f"Token expires in: {expires_in} seconds (~{expires_in // 86400} days)")

    return access_token


def step3_get_person_urn(access_token):
    """Step 3: Get your Person URN using the new token"""
    print("\n" + "=" * 70)
    print("STEP 3: Get Person URN")
    print("=" * 70)

    # Use OpenID Connect to get user info
    headers = {"Authorization": f"Bearer {access_token}"}

    # Try the userinfo endpoint
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    response = requests.get(userinfo_url, headers=headers, timeout=10)

    if response.status_code == 200:
        data = response.json()
        sub = data.get("sub")  # This is the Person ID

        if sub:
            person_urn = f"urn:li:person:{sub}"
            print(f"\n✅ Person URN: {person_urn}")
            return person_urn

    print(f"\n⚠️ Could not retrieve Person URN automatically")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return None


def step4_update_env_file(access_token, person_urn):
    """Step 4: Show instructions to update .env file"""
    print("\n" + "=" * 70)
    print("STEP 4: Update Your .env File")
    print("=" * 70)

    print("\nAdd/Update these lines in your .env file:\n")
    print("# LinkedIn")
    print(f"LINKEDIN_CLIENT_ID={CLIENT_ID}")
    print(f"LINKEDIN_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")

    if person_urn:
        print(f"LINKEDIN_PERSON_URN={person_urn}")
    else:
        print("LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID_HERE")
        print("\n⚠️ You'll need to find your Person URN manually")
        print("Visit: https://www.linkedin.com/in/YOUR-PROFILE-NAME/")
        print("Then use Chrome DevTools to find your Person ID")

    print("\n" + "=" * 70)
    print("✅ All Done!")
    print("=" * 70)
    print("\nYour LinkedIn access token is valid for ~60 days")
    print("Run this script again when it expires")


def main():
    """Main flow to get new LinkedIn access token"""
    print("\n🔐 LinkedIn OAuth Token Refresher")
    print("=" * 70)

    if not CLIENT_SECRET:
        print("\n❌ Error: LINKEDIN_CLIENT_SECRET not set in .env file")
        print("\nTo get your client secret:")
        print("1. Go to: https://www.linkedin.com/developers/apps")
        print("2. Click on your app: 'robovai bot'")
        print("3. Go to 'Auth' tab")
        print("4. Click 'Show' next to Primary Client Secret")
        print("5. Copy it and add to .env file:\n")
        print(f"   LINKEDIN_CLIENT_SECRET=YOUR_SECRET_HERE")
        return

    try:
        # Step 1: Get authorization code
        redirect_url = step1_get_authorization_url()

        # Step 2: Exchange for access token
        access_token = step2_exchange_code_for_token(redirect_url)

        if not access_token:
            print("\n❌ Failed to get access token")
            return

        # Step 3: Get Person URN
        person_urn = step3_get_person_urn(access_token)

        # Step 4: Show instructions
        step4_update_env_file(access_token, person_urn)

    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
