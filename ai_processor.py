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
    "linkedin_post": "منشور لينكدإن احترافي (بدون مصادر/روابط)",
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
    "llama3-70b-8192",
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

    # Some models wrap JSON in markdown fences.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\s*\n?", "", cleaned)
    if cleaned.endswith("```"):
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    def _escape_controls_inside_strings(text: str) -> str:
        """Escape raw newlines/tabs inside JSON strings so json.loads can parse."""
        out: list[str] = []
        in_string = False
        escaping = False
        for ch in text:
            if in_string:
                if escaping:
                    out.append(ch)
                    escaping = False
                    continue
                if ch == "\\":
                    out.append(ch)
                    escaping = True
                    continue
                if ch == '"':
                    out.append(ch)
                    in_string = False
                    continue
                if ch == "\n":
                    out.append("\\n")
                    continue
                if ch == "\r":
                    out.append("\\r")
                    continue
                if ch == "\t":
                    out.append("\\t")
                    continue
                out.append(ch)
            else:
                if ch == '"':
                    out.append(ch)
                    in_string = True
                    continue
                out.append(ch)
        return "".join(out)

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

    extracted = cleaned[start : end + 1]
    parsed = _try_parse(extracted)
    if parsed is not None:
        return parsed
    return _try_parse(_escape_controls_inside_strings(extracted))


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


def _strip_urls(text: str) -> str:
    # Remove any URLs; CTAs and links are handled outside the body.
    cleaned = re.sub(r"https?://\S+", "", text or "")

    lines: list[str] = []
    for line in cleaned.splitlines():
        if re.search(
            r"\b(source|original\s+article|المصدر|مصدر|المقال\s+الأصلي)\b",
            line,
            flags=re.IGNORECASE,
        ):
            continue
        lines.append(line.rstrip())

    out = "\n".join(lines).strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


def _normalize_ai_result(parsed: Dict[str, Any], *, link: str) -> Dict[str, Any]:
    telegram_post = _strip_urls(
        _strip_code_fences(_ensure_string(parsed.get("telegram_post")))
    )
    facebook_post = _strip_urls(
        _strip_code_fences(_ensure_string(parsed.get("facebook_post")))
    )
    linkedin_post = _strip_urls(
        _strip_code_fences(_ensure_string(parsed.get("linkedin_post")))
    )
    blog_title = _ensure_string(parsed.get("blog_title"))
    blog_content_md = _strip_code_fences(_ensure_string(parsed.get("blog_content_md")))
    discord_msg = _strip_urls(
        _strip_code_fences(_ensure_string(parsed.get("discord_msg")))
    )

    # --- FLUID FALLBACKS (Robust Recovery) ---
    # 1. Gather any valid text content found
    sources = [
        t
        for t in [
            telegram_post,
            facebook_post,
            blog_content_md,
            discord_msg,
            linkedin_post,
        ]
        if t
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
    if not linkedin_post:
        linkedin_post = facebook_post or telegram_post
    if not blog_title:
        # Extract potential title from first line of content
        first_line = fallback_text.split("\n")[0].strip()
        # Remove markdown headers if present
        blog_title = re.sub(r"^[\#\*]+", "", first_line).strip() or "Tech Update"

    joined = "\n".join(
        [
            telegram_post,
            facebook_post,
            linkedin_post,
            blog_title,
            blog_content_md,
            discord_msg,
        ]
    )
    if _contains_banned_phrases(joined):
        raise ValueError("Content contains banned phrases")

    latin_fraction = _latin_ratio(joined)
    if latin_fraction > 0.75:
        raise ValueError(
            f"Language skew detected (latin ratio: {latin_fraction:.2f} > 0.75)"
        )

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
        "linkedin_post": linkedin_post,
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
    brand_name: str = "robovai_ar",  # NEW: Brand awareness
    brand_language: str = "en",  # NEW: Language awareness
) -> Optional[Dict[str, Any]]:
    """Generate per-platform content using intelligent AI routing.

    Args:
        title: Post title
        summary: Post summary
        link: Post link
        system_prompt: Custom system prompt (optional)
        platform: Target platform (blogger, devto, facebook, telegram, etc.)
        brand_name: Brand identifier (blocksignals, zerodev, flowpilot, robovai_ar)
        brand_language: Content language (en, ar)

    Returns:
        Dict with platform-specific content or None on failure
    """
    _set_last_error(None)

    # Get AI manager
    ai_manager = _get_ai_manager()

    # Use custom prompt if provided, otherwise use default
    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    
    # Add platform-specific instructions
    platform_instructions = _get_platform_instructions(platform, brand_name, brand_language)
    effective_system_prompt += f"\n\n{platform_instructions}"

    user_content = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Link: {link}\n\n"
        f"Target Platform: {platform}\n"
        f"Brand: {brand_name}\n"
        f"Language: {brand_language}\n\n"
        "Return ONLY the JSON object with the required keys.\n\n"
        "CRITICAL JSON RULES: Output must be strict valid JSON. Do NOT wrap in ``` fences. "
        "Do NOT include raw line breaks inside string values; use \\n for new lines.\n\n"
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
            brand_language=brand_language,  # NEW: Pass language for routing
        )

        if not result:
            _set_last_error("Empty AI response")
            return None

        # Parse JSON response (result is the content string directly)
        parsed = _parse_json_response(result)
        if parsed is None:
            snippet = result.strip().replace("\n", " ")[:200]
            _set_last_error(f"Failed to parse JSON response: {snippet}...")
            return None

        return _normalize_ai_result(parsed, link=link)

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


def _get_platform_instructions(platform: str, brand_name: str, brand_language: str) -> str:
    """
    Get platform-specific formatting and content instructions
    
    Args:
        platform: Target platform
        brand_name: Brand identifier
        brand_language: Content language
    
    Returns:
        Additional instructions for system prompt
    """
    instructions = {
        "blogger": {
            "en": "Write a comprehensive article (1200-1500 words) with SEO optimization, clear headers (## ##), internal links placeholders, and markdown formatting.",
            "ar": "اكتب مقالة شاملة (1200-1500 كلمة) مع تحسين SEO، عناوين واضحة، روابط داخلية، وتنسيق Markdown. استخدم اللهجة المصرية المهنية.",
        },
        "devto": {
            "en": "Write a technical tutorial (1500-2000 words) with code blocks, step-by-step instructions, markdown formatting, and clear learning outcomes.",
            "ar": "غير مدعوم - Dev.to للإنجليزي فقط",
        },
        "facebook": {
            "en": "Write an engaging story (600-800 words) with a strong hook, short paragraphs (2-3 lines), and a question at the end to encourage comments.",
            "ar": "اكتب قصة جذابة (600-800 كلمة) تبدأ بموقف relatable، فقرات قصيرة، وسؤال في النهاية للتفاعل. استخدم اللهجة المصرية الطبيعية.",
        },
        "telegram": {
            "en": "Write a concise update (150-250 words) with key takeaways in bullets, emojis, and a clear call to action.",
            "ar": "اكتب تنبيه قصير (150-200 كلمة) مع bullets واضحة وemojis. استخدم اللهجة المصرية البسيطة.",
        },
        "discord": {
            "en": "Write a discussion-starter (400-500 words) with context and open-ended questions to engage the community.",
            "ar": "غير مدعوم - Discord للإنجليزي فقط",
        },
    }
    
    lang = brand_language if brand_language in ["en", "ar"] else "en"
    instruction = instructions.get(platform, {}).get(lang, instructions["telegram"]["en"])
    
    # Add brand-specific modifications
    if brand_name == "robovai_ar" and brand_language == "ar":
        if platform == "blogger":
            instruction += "\n\nمهم: اشرح ليه الموضوع ده مهم للسوق المصري والعربي. أضف أمثلة محلية."
        elif platform == "facebook":
            instruction += "\n\nابدأ بسيناريو أو موقف يحصل في مصر. خلي الناس تحس إنك بتتكلم عنهم."
        elif platform == "telegram":
            instruction += "\n\nتنبيه سريع بأسلوب صديق بيبعت رسالة. استخدم emojis بكثرة."
    
    return f"**Platform Instructions for {platform}**:\n{instruction}"
