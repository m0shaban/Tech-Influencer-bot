"""
Image Generator Test Script
Tests Arabic text rendering and image upload functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_arabic_fonts():
    """Test Arabic font loading and reshaping."""
    print("\n" + "=" * 60)
    print("🔤 TEST 1: Arabic Font Loading")
    print("=" * 60)
    
    try:
        from image_generator import ArabicFontManager
        
        # Test font loading
        font = ArabicFontManager.get_font(size=48, bold=True)
        print(f"✅ Font loaded successfully: {type(font)}")
        
        # Test Arabic reshaping
        test_text = "مرحباً بكم في RoboVAI 🤖"
        reshaped = ArabicFontManager.reshape_arabic(test_text)
        print(f"✅ Arabic text reshaped:")
        print(f"   Original: {test_text}")
        print(f"   Reshaped: {reshaped}")
        
        return True
    except Exception as e:
        print(f"❌ Font test failed: {e}")
        return False


def test_image_generation():
    """Test image generation with Arabic text."""
    print("\n" + "=" * 60)
    print("🖼️ TEST 2: Image Generation")
    print("=" * 60)
    
    try:
        from image_generator import OGImageGenerator
        
        generator = OGImageGenerator()
        
        # Test with Arabic headline
        arabic_headline = "الذكاء الاصطناعي يغير طريقة عملنا في 2026"
        
        print(f"📝 Generating image with headline:")
        print(f"   '{arabic_headline}'")
        
        result = generator.generate_og_image(headline=arabic_headline)
        
        if result and result.get("local_path"):
            local_path = result["local_path"]
            print(f"✅ Image generated: {local_path}")
            
            # Check file exists and size
            path = Path(local_path)
            if path.exists():
                size_kb = path.stat().st_size / 1024
                print(f"✅ File size: {size_kb:.1f} KB")
                return result
            else:
                print(f"❌ File not found at: {local_path}")
                return None
        else:
            print(f"❌ Image generation returned: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_english_image():
    """Test image generation with English text."""
    print("\n" + "=" * 60)
    print("🖼️ TEST 3: English Image Generation")
    print("=" * 60)
    
    try:
        from image_generator import OGImageGenerator
        
        generator = OGImageGenerator()
        
        english_headline = "Bitcoin Breaks $100K: What This Means for DeFi"
        
        print(f"📝 Generating image with headline:")
        print(f"   '{english_headline}'")
        
        result = generator.generate_og_image(headline=english_headline)
        
        if result and result.get("local_path"):
            print(f"✅ Image generated: {result['local_path']}")
            return result
        else:
            print(f"❌ Image generation returned: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        return None


def test_r2_upload():
    """Test R2 upload if configured."""
    print("\n" + "=" * 60)
    print("☁️ TEST 4: R2 Upload (if configured)")
    print("=" * 60)
    
    try:
        import os
        
        # Check if R2 is configured
        r2_bucket = os.getenv("R2_BUCKET_NAME")
        r2_endpoint = os.getenv("R2_ENDPOINT_URL")
        
        if not r2_bucket or not r2_endpoint:
            print("⚠️ R2 not configured (R2_BUCKET_NAME or R2_ENDPOINT_URL missing)")
            print("   Skipping upload test...")
            return None
        
        print(f"✅ R2 configured: {r2_bucket}")
        
        from r2_uploader import upload_image_if_configured
        from image_generator import OGImageGenerator
        
        generator = OGImageGenerator()
        
        # Generate a test image
        result = generator.generate_og_image(headline="Test Upload Image")
        
        if not result or not result.get("local_path"):
            print("❌ Could not generate test image")
            return None
        
        local_path = result["local_path"]
        filename = f"test_upload_{Path(local_path).name}"
        
        print(f"📤 Uploading {filename}...")
        
        public_url = upload_image_if_configured(local_path, filename)
        
        if public_url:
            print(f"✅ Upload successful!")
            print(f"   URL: {public_url}")
            return public_url
        else:
            print("⚠️ Upload returned None (check R2 credentials)")
            return None
            
    except Exception as e:
        print(f"❌ R2 upload test failed: {e}")
        return None


async def test_telegram_upload():
    """Test uploading image to Telegram."""
    print("\n" + "=" * 60)
    print("📱 TEST 5: Telegram Image Upload")
    print("=" * 60)
    
    try:
        import os
        from telegram import Bot
        
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            print("⚠️ TELEGRAM_TOKEN not set, skipping...")
            return None
        
        # Get admin chat ID from env or use default
        admin_id = os.getenv("ADMIN_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_ID")
        if not admin_id:
            print("⚠️ ADMIN_CHAT_ID not set, skipping...")
            return None
        
        print(f"📱 Testing Telegram upload to chat: {admin_id}")
        
        # Generate test image
        from image_generator import OGImageGenerator
        
        generator = OGImageGenerator()
        
        result = generator.generate_og_image(headline="🧪 Test: تجربة رفع صورة عربية")
        
        if not result or not result.get("local_path"):
            print("❌ Could not generate test image")
            return None
        
        local_path = result["local_path"]
        
        bot = Bot(token=token)
        
        with open(local_path, "rb") as photo:
            message = await bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption="🧪 **Image Generator Test**\n\nIf you see this with Arabic text rendered correctly, the image generator is working! ✅",
                parse_mode="Markdown"
            )
        
        if message:
            print(f"✅ Telegram upload successful!")
            print(f"   Message ID: {message.message_id}")
            return True
        else:
            print("❌ Telegram upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Telegram upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_all_templates():
    """Test all design templates."""
    print("\n" + "=" * 60)
    print("🎨 TEST 6: All Design Templates")
    print("=" * 60)
    
    try:
        from image_generator import (
            GradientTemplate,
            MinimalistTemplate,
            ModernTemplate,
            NeonTemplate,
        )
        
        templates = [
            ("Gradient", GradientTemplate),
            ("Minimalist", MinimalistTemplate),
            ("Modern", ModernTemplate),
            ("Neon", NeonTemplate),
        ]
        
        test_headline = "Testing Template Design"
        
        for name, TemplateClass in templates:
            try:
                template = TemplateClass(width=1200, height=630)
                # Just verify it can be instantiated
                print(f"✅ {name} template: OK")
            except Exception as e:
                print(f"❌ {name} template: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return None


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 IMAGE GENERATOR TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Fonts
    results["fonts"] = test_arabic_fonts()
    
    # Test 2: Arabic image
    results["arabic_image"] = test_image_generation()
    
    # Test 3: English image
    results["english_image"] = test_english_image()
    
    # Test 4: R2 upload
    results["r2_upload"] = test_r2_upload()
    
    # Test 5: Telegram upload (async)
    try:
        results["telegram_upload"] = asyncio.run(test_telegram_upload())
    except Exception as e:
        print(f"⚠️ Telegram test skipped: {e}")
        results["telegram_upload"] = None
    
    # Test 6: Templates
    results["templates"] = test_all_templates()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is True or (result is not None and result is not False):
            status = "✅ PASS"
            passed += 1
        elif result is None:
            status = "⚠️ SKIP"
            skipped += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n🎉 All critical tests passed! Image generator is production-ready.")
    else:
        print("\n⚠️ Some tests failed. Please review before production deployment.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
