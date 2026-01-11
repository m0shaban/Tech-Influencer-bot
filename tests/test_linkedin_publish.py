#!/usr/bin/env python3
"""
Test LinkedIn Publisher - validate that publishing works
"""
from linkedin_publisher import LinkedInPublisher, test_linkedin_connection


def test_all():
    """Run all LinkedIn publishing tests"""
    print("=" * 60)
    print("Testing LinkedIn Publisher")
    print("=" * 60)

    # Test 1: Connection
    print("\n[Test 1] Testing connection...")
    result = test_linkedin_connection()
    if not result:
        print("[!] LinkedIn not configured properly")
        return False

    # Test 2: Text-only post
    print("\n[Test 2] Testing text-only post...")
    try:
        publisher = LinkedInPublisher()
        response = publisher.publish_text_post(
            caption="Test post from RoboBot\n\nThis is a test message to verify LinkedIn integration is working correctly.",
            link=None,
        )
        if response.get("status") == "success":
            print(f"[OK] Text post published successfully")
            print(f"    Post ID: {response.get('post_id')}")
        else:
            print(f"[!] Text post failed: {response}")
            return False
    except Exception as e:
        print(f"[!] Text post error: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Post with link
    print("\n[Test 3] Testing post with link...")
    try:
        publisher = LinkedInPublisher()
        response = publisher.publish_article(
            caption="Check out this amazing tech article about AI and automation!",
            article_url="https://www.linkedin.com",
        )
        if response.get("status") == "success":
            print(f"[OK] Link post published successfully")
            print(f"    Post ID: {response.get('post_id')}")
        else:
            print(f"[!] Link post failed: {response}")
            return False
    except Exception as e:
        print(f"[!] Link post error: {e}")
        return False

    print("\n" + "=" * 60)
    print("[OK] All LinkedIn tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_all()
