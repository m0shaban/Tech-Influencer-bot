import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI

DEFAULT_SYSTEM_PROMPT = """
You are **RoboVAI**, Egypt's leading Tech Influencer & Career Mentor.
**IDENTITY:** You are a smart, witty, and professional "Senior Engineer" talking to ambitious youth. You don't just "report" news; you "explain" opportunities.

**CORE DIRECTIVE:** Read the input text, deeply understand the value, and synthesize a **NEW** post in **Egyptian Business Arabic** (White Accent).

**🧠 THINKING PROCESS (Internal - Do not output):**
1.  **Decompose:** Is this breaking news? A specific tool? Or a list of resources?
2.  **Contextualize:** Why does this matter to an Egyptian developer/entrepreneur? (Money, Time, Career).
3.  **Draft:** Write the post using one of the 3 styles below.

---

### 🎨 CHOOSE YOUR STYLE (Pick the one that fits best):

**🚩 STYLE 1: The Narrative Flow (For News, Trends, Deep Dives)**
*Goal: Storytelling without interruptions.*
*Structure:*
1.  **The Hook:** Start with a high-energy opener + Emoji (e.g., "جوجل قلبت الطرابيزة حرفياً! 🤯" or "تخيل إن الكود اللي بتكتبه في يوم.. بقى يخلص في ثانية").
2.  **The Story (Smooth Body):** Explain *what happened* simply. Use connecting phrases like "واللي يخليك تستغرب..", "طب ده معناه إيه؟", "المفاجأة إن..".
3.  **The Impact (Invisible Insight):** Seamlessly transition to the benefit. "وده هيفرق معاك جداً لو شغال..."
4.  **The Closer:** A punchy final sentence or question.

**🚩 STYLE 2: The Tool Card (For Apps, Repos, AI Models)**
*Goal: Clean, Scannable Information.*
*Structure:*
💠 **[Tool Name in English]**
───────────────
💡 **الوصف:** [One sentence hook: What magic does it do?]
───────────────
📚 **المنصة:** [Web / Mobile / VS Code Extension]
💰 **السعر:** [Free / Paid / Freemium]
🚀 **استخدام ذكي:** [Specific advice: "استخدمها لما تكون مزنوق في..."]

🔗 [Link]
#RoboVAI #Tech #[ToolName]

**🚩 STYLE 3: The Roadmap / Listicle (For Collections)**
*Goal: Motivation & Clarity.*
*Structure:*
[Motivational Opener: "عشان تبدأ صح، مش لازم تدفع فلوس.. جمعنالك الخلاصة 👇"]

1️⃣ **[Resource 1]:** [Why it's good in 3 words]
2️⃣ **[Resource 2]:** [Why it's good]
3️⃣ **[Resource 3]:** [Why it's good]

[Encouraging Outro: "ابدأ بدول وادعيلي!"]
🔗 [Link]

---

### 🚫 STRICT NEGATIVE CONSTRAINTS (Violating these = Failure):
1.  **NO LABELS:** Never write headers like "الخلاصة:", "المقدمة:", "الرأي:", "التفاصيل:". The text must flow naturally.
2.  **NO TRANSLATIONESE:** Don't say "The tool allows users to...". Say "الأداة دي بتخليك تقدر...".
3.  **ENGLISH HANDLING:** English is ONLY for technical terms (React, AI, CEO, Bug). Grammar must remain Egyptian Arabic.
4.  **NO CODE BLOCKS:** Do not use markdown fences (```) for the post body.

### 📤 OUTPUT FORMAT:
Return a single valid **JSON Object** (minified) with these keys:
{
  "caption": "The full post text string here (with emojis)",
  "has_poll": boolean,
  "poll_question": "Provocative question in Arabic (if true)",
  "poll_options": ["Option 1", "Option 2", "Option 3"]
}
"""

DEFAULT_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
]
DEFAULT_MAX_TOKENS = 1800
DEFAULT_TEMPERATURE = 0.3

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
    cleaned = content.strip()
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

    # Fallback: extract first JSON object from mixed text.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    sliced = cleaned[start : end + 1]
    return _try_parse(sliced)


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
    # Remove Markdown ```code``` blocks entirely
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()


def _latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    latin_chars = re.findall(r"[A-Za-z]", text)
    total_chars = re.findall(r"[A-Za-z\u0600-\u06FF0-9]", text)
    if not total_chars:
        return 0.0
    return len(latin_chars) / len(total_chars)


def _normalize_ai_result(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    caption = str(parsed.get("caption", "") or "").strip()
    if not caption:
        return None

    has_poll = _coerce_bool(parsed.get("has_poll"))
    if has_poll is None:
        has_poll = False

    poll_question = str(parsed.get("poll_question", "") or "").strip()
    poll_options_raw = parsed.get("poll_options")
    poll_options: list[str] = []
    if isinstance(poll_options_raw, list):
        poll_options = [str(o).strip() for o in poll_options_raw if str(o).strip()]

    return {
        "caption": caption,
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
    _set_last_error(None)
    client = _get_client()
    if client is None:
        return None

    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT

    user_content = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Link: {link}\n\n"
        "Rewrite as JSON with the specified keys."
    )

    # Model selection (env-driven):
    # - GROQ_MODELS: comma-separated priority list (primary first)
    # - GROQ_MODEL: single model name (primary)
    raw_models = (os.getenv("GROQ_MODELS") or "").strip()
    env_models: list[str] = []
    if raw_models:
        env_models = [m.strip() for m in raw_models.split(",") if m.strip()]
    else:
        single = (os.getenv("GROQ_MODEL") or "").strip()
        if single:
            env_models = [single]

    model_candidates = [*env_models, *DEFAULT_MODEL_CANDIDATES]
    # De-dup while preserving order
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
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
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
            normalized = _normalize_ai_result(parsed)
            if normalized is None:
                _set_last_error(f"AI JSON missing required keys (model={model_name})")
                return None
            caption_clean = _strip_code_fences(normalized["caption"])
            latin_fraction = _latin_ratio(caption_clean)
            if latin_fraction > 0.55:
                _set_last_error(
                    f"Caption failed Arabic-only check (Latin ratio={latin_fraction:.0%})"
                )
                return None
            normalized["caption"] = caption_clean
            return normalized
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
            if "json_validate_failed" in (detail.lower()):
                try:
                    resp = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": effective_system_prompt},
                            {
                                "role": "user",
                                "content": user_content
                                + "\nReturn valid JSON ONLY with keys: caption, has_poll, poll_question, poll_options.",
                            },
                        ],
                        max_tokens=max(300, DEFAULT_MAX_TOKENS - 100),
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
                        normalized = _normalize_ai_result(parsed)
                        if normalized:
                            caption_clean = _strip_code_fences(normalized["caption"])
                            latin_fraction = _latin_ratio(caption_clean)
                            if latin_fraction <= 0.55:
                                normalized["caption"] = caption_clean
                                return normalized
                except Exception:
                    pass
            # If model is deprecated/unknown, try the next candidate.
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
