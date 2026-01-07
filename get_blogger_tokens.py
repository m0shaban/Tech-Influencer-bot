"""
Script to get Blogger OAuth tokens
Run this once to get your access_token and refresh_token
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

# Blogger API scope
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def get_blogger_tokens():
    """Get OAuth tokens for Blogger API"""

    client_id = os.getenv("BLOGGER_CLIENT_ID")
    client_secret = os.getenv("BLOGGER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Error: BLOGGER_CLIENT_ID or BLOGGER_CLIENT_SECRET not found in .env")
        return

    # Create client config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
        }
    }

    try:
        print("🔐 Starting OAuth authentication...")
        print("=" * 60)

        # Create the flow
        flow = InstalledAppFlow.from_client_config(
            client_config, scopes=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )

        # Run local server for authentication
        print("\n📱 A browser window will open for authentication...")
        print("   Please sign in with your Google account and authorize the app")
        print("=" * 60)

        credentials = flow.run_local_server(
            port=8080,
            success_message="✅ Authentication successful! You can close this window.",
            open_browser=True,
        )

        print("\n" + "=" * 60)
        print("✅ Authentication successful!")
        print("=" * 60)
        print("\n📋 Copy these values to your .env file:")
        print("-" * 60)
        print(f"BLOGGER_ACCESS_TOKEN={credentials.token}")
        print(f"BLOGGER_REFRESH_TOKEN={credentials.refresh_token}")
        print("-" * 60)

        print("\n💡 Tip: The refresh_token will be used to automatically")
        print("   get new access_tokens when the current one expires.")

        # Save to a temp file for easy copying
        with open("blogger_tokens.txt", "w", encoding="utf-8") as f:
            f.write(f"BLOGGER_ACCESS_TOKEN={credentials.token}\n")
            f.write(f"BLOGGER_REFRESH_TOKEN={credentials.refresh_token}\n")

        print(f"\n💾 Tokens also saved to: blogger_tokens.txt")

    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your Client ID and Secret are correct")
        print("2. Enable Blogger API in Google Cloud Console:")
        print("   https://console.cloud.google.com/apis/library/blogger.googleapis.com")
        print("3. Add redirect URI in OAuth consent screen:")
        print("   http://localhost:8080")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   Blogger OAuth Token Generator")
    print("=" * 60)
    get_blogger_tokens()
