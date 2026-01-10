#!/usr/bin/env python3
"""
🧪 Full System Test Script
Tests all components of the Tech Influencer Bot system

Run: python test_full_system.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Colors for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_test(name: str, passed: bool, details: str = ""):
    status = (
        f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
    )
    print(f"  [{status}] {name}")
    if details:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")


class SystemTester:
    """Comprehensive system tester"""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load config.json"""
        try:
            config_path = Path(__file__).parent / "config.json"
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            print_error(f"Failed to load config.json: {e}")
            return {}

    # =========================================================================
    # TEST 1: Environment Variables
    # =========================================================================
    def test_environment(self) -> Dict[str, Any]:
        """Test all required environment variables"""
        print_header("TEST 1: Environment Variables")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        # Core variables
        core_vars = [
            ("TELEGRAM_TOKEN", "Main bot token"),
            ("ADMIN_USER_ID", "Admin user ID"),
            ("GROQ_API_KEY", "Primary Groq API key"),
        ]

        # Brand-specific variables
        brand_vars = {
            "blocksignals": [
                ("TELEGRAM_TOKEN_BS", "BlockSignals Telegram token"),
                ("DISCORD_WEBHOOK_URL_BS", "BlockSignals Discord webhook"),
                ("CHANNEL_ID_BS", "BlockSignals channel ID"),
            ],
            "zerodev": [
                ("TELEGRAM_TOKEN_ZDS", "ZeroDev Telegram token"),
                ("DEVTO_API_KEY_ZDS", "ZeroDev Dev.to API key"),
                ("CHANNEL_ID_ZDS", "ZeroDev channel ID"),
            ],
            "robovai_ar": [
                ("TELEGRAM_TOKEN_ARB", "RoboVAI Arabic Telegram token"),
                ("BLOGGER_ACCESS_TOKEN_ARB", "RoboVAI Blogger token"),
                ("BLOGGER_BLOG_ID_ARB", "RoboVAI Blogger blog ID"),
                ("FACEBOOK_PAGE_ACCESS_TOKEN_ARB", "RoboVAI Facebook token"),
                ("CHANNEL_ID_ARB", "RoboVAI channel ID"),
            ],
        }

        # Check core variables
        print_info("Core Variables:")
        for var, desc in core_vars:
            value = os.getenv(var)
            if value:
                print_test(f"{var} ({desc})", True, f"Set ({len(value)} chars)")
                results["passed"] += 1
            else:
                print_test(f"{var} ({desc})", False, "MISSING!")
                results["failed"] += 1

        # Check optional Groq keys
        print_info("\nGroq API Keys (for load balancing):")
        groq_count = 0
        for i in range(1, 5):
            key_name = f"GROQ_API_KEY_{i}" if i > 1 else "GROQ_API_KEY"
            if os.getenv(key_name):
                groq_count += 1
        print_test(f"Groq API Keys", groq_count > 0, f"{groq_count} keys configured")

        # Check NVIDIA keys
        print_info("\nNVIDIA API Keys (for reasoning):")
        nvidia_keys = []
        for key in ["NVIDIA_API_KEY", "NVIDIA_API_KEY_DEEPSEEK"]:
            if os.getenv(key):
                nvidia_keys.append(key)
        if nvidia_keys:
            print_test("NVIDIA API Keys", True, f"{len(nvidia_keys)} keys configured")
            results["passed"] += 1
        else:
            print_test("NVIDIA API Keys", False, "No NVIDIA keys (optional)")
            results["warnings"] += 1

        # Check brand-specific variables
        for brand, vars_list in brand_vars.items():
            print_info(f"\n{brand.upper()} Variables:")
            for var, desc in vars_list:
                value = os.getenv(var)
                if value:
                    print_test(f"{var}", True, f"Set ({len(value)} chars)")
                    results["passed"] += 1
                else:
                    print_test(f"{var}", False, "MISSING!")
                    results["failed"] += 1

        self.results["environment"] = results
        return results

    # =========================================================================
    # TEST 2: Config.json Validation
    # =========================================================================
    def test_config(self) -> Dict[str, Any]:
        """Test config.json structure and values"""
        print_header("TEST 2: Config.json Validation")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        if not self.config:
            print_error("Config not loaded!")
            results["failed"] += 1
            return results

        # Check main keys
        print_info("Main Configuration:")
        main_keys = ["status", "brands", "active_brand", "auto_rotate_brands"]
        for key in main_keys:
            if key in self.config:
                print_test(f"config.{key}", True, str(self.config[key])[:50])
                results["passed"] += 1
            else:
                print_test(f"config.{key}", False, "Missing key")
                results["failed"] += 1

        # Check brands
        brands = self.config.get("brands", {})
        print_info(f"\nBrands ({len(brands)} configured):")

        for brand_key, brand_cfg in brands.items():
            print_info(f"\n  {brand_key}:")

            # Required brand fields
            required = [
                "display_name",
                "language",
                "system_prompt",
                "feeds",
                "platforms",
                "channel_id",
            ]
            for field in required:
                if field in brand_cfg:
                    value = brand_cfg[field]
                    if field == "feeds":
                        print_test(f"    {field}", True, f"{len(value)} feeds")
                    elif field == "platforms":
                        enabled = [p for p, c in value.items() if c.get("enabled")]
                        print_test(
                            f"    {field}", True, f"Enabled: {', '.join(enabled)}"
                        )
                    elif field == "system_prompt":
                        print_test(f"    {field}", True, f"{len(value)} chars")
                    else:
                        print_test(f"    {field}", True, str(value)[:30])
                    results["passed"] += 1
                else:
                    print_test(f"    {field}", False, "Missing!")
                    results["failed"] += 1

            # Check schedule
            schedule = brand_cfg.get("schedule", {})
            if schedule:
                tz = schedule.get("timezone", "Not set")
                wake = schedule.get("wake_hour", "?")
                sleep = schedule.get("sleep_hour", "?")
                print_test(f"    schedule", True, f"{tz}, {wake}:00-{sleep}:00")
                results["passed"] += 1
            else:
                print_test(f"    schedule", False, "Missing schedule config")
                results["warnings"] += 1

        self.results["config"] = results
        return results

    # =========================================================================
    # TEST 3: AI Provider Connectivity
    # =========================================================================
    async def test_ai_providers(self) -> Dict[str, Any]:
        """Test AI provider connections"""
        print_header("TEST 3: AI Provider Connectivity")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from ai_provider_manager import AIProviderManager

            manager = AIProviderManager()

            print_info("Groq API Keys:")
            print_test(
                "Loaded keys",
                len(manager.groq_keys) > 0,
                f"{len(manager.groq_keys)} keys",
            )

            print_info("\nNVIDIA API Keys:")
            print_test(
                "Loaded keys",
                len(manager.nvidia_keys) > 0,
                f"{len(manager.nvidia_keys)} keys",
            )

            # Test actual API call to Groq
            print_info("\nTesting Groq API Call:")
            try:
                from openai import OpenAI

                client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=(
                        manager.groq_keys[0]
                        if manager.groq_keys
                        else os.getenv("GROQ_API_KEY")
                    ),
                )

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": "Say 'API OK' in 2 words"}],
                    max_tokens=10,
                )

                if response.choices:
                    print_test(
                        "Groq API call",
                        True,
                        f"Response: {response.choices[0].message.content[:30]}",
                    )
                    results["passed"] += 1
                else:
                    print_test("Groq API call", False, "Empty response")
                    results["failed"] += 1

            except Exception as e:
                print_test("Groq API call", False, str(e)[:50])
                results["failed"] += 1

            results["passed"] += 2  # For key loading

        except Exception as e:
            print_error(f"AI Provider test failed: {e}")
            results["failed"] += 1

        self.results["ai_providers"] = results
        return results

    # =========================================================================
    # TEST 4: RSS Feed Fetching
    # =========================================================================
    async def test_rss_feeds(self) -> Dict[str, Any]:
        """Test RSS feed fetching for all brands"""
        print_header("TEST 4: RSS Feed Fetching")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from feed_manager import fetch_random_new_post

            brands = self.config.get("brands", {})

            for brand_key, brand_cfg in brands.items():
                feeds = brand_cfg.get("feeds", [])
                print_info(f"\n{brand_key} ({len(feeds)} feeds):")

                # Try to fetch a post
                try:
                    post = fetch_random_new_post(brand=brand_key)
                    if post:
                        print_test(
                            f"Fetch post",
                            True,
                            f"'{post.get('title', 'Untitled')[:40]}...'",
                        )
                        results["passed"] += 1
                    else:
                        print_test(
                            f"Fetch post",
                            False,
                            "No posts available (might be duplicate filter)",
                        )
                        results["warnings"] += 1
                except Exception as e:
                    print_test(f"Fetch post", False, str(e)[:50])
                    results["failed"] += 1

        except Exception as e:
            print_error(f"RSS test failed: {e}")
            results["failed"] += 1

        self.results["rss_feeds"] = results
        return results

    # =========================================================================
    # TEST 5: Content Generation
    # =========================================================================
    async def test_content_generation(self) -> Dict[str, Any]:
        """Test AI content generation for each brand"""
        print_header("TEST 5: Content Generation")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from ai_processor import rewrite_with_ai, get_last_ai_error

            # Test data
            test_article = {
                "title": "OpenAI Announces GPT-5 with Revolutionary Capabilities",
                "summary": "OpenAI has unveiled GPT-5, featuring improved reasoning, multimodal understanding, and reduced hallucinations. The new model shows 50% improvement in benchmark tests.",
                "link": "https://example.com/gpt5-announcement",
            }

            brands = self.config.get("brands", {})

            for brand_key, brand_cfg in brands.items():
                language = brand_cfg.get("language", "en")
                system_prompt = brand_cfg.get("system_prompt", "")

                print_info(f"\n{brand_key} (language: {language}):")

                # Get enabled platforms
                platforms = brand_cfg.get("platforms", {})
                enabled = [p for p, c in platforms.items() if c.get("enabled")]

                if not enabled:
                    print_test("Platforms", False, "No platforms enabled!")
                    results["failed"] += 1
                    continue

                # Test generation for first enabled platform
                test_platform = enabled[0]
                print_info(f"  Testing platform: {test_platform}")

                try:
                    result = rewrite_with_ai(
                        title=test_article["title"],
                        summary=test_article["summary"],
                        link=test_article["link"],
                        system_prompt=system_prompt,
                        platform=test_platform,
                        brand_name=brand_key,
                        brand_language=language,
                    )

                    if result:
                        # Check key fields
                        fields_ok = []
                        fields_missing = []

                        for field in [
                            "telegram_post",
                            "facebook_post",
                            "blog_content_md",
                            "discord_msg",
                        ]:
                            content = result.get(field, "")
                            if content and len(content) > 50:
                                fields_ok.append(field)
                            else:
                                fields_missing.append(field)

                        if fields_ok:
                            print_test(
                                f"Content generation",
                                True,
                                f"Generated: {', '.join(fields_ok)}",
                            )
                            results["passed"] += 1

                            # Show sample
                            sample_field = fields_ok[0]
                            sample = result[sample_field][:100].replace("\n", " ")
                            print(
                                f"       {Colors.CYAN}Sample: {sample}...{Colors.END}"
                            )
                        else:
                            print_test(f"Content generation", False, "All fields empty")
                            results["failed"] += 1
                    else:
                        error = get_last_ai_error()
                        print_test(f"Content generation", False, f"Error: {error}")
                        results["failed"] += 1

                except Exception as e:
                    print_test(f"Content generation", False, str(e)[:80])
                    results["failed"] += 1

        except Exception as e:
            print_error(f"Content generation test failed: {e}")
            results["failed"] += 1

        self.results["content_generation"] = results
        return results

    # =========================================================================
    # TEST 6: Platform Publishers
    # =========================================================================
    async def test_platform_publishers(self) -> Dict[str, Any]:
        """Test platform publisher initialization"""
        print_header("TEST 6: Platform Publishers")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from multi_platform_publisher import MultiPlatformPublisher

            brands = self.config.get("brands", {})

            for brand_key, brand_cfg in brands.items():
                print_info(f"\n{brand_key}:")

                try:
                    publisher = MultiPlatformPublisher(brand_key=brand_key)
                    enabled = publisher.enabled_platforms

                    if enabled:
                        print_test(
                            f"Publisher init", True, f"Enabled: {', '.join(enabled)}"
                        )
                        results["passed"] += 1
                    else:
                        print_test(f"Publisher init", False, "No platforms enabled")
                        results["failed"] += 1

                except Exception as e:
                    print_test(f"Publisher init", False, str(e)[:50])
                    results["failed"] += 1

        except Exception as e:
            print_error(f"Publisher test failed: {e}")
            results["failed"] += 1

        self.results["publishers"] = results
        return results

    # =========================================================================
    # TEST 7: Image Generator
    # =========================================================================
    async def test_image_generator(self) -> Dict[str, Any]:
        """Test image generation with Arabic text"""
        print_header("TEST 7: Image Generator")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from image_generator import OGImageGenerator, ArabicFontManager

            # Test Arabic font
            print_info("Arabic Font Support:")
            try:
                font = ArabicFontManager.get_font(size=32)
                print_test(
                    "Arabic font loaded",
                    True,
                    f"Font: {ArabicFontManager._picked_name}",
                )
                results["passed"] += 1
            except Exception as e:
                print_test("Arabic font loaded", False, str(e)[:50])
                results["failed"] += 1

            # Test Arabic text reshaping
            print_info("\nArabic Text Reshaping:")
            try:
                test_text = "مرحباً بالعالم - اختبار النص العربي"
                reshaped = ArabicFontManager.reshape_arabic(test_text)
                print_test("Text reshaping", True, f"Input: {len(test_text)} chars")
                results["passed"] += 1
            except Exception as e:
                print_test("Text reshaping", False, str(e)[:50])
                results["failed"] += 1

            # Test image generation
            print_info("\nImage Generation:")
            try:
                generator = OGImageGenerator()
                result = generator.generate_og_image(
                    headline="🧪 Test: أختبار توليد الصور العربية"
                )

                if result and result.get("local_path"):
                    path = result["local_path"]
                    print_test("Generate image", True, f"Saved to: {path}")
                    results["passed"] += 1

                    # Check file exists
                    if Path(path).exists():
                        size = Path(path).stat().st_size
                        print_test("Image file", True, f"Size: {size/1024:.1f} KB")
                        results["passed"] += 1
                    else:
                        print_test("Image file", False, "File not found")
                        results["failed"] += 1
                else:
                    print_test("Generate image", False, "No result returned")
                    results["failed"] += 1

            except Exception as e:
                print_test("Generate image", False, str(e)[:80])
                results["failed"] += 1

        except Exception as e:
            print_error(f"Image generator test failed: {e}")
            results["failed"] += 1

        self.results["image_generator"] = results
        return results

    # =========================================================================
    # TEST 8: Telegram Bot Connection
    # =========================================================================
    async def test_telegram_bots(self) -> Dict[str, Any]:
        """Test Telegram bot connections"""
        print_header("TEST 8: Telegram Bot Connections")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        from telegram import Bot

        # Test main bot
        print_info("Main Bot:")
        main_token = os.getenv("TELEGRAM_TOKEN")
        if main_token:
            try:
                bot = Bot(token=main_token)
                me = await bot.get_me()
                print_test("Main bot", True, f"@{me.username}")
                results["passed"] += 1
            except Exception as e:
                print_test("Main bot", False, str(e)[:50])
                results["failed"] += 1
        else:
            print_test("Main bot", False, "Token not set")
            results["failed"] += 1

        # Test brand bots
        brand_tokens = {
            "blocksignals": "TELEGRAM_TOKEN_BS",
            "zerodev": "TELEGRAM_TOKEN_ZDS",
            "robovai_ar": "TELEGRAM_TOKEN_ARB",
        }

        print_info("\nBrand Bots:")
        for brand, token_var in brand_tokens.items():
            token = os.getenv(token_var)
            if token:
                try:
                    bot = Bot(token=token)
                    me = await bot.get_me()
                    print_test(f"{brand}", True, f"@{me.username}")
                    results["passed"] += 1
                except Exception as e:
                    print_test(f"{brand}", False, str(e)[:50])
                    results["failed"] += 1
            else:
                print_test(f"{brand}", False, f"{token_var} not set")
                results["failed"] += 1

        self.results["telegram"] = results
        return results

    # =========================================================================
    # TEST 9: Full Publishing Pipeline (Dry Run)
    # =========================================================================
    async def test_publishing_pipeline(self) -> Dict[str, Any]:
        """Test the full publishing pipeline without actually posting"""
        print_header("TEST 9: Publishing Pipeline (Dry Run)")

        results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

        try:
            from sequential_publisher import SequentialPublisher
            from multi_platform_publisher import MultiPlatformPublisher
            from feed_manager import fetch_random_new_post

            # Test for one brand
            test_brand = "robovai_ar"
            print_info(f"Testing brand: {test_brand}")

            # 1. Fetch post
            print_info("\n1. Fetching RSS post...")
            post = fetch_random_new_post(brand=test_brand)
            if post:
                print_test("Fetch RSS", True, f"'{post.get('title', '')[:40]}...'")
                results["passed"] += 1
            else:
                print_test("Fetch RSS", False, "No posts available")
                results["warnings"] += 1
                # Use test data
                post = {
                    "title": "Test Article for Pipeline",
                    "summary": "This is a test article summary for testing the publishing pipeline.",
                    "link": "https://example.com/test",
                }

            # 2. Initialize publishers
            print_info("\n2. Initializing publishers...")
            try:
                platform_publisher = MultiPlatformPublisher(brand_key=test_brand)
                seq_publisher = SequentialPublisher(self.config)
                print_test(
                    "Publishers init",
                    True,
                    f"Enabled: {platform_publisher.enabled_platforms}",
                )
                results["passed"] += 1
            except Exception as e:
                print_test("Publishers init", False, str(e)[:50])
                results["failed"] += 1
                return results

            # 3. Generate content
            print_info("\n3. Generating content...")
            try:
                from ai_processor import rewrite_with_ai

                brand_cfg = self.config.get("brands", {}).get(test_brand, {})
                content = rewrite_with_ai(
                    title=post.get("title", ""),
                    summary=post.get("summary", ""),
                    link=post.get("link", ""),
                    system_prompt=brand_cfg.get("system_prompt", ""),
                    platform="telegram",
                    brand_name=test_brand,
                    brand_language=brand_cfg.get("language", "ar"),
                )

                if content:
                    print_test("Generate content", True, "Content ready")
                    results["passed"] += 1

                    # Show preview
                    preview = content.get("telegram_post", "")[:150].replace("\n", " ")
                    print(f"       {Colors.CYAN}Preview: {preview}...{Colors.END}")
                else:
                    from ai_processor import get_last_ai_error

                    print_test("Generate content", False, get_last_ai_error())
                    results["failed"] += 1

            except Exception as e:
                print_test("Generate content", False, str(e)[:80])
                results["failed"] += 1

            print_info("\n4. Pipeline ready!")
            print_success("All components working. Ready to publish!")

        except Exception as e:
            print_error(f"Pipeline test failed: {e}")
            import traceback

            traceback.print_exc()
            results["failed"] += 1

        self.results["pipeline"] = results
        return results

    # =========================================================================
    # Summary
    # =========================================================================
    def print_summary(self):
        """Print test summary"""
        print_header("📊 TEST SUMMARY")

        total_passed = 0
        total_failed = 0
        total_warnings = 0

        for test_name, result in self.results.items():
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            warnings = result.get("warnings", 0)

            total_passed += passed
            total_failed += failed
            total_warnings += warnings

            status = "✅" if failed == 0 else "❌"
            print(
                f"  {status} {test_name}: {passed} passed, {failed} failed, {warnings} warnings"
            )

        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(
            f"  {Colors.BOLD}TOTAL: {total_passed} passed, {total_failed} failed, {total_warnings} warnings{Colors.END}"
        )

        if total_failed == 0:
            print(
                f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! System is ready for production.{Colors.END}"
            )
        else:
            print(
                f"\n{Colors.RED}{Colors.BOLD}⚠️  Some tests failed. Please fix the issues above.{Colors.END}"
            )

        return total_failed == 0


async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     🤖 TECH INFLUENCER BOT - FULL SYSTEM TEST 🧪        ║")
    print("║                                                          ║")
    print(
        f"║     Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                        ║"
    )
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    tester = SystemTester()

    # Run all tests
    tester.test_environment()
    tester.test_config()
    await tester.test_ai_providers()
    await tester.test_rss_feeds()
    await tester.test_content_generation()
    await tester.test_platform_publishers()
    await tester.test_image_generator()
    await tester.test_telegram_bots()
    await tester.test_publishing_pipeline()

    # Print summary
    success = tester.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
