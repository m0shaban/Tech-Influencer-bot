"""
RoboVAI AI Brain Module V3 (Enterprise Edition)
Handles intelligent content generation with Chain-Of-Thought processing.
Features:
- Surgical JSON Extraction
- Platform-Specific Optimization
- Recursive Fallback Strategies
- Strict Arabic Enforcement
"""

import json
import os
import re
import logging
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv

# Use standard OpenAI client (compatible with Googel/Groq)
from openai import OpenAI
from ai_provider_manager import AIProviderManager

load_dotenv()

# Logger settings
logger = logging.getLogger("ai_processor")
logger.setLevel(logging.INFO)

# --- Configuration ---
# Priority List: Powerful models first, fast models as fallback
DEFAULT_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",  # Smartest open model
    "mixtral-8x7b-32768",  # Huge context
    "llama-3.1-8b-instant",  # Fastest fallback
]

# The "Brain" Instructions - Chain of Thought injected
CHAIN_OF_THOUGHT_PROMPT = """
Start by thinking step-by-step:
1. Analyze the input news: What is the core value? Who is the audience?
2. Extract key technical details (terms, versions, impact).
3. Plan the Blog Post:
   - Catchy Title (Arabic SEO Optimized).
   - Introduction: Hook the reader with a "Why this matters" angle.
   - Body: 3-5 clear points using H2/H3 headers.
   - Conclusion: Summary + Call to Action.
4. Plan Social Posts:
   - Facebook: Storytelling hook.
   - Telegram: Urgent/Exclusive summary.
5. Review: Does this sound like a human expert (RoboVAI)?

OUTPUT ONLY THE FINAL JSON.
"""

SYSTEM_PERSONA = """
أنت 'RoboVAI' (محمد شعبان)، الخبير التقني الأول في الشرق الأوسط.
شخصيتك:
- ذكي جداً ومطلع على أحدث التقنيات.
- تتحدث باللغة العربية الفصحى السلسة (Modern Standard Arabic).
- تكره الحشو والكلام الذي لا معنى له.
- تحب الأمثلة العملية والأكواد (إذا وجدت).
- تستخدم Markdown ببراعة لتنسيق المقالات.

مهمتك:
تحويل الخبر التقني الجاف إلى "درس ممتع" ومقالة احترافية.
"""

REQUIRED_JSON_SCHEMA = """
{
  "blog_title": "العنوان المقترح للمقال (جذاب و SEO)",
  "blog_meta_description": "وصف قصير لمحركات البحث (150 حرف)",
  "blog_content_md": "المقال كاملاً بتنسيق Markdown (مقدمة، عناوين H2، نقاط، خاتمة)",
  "facebook_post": "منشور فيسبوك (قصة + تشويق) - بدون روابط",
  "telegram_post": "ملخص تليجرام (خبر عاجل + نقاط) - بدون روابط",
  "keywords": ["tag1", "tag2", "tag3"]
}
"""

# Global Client Instance
_client: Optional[OpenAI] = None


def _get_client() -> Optional[OpenAI]:
    """Initialize OpenAI Client for Groq/External Providers"""
    global _client
    if _client:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("❌ Missing GROQ_API_KEY")
        return None

    _client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    return _client


def _extract_json_surgically(text: str) -> Optional[Dict[str, Any]]:
    """
    Advanced regex-based parser to find JSON objects inside messy text.
    Handles common LLM errors like markdown fences, extra text, etc.
    """
    if not text:
        return None

    # Cleaning: Removing Markdown Code Fences
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

    # Attempt 1: Standard Load
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Regex Extraction of largest {} block
    try:
        matches = re.findall(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", text, re.DOTALL)
        if matches:
            # Sort by length, assume the longest one is the main JSON
            longest_match = max(matches, key=len)
            return json.loads(longest_match)
    except Exception as e:
        logger.debug(f"Regex JSON extraction failed: {e}")

    # Attempt 3: Fix bad newlines in strings (Common LLM error)
    try:
        # Escape unescaped newlines inside quotes is very hard with regex safely.
        # instead, try `eval` safe approach (AST) if desperate? No, too risky.
        pass
    except:
        pass

    logger.error("❌ Failed to parse JSON from AI response.")
    return None


def rewrite_with_ai(
    title: str,
    summary: str,
    link: str,
    system_prompt: Optional[str] = None,
    brand_name: str = "RoboVAI",
    brand_language: str = "ar",
) -> Optional[Dict[str, Any]]:
    """
    Main Processor: Takes raw news -> Returns structured Gold Content.
    """

    client = _get_client()
    if not client:
        return None

    # Construct the Mega Prompt
    full_prompt = f"""
    {SYSTEM_PERSONA}
    
    {CHAIN_OF_THOUGHT_PROMPT}

    INPUT DATA:
    - Title: {title}
    - Summary source: {summary}
    - Link: {link}

    STRICT RULES:
    1. Output MUST be valid JSON only. No chatting.
    2. Language: ARABIC ONLY (العربية).
    3. Blog length: Minimum 800 words.
    4. Use Emoji 🤖 properly.
    
    {REQUIRED_JSON_SCHEMA}
    """

    for model in DEFAULT_MODEL_CANDIDATES:
        try:
            logger.info(f"🧠 Thinking with model: {model}...")

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": full_prompt},
                    {
                        "role": "user",
                        "content": "Generate the content now. JSON format.",
                    },
                ],
                model=model,
                temperature=0.6,  # Slightly creative but focused
                max_tokens=3500,  # Large buffer for long articles
                response_format={"type": "json_object"},  # Force JSON mode if supported
            )

            response_text = chat_completion.choices[0].message.content

            # Parse result
            parsed_data = _extract_json_surgically(response_text)

            if parsed_data:
                # Validate critical fields
                if "blog_content_md" in parsed_data:
                    # Check word count roughly
                    word_count = len(parsed_data["blog_content_md"].split())
                    logger.info(f"✅ Generated Content: {word_count} words")
                    return parsed_data
                else:
                    logger.warning(f"⚠️ Model {model} returned JSON but missing keys.")

        except Exception as e:
            logger.error(f"⚠️ Error with model {model}: {e}")
            continue  # Try next model

    logger.error("❌ All AI models failed to generate valid content.")
    return None


# Self-Test
if __name__ == "__main__":
    print("Testing AI Brain...")
    res = rewrite_with_ai(
        "Python 3.13 Released",
        "New features include JIT compiler and removal of GIL.",
        "http://python.org",
    )
    if res:
        print("✅ Success!")
        print("Title:", res.get("blog_title"))
        print("Snippet:", res.get("blog_content_md")[:100])
    else:
        print("❌ Failed.")
