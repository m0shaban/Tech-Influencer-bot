"""
AI Provider Manager - Multi-AI Strategy
Intelligently routes content generation to best-suited AI providers
"""

import os
import random
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIProviderManager:
    """Manages multiple AI providers with intelligent routing"""

    def __init__(self):
        self.groq_keys = self._load_groq_keys()
        self.nvidia_keys = self._load_nvidia_keys()
        self.groq_rotation_index = 0  # For round-robin
        self.key_health = {}  # Track key health

        # Initialize health tracking
        for key in self.groq_keys:
            self.key_health[key] = {"requests": 0, "errors": 0, "last_error": None}

        # Provider configurations
        self.providers = {
            # Deep reasoning for long-form content (Blogger, Dev.to)
            "reasoning": {
                "provider": "nvidia",
                "models": [
                    "deepseek-ai/deepseek-r1",
                    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
                ],
                "base_url": "https://integrate.api.nvidia.com/v1",
                "max_tokens": 8192,
                "temperature": 0.3,
                "use_for": ["blogger", "devto"],
            },
            # Fast multilingual generation (Facebook, Discord)
            "fast_multilingual": {
                "provider": "groq",
                "models": [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile",
                ],
                "base_url": "https://api.groq.com/openai/v1",
                "max_tokens": 3000,
                "temperature": 0.7,
                "use_for": ["facebook", "discord"],
            },
            # Ultra-fast for Telegram
            "ultra_fast": {
                "provider": "groq",
                "models": [
                    "llama-3.3-70b-versatile",
                    "meta-llama/llama-4-scout-17b-16e-instruct",
                ],
                "base_url": "https://api.groq.com/openai/v1",
                "max_tokens": 1024,
                "temperature": 0.8,
                "use_for": ["telegram"],
            },
        }

    def _load_groq_keys(self) -> List[str]:
        """Load all available Groq API keys"""
        keys = []
        for i in range(1, 10):  # Check GROQ_API_KEY, GROQ_API_KEY_2, etc.
            key_name = f"GROQ_API_KEY_{i}" if i > 1 else "GROQ_API_KEY"
            key = os.getenv(key_name)
            if key:
                keys.append(key)
        return keys

    def _load_nvidia_keys(self) -> List[str]:
        """Load all available NVIDIA API keys"""
        keys = []
        for key_name in ["NVIDIA_API_KEY", "NVIDIA_API_KEY_DEEPSEEK"]:
            key = os.getenv(key_name)
            if key:
                keys.append(key)
        return keys

    def get_provider_for_platform(
        self, platform: str, brand_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Get best AI provider configuration for platform + language

        Args:
            platform: Target platform (blogger, telegram, devto, facebook, discord)
            brand_language: Brand language (en, ar)

        Returns:
            Provider config with model, API key, temperature, etc.
        """
        # ARABIC OVERRIDE: Force Groq Llama3-70b for quality Arabic
        if brand_language == "ar":
            config = self.providers["fast_multilingual"]
            return {
                "strategy": "fast_multilingual_ar",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",  # Best Arabic model
                "base_url": config["base_url"],
                "api_key": self._get_next_groq_key(),  # Round-robin
                "max_tokens": 3000 if platform != "telegram" else 1024,
                "temperature": 0.65,  # More creative for natural dialect
            }

        # Find matching provider for English content
        for strategy_name, config in self.providers.items():
            if platform in config["use_for"]:
                return {
                    "strategy": strategy_name,
                    "provider": config["provider"],
                    "model": random.choice(config["models"]),
                    "base_url": config["base_url"],
                    "api_key": self._get_api_key(config["provider"]),
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                }

        # Fallback to fast_multilingual
        config = self.providers["fast_multilingual"]
        return {
            "strategy": "fast_multilingual",
            "provider": config["provider"],
            "model": random.choice(config["models"]),
            "base_url": config["base_url"],
            "api_key": self._get_api_key(config["provider"]),
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
        }

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get random API key for load balancing"""
        if provider == "groq":
            return self._get_next_groq_key()
        elif provider == "nvidia":
            return random.choice(self.nvidia_keys) if self.nvidia_keys else None
        return None

    def _get_next_groq_key(self) -> Optional[str]:
        """Get next Groq key with round-robin strategy"""
        if not self.groq_keys:
            return None

        attempts = 0
        while attempts < len(self.groq_keys):
            key = self.groq_keys[self.groq_rotation_index]
            self.groq_rotation_index = (self.groq_rotation_index + 1) % len(
                self.groq_keys
            )

            # Skip keys with too many recent errors (> 5)
            if self.key_health.get(key, {}).get("errors", 0) < 5:
                return key

            attempts += 1

        # All keys have errors - reset health and try first key
        print("⚠️ All Groq keys have errors - resetting health counters")
        for key in self.key_health:
            self.key_health[key]["errors"] = 0

        return self.groq_keys[0] if self.groq_keys else None

    def generate_content(
        self,
        platform: str,
        system_prompt: str,
        user_prompt: str,
        enable_reasoning: bool = False,
        brand_language: str = "en",  # NEW: Language awareness
    ) -> Optional[str]:
        """
        Generate content using best provider for platform

        Args:
            platform: Target platform
            system_prompt: System instructions
            user_prompt: User content
            enable_reasoning: Enable thinking mode for NVIDIA
            brand_language: Brand language (en, ar)

        Returns:
            Generated content or None if failed
        """
        config = self.get_provider_for_platform(platform, brand_language)

        if not config["api_key"]:
            print(f"⚠️ No API key available for {config['provider']}")
            return None

        try:
            client = OpenAI(
                base_url=config["base_url"],
                api_key=config["api_key"],
            )

            # Build request params
            params = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": config["temperature"],
                "max_tokens": config["max_tokens"],
            }

            # Only NVIDIA supports response_format json_object
            # Groq doesn't support this parameter
            if config["provider"] == "nvidia":
                params["response_format"] = {"type": "json_object"}

            # Enable reasoning for deep content (Blogger, Dev.to)
            if enable_reasoning and config["provider"] == "nvidia":
                if "nemotron" in config["model"]:
                    params["extra_body"] = {
                        "reasoning_budget": 8192,
                        "chat_template_kwargs": {"enable_thinking": True},
                    }
                elif "deepseek" in config["model"]:
                    params["extra_body"] = {"chat_template_kwargs": {"thinking": True}}

            print(
                f"🤖 Using {config['provider']} ({config['model']}) for {platform} [{brand_language}]"
            )

            response = client.chat.completions.create(**params)
            content = response.choices[0].message.content

            # Track success
            if config["api_key"] in self.key_health:
                self.key_health[config["api_key"]]["requests"] += 1

            return content

        except Exception as e:
            error_msg = str(e)
            print(f"❌ AI generation failed for {platform}: {error_msg}")

            # Track error for health monitoring
            if config["api_key"] in self.key_health:
                self.key_health[config["api_key"]]["errors"] += 1
                self.key_health[config["api_key"]]["last_error"] = error_msg

            # Check if rate limit error - try fallback
            if "429" in error_msg or "rate" in error_msg.lower():
                print("🔄 Rate limit detected - attempting fallback")
                return self._fallback_to_groq(system_prompt, user_prompt, platform)

            return None

    def _fallback_to_groq(
        self, system_prompt: str, user_prompt: str, platform: str
    ) -> Optional[str]:
        """Fallback to Groq when NVIDIA fails"""
        try:
            groq_key = self._get_next_groq_key()
            if not groq_key:
                return None

            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
            )

            # Use the latest working model
            fallback_model = "llama-3.3-70b-versatile"
            print(f"🔄 Fallback: Using Groq {fallback_model}")

            response = client.chat.completions.create(
                model=fallback_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
                max_tokens=2048,
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ Fallback also failed: {e}")
            return None


# Global instance
_manager: Optional[AIProviderManager] = None


def get_ai_manager() -> AIProviderManager:
    """Get or create AI Provider Manager"""
    global _manager
    if _manager is None:
        _manager = AIProviderManager()
    return _manager
