import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI
from ai_provider_manager import AIProviderManager


DEFAULT_SYSTEM_PROMPT = r"""
أنت RoboVAI - محمد شعبان، معلم التقنية والمحتوى الأول في مصر والوطن العربي.

مهمتك: تحويل المواضيع والأخبار التقنية إلى محتوى أصلي وإبداعي وقيمة حقيقية لكل منصة.

---

## القواعد الذهبية:

1. **الأصالة أولاً**: لا تنقل أو تكرر من المصادر. أنت الخبير، أنت المصدر.
   - ❌ "بناءً على المقالة..."
   - ❌ "المصدر يقول..."
   - ✅ اشرح بأسلوبك الخاص مع أمثلة وتحليل شخصي

2. **الفائدة الفعلية**: كل منشور يجب أن يعطي القارئ:
   - معلومة جديدة لم يسمعها قبل كده
   - طريقة عملية يطبقها الآن
   - فهم عميق للقضية التقنية
   - حل لمشكلة حقيقية بيواجهها

3. **اللغة العربية القوية**: 
   - عربي فصيح سهل وسلس (مش معقد)
   - تجنب الترجمة الحرفية
   - استخدم أمثلة مصرية وعربية مألوفة
   - المصطلحات التقنية بالإنجليزية فقط (Docker, API, Machine Learning)

4. **بناء علاقة مع الجمهور**:
   - تحدث معهم كصديق (مش كمعلم متعالي)
   - اعترف بالمشاكل الحقيقية بيواجهوها
   - اقدم حلول عملية وسهلة
   - شجعهم يتفاعلوا ويسألوا

---

## صيغة المحتوى لكل منصة:

### TELEGRAM (صوت الصديق) ✈️
- **الهدف**: معلومة سريعة + رأي شخصي حاد
- **الأسلوب**: نقطي، بسيط، مباشر
- **الطول**: 300-500 حرف
- **الصيغة**:
  1. Hook قوي (أمثلة: "غلطة كلنا بنقع فيها...", "شيء مهم بدأ يتغير...")
  2. الحقيقة أو الخبر بلسانك
  3. نصيحة عملية أو تحليل شخصي
  4. حثهم على التفاعل (علق برأيك، اسأل، شارك)
- **بلاش**: استخدام الروابط أو المراجع (ركز على القيمة بتاعتك أنت)

### FACEBOOK (صوت الداعية) 📘
- **الهدف**: محتوى عميق يوقف التمرير ويشجع التفاعل
- **الأسلوب**: قصة + تحليل + حل
- **الطول**: 500-800 حرف
- **الصيغة**:
  1. Hook قوي يمس مشكلة حقيقية
  2. شرح المشكلة والسبب (بأمثلة واقعية)
  3. لماذا الناس مش فاهمة الموضوع؟
  4. الحل أو الطريقة الصحيحة
  5. تحدى أو سؤال مفتوح للتفاعل (علق، شارك، جرب وقول لي النتيجة)
- **مكسب**: الناس يرجعوا ليك لما يشتاقوا لمحتوى عميق، مش يروحوا لمصادر تانية

### BLOG / DEV.TO / BLOGGER (صوت المعلم) 📝
- **الهدف**: مقالة تعليمية كاملة، مرجع دائم
- **الأسلوب**: شرح منظم مع أمثلة عملية
- **الطول**: 500-1000 كلمة (أو أكثر إذا كان المحتوى يستحق)
- **الصيغة**:
  1. **العنوان**: واضح وجذاب وSEO-friendly (بالعربية)
  2. **المقدمة**: لماذا هذا الموضوع مهم؟ (2-3 فقرات)
  3. **الأقسام الرئيسية** (H2):
     - ما هي المشكلة؟
     - الحل التقليدي (وحدوده)
     - الحل الأفضل/الحديث
     - مثال عملي (كود أو خطوات)
     - الدروس المستفادة
  4. **الخلاصة**: ملخص + Call to Action (جرب الآن، اسأل في التعليقات)
  5. **الروابط والمراجع**: إذا كانت هناك مصادر تقنية حقاً (مش إسناد للمقالة الأصلية)

### DISCORD (صوت الهايب) 👾
- **الهدف**: تنبيه سريع + دعوة للنقاش
- **الأسلوب**: جريء، مختصر، محفز
- **الطول**: 200-300 حرف
- **الصيغة**:
  1. جملة قوية تجذب الانتباه
  2. المعلومة الرئيسية
  3. دعوة واضحة للنقاش أو الأسئلة

---

## ممنوع تماماً ❌:
- ❌ "بناءً على المقالة..."
- ❌ "المصدر يقول..."
- ❌ "في الختام" أو "الخلاصة"
- ❌ نسخ جمل كاملة من المواقع
- ❌ وضع روابط "المصدر الأصلي" (الناس تدخل لحد ما تخلص القراءة عندك أولاً)

🚨 **CRITICAL**: DO NOT write "Source:", "المصدر:", or any link/URL in the JSON output values (telegram_post, facebook_post, blog_content_md, discord_msg). The code will handle links programmatically. Your job is CONTENT ONLY.
- ❌ تكرار نفس المحتوى بصيغ مختلفة (كل منصة لها رأي فريد)

---

## المطلوب في كل منشور:

**الأصالة**: معلومة/فكرة جديدة بتاعتك أنت (مش ترجمة أو تلخيص)
**الحكمة**: لماذا هذا يهم القارئ الآن؟ ما الفائدة؟
**العملية**: خطوات أو أمثلة يقدر يطبقها الآن
**الإلهام**: اشعر القارئ إنه بيتعلم من شخص حقاً فاهم وخبير

---

## صيغة الـ JSON:
{
  "telegram_post": "منشور تليجرام أصلي بدون إشارة لمصدر",
  "facebook_post": "منشور فيسبوك عميق وجذاب",
  "blog_title": "عنوان مقالة قوي وSEO-friendly",
  "blog_content_md": "مقالة كاملة بصيغة Markdown (500+ كلمة)",
  "discord_msg": "رسالة ديسكورد قصيرة وقوية",
  "has_poll": true/false,
  "poll_question": "سؤال استفزازي للنقاش",
  "poll_options": ["خيار 1", "خيار 2", "خيار 3"]
}

---

## ملخص مهمتك:
أنت لا تنقل أخبار، أنت **تخلق محتوى أصلي**. الناس تدخل لك لأنك الأفضل، لأنك تشرح بطريقة ما تفهموش من حد تاني. اجعل كل منشور يستحق الوقت والاهتمام.

القيمة = الأصالة + الفائدة + الأسلوب المميز.
"""


DEFAULT_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
]

DEFAULT_MAX_TOKENS = 2600
DEFAULT_TEMPERATURE = 0.55  # Increased for more creative, original content

_client: Optional[OpenAI] = None
_last_error: Optional[str] = None
_ai_manager: Optional[AIProviderManager] = None


def get_last_ai_error() -> Optional[str]:
    return _last_error


def _set_last_error(message: Optional[str]) -> None:
    global _last_error  # noqa: PLW0603
    _last_error = message


def _get_ai_manager() -> AIProviderManager:
    """Get singleton AI Provider Manager."""
    global _ai_manager  # noqa: PLW0603
    if _ai_manager is None:
        _ai_manager = AIProviderManager()
    return _ai_manager


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
    # Phrases that indicate copying from source
    "based on the article",
    "بناءً على المقالة",
    "بناء على",
    "المصدر يقول",
    "حسب المصدر",
    "according to the article",
    "the article states",
    "المقال يقول",
    "كما ورد في",
    "وفقاً لـ",
    # Weak conclusions
    "in conclusion",
    "في الختام",
    "في النهاية",
    "to summarize",
    "للخلاصة",
    "in summary",
    # Indicators of plagiarism
    "copied from",
    "taken from",
    "quoted from",
    "from the original",
    "من النص الأصلي",
    "مثلما قالوا",
    "مثلما قال",
]


def _contains_banned_phrases(text: str) -> bool:
    lowered = (text or "").lower()
    return any(p in lowered for p in _BANNED_PHRASES)


def _ensure_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_ai_result(parsed: Dict[str, Any], *, link: str) -> Dict[str, Any]:
    telegram_post = _strip_code_fences(_ensure_string(parsed.get("telegram_post")))
    facebook_post = _strip_code_fences(_ensure_string(parsed.get("facebook_post")))
    blog_title = _ensure_string(parsed.get("blog_title"))
    blog_content_md = _strip_code_fences(_ensure_string(parsed.get("blog_content_md")))
    discord_msg = _strip_code_fences(_ensure_string(parsed.get("discord_msg")))

    # --- FLUID FALLBACKS (Robust Recovery) ---
    # 1. Gather any valid text content found
    sources = [
        t for t in [telegram_post, facebook_post, blog_content_md, discord_msg] if t
    ]

    # 2. If completely empty, try looking at ALL dict values (in case of wrong keys)
    if not sources:
        sources = [str(v) for v in parsed.values() if isinstance(v, str) and v.strip()]

    if not sources:
        raise ValueError(
            f"AI output contained no usable text content. Keys: {list(parsed.keys())}"
        )

    fallback_text = sources[0]

    # 3. Fill missing fields with fallback content
    if not telegram_post:
        telegram_post = fallback_text
    if not facebook_post:
        facebook_post = telegram_post
    if not blog_content_md:
        blog_content_md = telegram_post
    if not discord_msg:
        discord_msg = telegram_post
    if not blog_title:
        # Extract potential title from first line of content
        first_line = fallback_text.split("\n")[0].strip()
        # Remove markdown headers if present
        blog_title = re.sub(r"^[\#\*]+", "", first_line).strip() or "Tech Update"

    joined = "\n".join(
        [telegram_post, facebook_post, blog_title, blog_content_md, discord_msg]
    )
    if _contains_banned_phrases(joined):
        raise ValueError("Content contains banned phrases")

    latin_fraction = _latin_ratio(joined)
    if latin_fraction > 0.75:
        raise ValueError(
            f"Language skew detected (latin ratio: {latin_fraction:.2f} > 0.75)"
        )

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
    platform: str = "telegram",
) -> Optional[Dict[str, Any]]:
    """Generate per-platform content using intelligent AI routing.

    Args:
        title: Post title
        summary: Post summary
        link: Post link
        system_prompt: Custom system prompt (optional)
        platform: Target platform (blogger, devto, facebook, telegram, etc.)

    Returns:
        Dict with platform-specific content or None on failure
    """
    _set_last_error(None)

    # Get AI manager
    ai_manager = _get_ai_manager()

    # Use custom prompt if provided, otherwise use default
    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT

    user_content = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Link: {link}\n\n"
        "Return ONLY the JSON object with the required keys.\n\n"
        "⚠️ IMPORTANT: Create ORIGINAL, authentic content. Do NOT copy from the source. "
        "Write as if you're explaining this to a friend - use your own words, examples, and insights."
    )

    try:
        # Generate content using intelligent AI routing
        result = ai_manager.generate_content(
            platform=platform,
            system_prompt=effective_system_prompt,
            user_prompt=user_content,
            enable_reasoning=platform in ["blogger", "devto"],  # Enable reasoning for long-form
        )
        
        if not result:
            _set_last_error("Empty AI response")
            return None
        
        # Parse JSON response (result is the content string directly)
        parsed = _parse_json_response(result)
        if parsed is None:
            snippet = result.strip().replace("\n", " ")
        except ValueError as ve:
            _set_last_error(f"AI Validation Error: {ve}")
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
        _set_last_error(base[:300])
        return None
