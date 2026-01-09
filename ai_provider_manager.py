"""
AI Provider Manager - Multi-AI Strategy
Intelligently routes content generation to best-suited AI providers
"""

import os
import random
from typing import Optional, Dict, Any, List
from openai import OpenAI


class AIProviderManager:
    """Manages multiple AI providers with intelligent routing"""

    def __init__(self):
        self.groq_keys = self._load_groq_keys()
        self.nvidia_keys = self._load_nvidia_keys()

        # Provider configurations
        self.providers = {
            # Deep reasoning for long-form content (Blogger, Dev.to)
            "reasoning": {
                "provider": "nvidia",
                "models": [
                    "nvidia/nemotron-3-nano-30b-a3b",
                    "deepseek-ai/deepseek-v3.1-terminus",
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
                    "llama-3.1-8b-instant",
                    "llama-3.3-70b-versatile",
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

    def get_provider_for_platform(self, platform: str) -> Dict[str, Any]:
        """Get best AI provider configuration for a platform"""
        # Find matching provider
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
            return random.choice(self.groq_keys) if self.groq_keys else None
        elif provider == "nvidia":
            return random.choice(self.nvidia_keys) if self.nvidia_keys else None
        return None

    def generate_content(
        self,
        platform: str,
        system_prompt: str,
        user_prompt: str,
        enable_reasoning: bool = False,
    ) -> Optional[str]:
        """Generate content using best provider for platform"""
        config = self.get_provider_for_platform(platform)

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
                "response_format": {"type": "json_object"},
            }

            # Enable reasoning for deep content (Blogger, Dev.to)
            if enable_reasoning and config["provider"] == "nvidia":
                if "nemotron" in config["model"]:
                    params["extra_body"] = {
                        "reasoning_budget": 8192,
                        "chat_template_kwargs": {"enable_thinking": True},
                    }
                elif "deepseek" in config["model"]:
                    params["extra_body"] = {"chat_template_kwargs": {"thinking": True}}

            print(f"🤖 Using {config['provider']} ({config['model']}) for {platform}")

            response = client.chat.completions.create(**params)
            content = response.choices[0].message.content

            return content

        except Exception as e:
            print(f"❌ AI generation failed for {platform}: {e}")
            return None


# Global instance
_manager: Optional[AIProviderManager] = None


def get_ai_manager() -> AIProviderManager:
    """Get or create AI Provider Manager"""
    global _manager
    if _manager is None:
        _manager = AIProviderManager()
    return _manager
