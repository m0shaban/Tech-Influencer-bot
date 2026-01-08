import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI


DEFAULT_SYSTEM_PROMPT = r"""
You are RoboVAI (Mohamed Shaban), Egypt's top Tech Career Mentor & Content Creator.

Input: a tech link/topic with title + short summary.
Output: ONE JSON object with 4 distinct content pieces optimized per platform.

GLOBAL RULES:
- Tone: Egyptian Business Arabic (White Accent). Smart, witty, professional.
- No copy-paste: Create new value (roadmaps, tips, explanations, practical steps).
- English ONLY for technical terms (e.g., Docker, LLM, Kubernetes).
- Do NOT use phrases like: "Based on the article", "In conclusion", "بناءً على", "في الختام".

PLATFORM 1: TELEGRAM (Friend vibe) ✈️
- Short, punchy, conversational.
- No section headers like "Conclusion".
- Format: Hook -> Story/Insight -> Tip -> Link at bottom.
- Emojis used naturally.

PLATFORM 2: FACEBOOK (Viral vibe) 📘
- Longer than Telegram.
- Great hook that stops scroll (e.g., "غلطة كلنا بنقع فيها...").
- Spacing for readability.
- Ask for engagement (tag/share/comment).
- Problem vs Solution framing.

PLATFORM 3: BLOG (Dev.to / Blogger) 📝
- Full educational Markdown article.
- 400-600 words.
- SEO Arabic title.
- Structure: Intro, H2 sections, bullets, code blocks ONLY if relevant.
- Include action plan.

PLATFORM 4: DISCORD (Community vibe) 👾
- Quick alert, casual hype.
- Format: "Hey @everyone! 🚨 ... Let's discuss in #general".

OUTPUT JSON STRUCTURE (ONLY JSON; no markdown wrapper):
{
  "telegram_post": "string",
  "facebook_post": "string",
  "blog_title": "string",
  "blog_content_md": "string",
  "discord_msg": "string",
  "has_poll": true/false,
  "poll_question": "string",
  "poll_options": ["Option 1", "Option 2", "Option 3"]
}
"""


DEFAULT_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
]

DEFAULT_MAX_TOKENS = 2600
DEFAULT_TEMPERATURE = 0.35

_client: Optional[OpenAI] = None
_last_error: Optional[str] = None


def get_last_ai_error() -> Optional[str]:
    return _last_error


def _set_last_error(message: Optional[str]) -> None:
    global _last_error  # noqa: PLW0603
    _last_error = message


def _get_client() -> Optional[OpenAI]:
    global _client  # noqa: PLW0603
    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        _set_last_error("Missing GROQ_API_KEY")
        return None

    _client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    return _client


def _parse_json_response(content: str) -> Optional[Dict[str, Any]]:
    cleaned = (content or "").strip()
    if not cleaned:
        return None

    def _try_parse(text: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    direct = _try_parse(cleaned)
    if direct is not None:
        return direct

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return _try_parse(cleaned[start : end + 1])


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "1"}:
            return True
        if v in {"false", "no", "0"}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    return None


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    # Only remove start/end fences if they wrap the entire content,
    # or just remove all backticks if that's safer.
    # But usually we just want to strip the outer markdown block if present.
    # Let's just remove the fence markers but keep content.
    s = text.strip()
    if s.startswith("```"):
        # Remove first line starting with ```
        s = re.sub(r"^```\w*\s*\n?", "", s)
    if s.endswith("```"):
        # Remove last ```
        s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def _latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    latin_chars = re.findall(r"[A-Za-z]", text)
    total_chars = re.findall(r"[A-Za-z\u0600-\u06FF0-9]", text)
    if not total_chars:
        return 0.0
    return len(latin_chars) / len(total_chars)


_BANNED_PHRASES = [
    "based on the article",
    "in conclusion",
    "في الختام",
]


def _contains_banned_phrases(text: str) -> bool:
    lowered = (text or "").lower()
    return any(p in lowered for p in _BANNED_PHRASES)


def _ensure_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_ai_result(
    parsed: Dict[str, Any], *, link: str
) -> Dict[str, Any]:
    telegram_post = _strip_code_fences(_ensure_string(parsed.get("telegram_post")))
    facebook_post = _strip_code_fences(_ensure_string(parsed.get("facebook_post")))
    blog_title = _ensure_string(parsed.get("blog_title"))
    blog_content_md = _strip_code_fences(_ensure_string(parsed.get("blog_content_md")))
    discord_msg = _strip_code_fences(_ensure_string(parsed.get("discord_msg")))

    # --- FLUID FALLBACKS (Robust Recovery) ---
    # 1. Gather any valid text content found
    sources = [t for t in [telegram_post, facebook_post, blog_content_md, discord_msg] if t]

    # 2. If completely empty, try looking at ALL dict values (in case of wrong keys)
    if not sources:
        sources = [str(v) for v in parsed.values() if isinstance(v, str) and v.strip()]

    if not sources:
        raise ValueError(f"AI output contained no usable text content. Keys: {list(parsed.keys())}")

    fallback_text = sources[0]

    # 3. Fill missing fields with fallback content
    if not telegram_post: telegram_post = fallback_text
    if not facebook_post: facebook_post = telegram_post
    if not blog_content_md: blog_content_md = telegram_post
    if not discord_msg: discord_msg = telegram_post
    if not blog_title:
        # Extract potential title from first line of content
        first_line = fallback_text.split('\n')[0].strip()
        # Remove markdown headers if present
        blog_title = re.sub(r'^[\#\*]+', '', first_line).strip() or "Tech Update"

    joined = "\n".join(
        [telegram_post, facebook_post, blog_title, blog_content_md, discord_msg]
    )
    if _contains_banned_phrases(joined):
        raise ValueError("Content contains banned phrases")

    latin_fraction = _latin_ratio(joined)
    if latin_fraction > 0.75:
        raise ValueError(f"Language skew detected (latin ratio: {latin_fraction:.2f} > 0.75)")

    # Ensure the link exists (main pipeline may append again safely).
    if link and link not in telegram_post:
        telegram_post = telegram_post.rstrip() + f"\n\n{link}"
    if link and link not in facebook_post:
        facebook_post = facebook_post.rstrip() + f"\n\n{link}"
    if link and link not in discord_msg:
        discord_msg = discord_msg.rstrip() + f"\n{link}"

    has_poll = _coerce_bool(parsed.get("has_poll"))
    if has_poll is None:
        has_poll = False
    poll_question = _ensure_string(parsed.get("poll_question"))
    poll_options_raw = parsed.get("poll_options")
    poll_options: list[str] = []
    if isinstance(poll_options_raw, list):
        poll_options = [str(o).strip() for o in poll_options_raw if str(o).strip()]

    return {
        "telegram_post": telegram_post,
        "facebook_post": facebook_post,
        "blog_title": blog_title,
        "blog_content_md": blog_content_md,
        "discord_msg": discord_msg,
        "has_poll": bool(has_poll),
        "poll_question": poll_question,
        "poll_options": poll_options,
    }


def rewrite_with_ai(
    title: str,
    summary: str,
    link: str,
    system_prompt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Generate per-platform content as a single JSON object."""
    _set_last_error(None)
    client = _get_client()
    if client is None:
        return None

    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT

    user_content = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Link: {link}\n\n"
        "Return ONLY the JSON object with the required keys."
    )

    raw_models = (os.getenv("GROQ_MODELS") or "").strip()
    env_models: list[str] = []
    if raw_models:
        env_models = [m.strip() for m in raw_models.split(",") if m.strip()]
    else:
        single = (os.getenv("GROQ_MODEL") or "").strip()
        if single:
            env_models = [single]

    model_candidates = [*env_models, *DEFAULT_MODEL_CANDIDATES]
    seen_models: set[str] = set()
    model_candidates = [
        m for m in model_candidates if not (m in seen_models or seen_models.add(m))
    ]

    last_error: Optional[str] = None
    for model_name in model_candidates:
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": effective_system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "0") or 0)
                or DEFAULT_MAX_TOKENS,
                temperature=float(os.getenv("GROQ_TEMPERATURE", "0") or 0)
                or DEFAULT_TEMPERATURE,
                response_format={"type": "json_object"},
            )

            content = resp.choices[0].message.content if resp and resp.choices else None
            if not content:
                _set_last_error(f"Empty AI response (model={model_name})")
                return None

            parsed = _parse_json_response(content)
            if parsed is None:
                snippet = content.strip().replace("\n", " ")
                _set_last_error(
                    f"Invalid JSON from AI (model={model_name}): {snippet[:180]}"
                )
                return None

            try:
                normalized = _normalize_ai_result(parsed, link=link)
                return normalized
            except ValueError as ve:
                _set_last_error(f"AI Validation Error ({model_name}): {ve}")
                return None

        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            msg = str(getattr(exc, "message", "") or "")
            base = f"{type(exc).__name__}"
            if status is not None:
                base += f" (HTTP {status})"
            detail = (msg or str(exc) or "").strip()
            if detail:
                base += f": {detail}"
            last_error = f"{base} (model={model_name})"[:300]

            # Retry once for Groq JSON validation failures
            if "json_validate_failed" in detail.lower():
                try:
                    resp = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": effective_system_prompt},
                            {
                                "role": "user",
                                "content": user_content
                                + "\nReturn valid JSON ONLY with keys: telegram_post, facebook_post, blog_title, blog_content_md, discord_msg, has_poll, poll_question, poll_options.",
                            },
                        ],
                        max_tokens=max(400, DEFAULT_MAX_TOKENS - 200),
                        temperature=0.2,
                        response_format={"type": "json_object"},
                    )
                    content = (
                        resp.choices[0].message.content
                        if resp and resp.choices
                        else None
                    )
                    parsed = _parse_json_response(content or "")
                    if parsed:
                        normalized = _normalize_ai_result(parsed, link=link)
                        if normalized is not None:
                            return normalized
                except Exception:
                    pass

            lowered = detail.lower()
            if (
                "decommissioned" in lowered
                or "no longer supported" in lowered
                or "not found" in lowered
            ):
                continue
            _set_last_error(last_error)
            return None

    _set_last_error(last_error or "AI request failed")
    return None
