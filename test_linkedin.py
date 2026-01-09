"""
LinkedIn Publisher Test Script
Test LinkedIn API connection and publishing
"""

import os
from dotenv import load_dotenv
from linkedin_publisher import LinkedInPublisher

load_dotenv()


def test_connection():
    """Test 1: Check if credentials are configured"""
    print("=" * 70)
    print("TEST 1: Configuration Check")
    print("=" * 70)

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")

    checks = {
        "Client ID": client_id,
        "Client Secret": client_secret,
        "Access Token": access_token,
        "Person URN": person_urn,
    }

    all_ok = True
    for name, value in checks.items():
        if value:
            # Show first 20 chars only
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {name}: {display}")
        else:
            print(f"❌ {name}: Not configured")
            all_ok = False

    print()
    return all_ok


def test_token_validity():
    """Test 2: Verify access token format"""
    print("=" * 70)
    print("TEST 2: Token Validity Check")
    print("=" * 70)

    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

    if not access_token:
        print("❌ No access token found")
        return False

    # LinkedIn tokens typically start with AQ
    if access_token.startswith("AQ"):
        print(f"✅ Token format looks valid: {access_token[:10]}...")
        print(f"✅ Token length: {len(access_token)} characters")
        print("\n⚠️ Note: Token expires after ~60 days")
        print("   If publishing fails, run: python get_linkedin_token.py")
        return True
    else:
        print(f"⚠️ Token format unexpected: {access_token[:10]}...")
        print("   Token might still work, but verify if publishing fails")
        return True


def test_text_post():
    """Test 3: Publish a simple text post"""
    print("\n" + "=" * 70)
    print("TEST 3: Text Post Publishing")
    print("=" * 70)

    try:
        publisher = LinkedInPublisher()

        test_caption = """🤖 Testing RoboVAI LinkedIn Integration

This is an automated test post from my AI-powered content publishing system.

✅ Multi-platform publishing
✅ Intelligent AI routing
✅ Sequential publishing with cross-links

#AI #Automation #TechInnovation"""

        print("\nPublishing test post...")
        print(f"Caption preview: {test_caption[:50]}...")

        result = publisher.publish_text_post(
            caption=test_caption,
            visibility="PUBLIC",  # Change to "CONNECTIONS" for private test
        )

        print("\n✅ SUCCESS!")
        print(f"Platform: {result.get('platform')}")
        print(f"Post ID: {result.get('post_id')}")

        if result.get("post_id"):
            print(
                f"\n🔗 View post at: https://www.linkedin.com/feed/update/{result.get('post_id')}"
            )

        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")

        # Show common error solutions
        if "401" in str(e):
            print("\n💡 Solution: Access token expired or invalid")
            print("   Run: python get_linkedin_token.py")
        elif "403" in str(e):
            print("\n💡 Solution: Missing permissions")
            print("   Ensure w_member_social scope is enabled in your LinkedIn app")
        elif "400" in str(e):
            print("\n💡 Solution: Invalid request format")
            print("   Check that LINKEDIN_PERSON_URN is correct")

        import traceback

        traceback.print_exc()
        return False


def test_article_post():
    """Test 4: Share an article with preview"""
    print("\n" + "=" * 70)
    print("TEST 4: Article Sharing (Optional)")
    print("=" * 70)

    confirm = input("\nDo you want to test article sharing? (y/N): ").strip().lower()

    if confirm != "y":
        print("⏭️  Skipped")
        return True

    try:
        publisher = LinkedInPublisher()

        test_caption = """📚 Interesting read on AI automation

Check out this article about intelligent content publishing systems."""

        test_url = "https://blog.linkedin.com/"

        print("\nPublishing article share...")

        result = publisher.publish_article(
            caption=test_caption,
            article_url=test_url,
            visibility="CONNECTIONS",  # Private test
        )

        print("\n✅ SUCCESS!")
        print(f"Post ID: {result.get('post_id')}")

        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("\n🧪 LinkedIn Publisher Test Suite")
    print("=" * 70)
    print("\n⚠️  WARNING: This will publish real posts to your LinkedIn profile")
    print("   Posts will be PUBLIC by default")
    print()

    confirm = input("Continue with tests? (y/N): ").strip().lower()

    if confirm != "y":
        print("\n❌ Tests cancelled")
        return

    print()

    # Run tests
    results = []

    # Test 1: Configuration
    config_ok = test_connection()
    results.append(("Configuration", config_ok))

    if not config_ok:
        print("\n❌ Configuration incomplete. Please add credentials to .env file")
        print("\n📝 Steps to fix:")
        print("1. Get Client Secret from: https://www.linkedin.com/developers/apps")
        print("2. Run: python get_linkedin_token.py")
        print("3. Add credentials to .env file")
        return

    # Test 2: Token validity
    token_ok = test_token_validity()
    results.append(("Token Format", token_ok))

    # Test 3: Publish text post
    publish_ok = test_text_post()
    results.append(("Text Publishing", publish_ok))

    if not publish_ok:
        print("\n⚠️  Publishing failed. Skipping remaining tests.")
    else:
        # Test 4: Article sharing (optional)
        article_ok = test_article_post()
        results.append(
            ("Article Sharing", article_ok if article_ok is not None else True)
        )

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n🎉 All tests passed! LinkedIn is ready to use")
        print("\n💡 To enable LinkedIn in automatic publishing:")
        print("   1. Open platform_config.json")
        print("   2. Set platforms.linkedin.enabled = true")
    else:
        print("\n⚠️  Some tests failed. Check errors above for solutions")

    print()


if __name__ == "__main__":
    main()
