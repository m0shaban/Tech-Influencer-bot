"""
Get Blogger OAuth tokens using Google OAuth 2.0
Run this script to get Access Token and Refresh Token for Blogger API
"""

import os
from dotenv import load_dotenv
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

load_dotenv()

# Get credentials from .env
CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080"

# OAuth endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Blogger API scope
SCOPE = "https://www.googleapis.com/auth/blogger"

# Store the authorization code
auth_code = None


class OAuthHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback"""

    def do_GET(self):
        global auth_code

        # Parse the URL
        query = urlparse(self.path).query
        params = parse_qs(query)

        if "code" in params:
            auth_code = params["code"][0]

            # Send success response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✓ Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <p style="color: #666;">أغلق هذه النافذة وارجع للـ Terminal</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            # Error
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">✗ Authorization Failed</h1>
                <p>Please try again.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress log messages"""
        pass


def get_oauth_tokens():
    """Get OAuth tokens for Blogger API"""

    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "❌ Error: BLOGGER_CLIENT_ID and BLOGGER_CLIENT_SECRET must be set in .env"
        )
        return

    # Step 1: Build authorization URL
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "response_type": "code",
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
    }

    auth_url = f"{AUTH_URL}?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])

    print("=" * 60)
    print("🔐 Blogger OAuth 2.0 Token Generator")
    print("=" * 60)
    print("\nStep 1: Opening browser for authorization...")
    print("خطوة 1: جاري فتح المتصفح للموافقة...")
    print(f"\nIf browser doesn't open, visit this URL manually:")
    print(f"إذا لم يفتح المتصفح، افتح هذا الرابط يدوياً:")
    print(f"\n{auth_url}\n")

    # Open browser
    webbrowser.open(auth_url)

    # Step 2: Start local server to receive callback
    print("Step 2: Waiting for authorization...")
    print("خطوة 2: في انتظار الموافقة...\n")

    server = HTTPServer(("localhost", 8080), OAuthHandler)
    server.handle_request()  # Handle one request and stop

    if not auth_code:
        print("\n❌ No authorization code received")
        return

    print("\n✓ Authorization code received!")
    print("✓ تم استلام كود التفويض!\n")

    # Step 3: Exchange code for tokens
    print("Step 3: Exchanging code for tokens...")
    print("خطوة 3: جاري تبديل الكود بالـ Tokens...")

    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(TOKEN_URL, data=token_data)

        if response.status_code == 200:
            tokens = response.json()

            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            print("\n" + "=" * 60)
            print("✓ SUCCESS! Add these to your .env file:")
            print("✓ نجح! أضف هذه القيم لملف .env:")
            print("=" * 60)
            print(f"\nBLOGGER_ACCESS_TOKEN={access_token}")
            if refresh_token:
                print(f"BLOGGER_REFRESH_TOKEN={refresh_token}")
            else:
                print(
                    "⚠️  No refresh token received (you may need to revoke access and try again)"
                )
            print("\n" + "=" * 60)

        else:
            print(f"\n❌ Failed to get tokens: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"\n❌ Error exchanging code for tokens: {e}")


if __name__ == "__main__":
    get_oauth_tokens()
