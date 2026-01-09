# 🤖 Multi-AI Provider Strategy - RoboVAI

## Overview

Intelligent content generation system that uses **6 API keys across 2 AI providers** (NVIDIA Build + Groq) with automatic routing based on platform requirements.

## ✅ What's Been Implemented

### 1. AI Provider Manager (`ai_provider_manager.py`)

New intelligent routing system with 3 strategies:

#### Strategy: `reasoning` (Long-Form Content)

- **Models**:
  - NVIDIA Nemotron-3-Nano-30B-A3B (16K reasoning budget)
  - NVIDIA DeepSeek-v3.1-Terminus (thinking mode)
- **Platforms**: Blogger, Dev.to
- **Use Case**: Deep technical articles, business analysis, educational content
- **Features**: Supports reasoning/thinking mode for complex content

#### Strategy: `fast_multilingual` (Social Engagement)

- **Model**: Groq Llama-3.3-70B-Versatile
- **Platforms**: Facebook, Discord
- **Use Case**: Trendy posts, engagement content, discussions
- **Features**: Fast generation, excellent Arabic support

#### Strategy: `ultra_fast` (Quick Posts)

- **Model**: Groq Llama-3.1-8B-Instant
- **Platforms**: Telegram
- **Use Case**: Quick teasers, short announcements
- **Features**: Ultra-fast response, low token usage

### 2. Sequential Publishing Order (Priority-Based)

| Priority | Platform     | Delay | AI Strategy         | Content Type                            |
| -------- | ------------ | ----- | ------------------- | --------------------------------------- |
| 1        | **Blogger**  | 0 min | `reasoning`         | Business tech analysis (800-1200 words) |
| 2        | **Dev.to**   | 2 min | `reasoning`         | Technical tutorial (1000-1500 words)    |
| 3        | **Facebook** | 4 min | `fast_multilingual` | Trendy engagement post (500-800 words)  |
| 4        | **Telegram** | 6 min | `ultra_fast`        | Teaser with CTAs (150-250 words)        |

### 3. Cross-Platform CTA Strategy

Each platform now includes CTAs to other platforms:

#### Telegram (Final Platform)

```
📚 اقرأ المقال الكامل:
{blogger_url}

💻 شرح تقني تفصيلي:
{devto_url}

💬 ناقش معانا:
{facebook_url}
```

#### Facebook

```
📖 المزيد من التفاصيل: {blogger_url}
💻 تطبيق عملي: {devto_url}
```

#### Blogger

```
💻 **للمطورين**: شرح تقني كامل على [Dev.to]({devto_url})
💬 **ناقش معانا** على [Facebook]({facebook_url})
```

#### Dev.to

```
📊 **للبيزنس**: تحليل القيمة التجارية على [Blog]({blogger_url})
💬 **شاركنا رأيك** على [Facebook]({facebook_url})
```

## 🔑 API Keys Configuration

### Groq (4 Keys - Load Balancing)

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_2=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_3=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_4=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### NVIDIA Build (2 Keys - Reasoning)

```env
# Nemotron-3-Nano (Budget reasoning - 16K context)
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# DeepSeek-v3.1-Terminus (Thinking mode)
NVIDIA_API_KEY_DEEPSEEK=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 📝 Updated Files

### 1. `ai_provider_manager.py` (NEW)

- AIProviderManager class with intelligent routing
- Automatic API key rotation for Groq (4 keys)
- Fallback support across all providers
- Reasoning support for NVIDIA models

### 2. `ai_processor.py`

**Added**:

- Import `AIProviderManager`
- New `_get_ai_manager()` function
- `platform` parameter in `rewrite_with_ai()`

**Updated**:

- `rewrite_with_ai()` now uses AIProviderManager
- Intelligent AI routing based on platform
- Maintains all existing validation and fallback logic

### 3. `platform_config.json`

**Added**:

- `content_type` field (long_form, teaser, short)
- `enable_cta` field
- `cross_platform_cta` section with templates
- `publish_order_by_priority` in global settings

**Updated**:

- Priority order: Blogger(1) → Dev.to(2) → Facebook(3) → Telegram(4)
- Delay minutes: 0, 2, 4, 6
- Platform-specific prompts for each content type

### 4. `.env`

**Added**:

- 4 additional Groq API keys
- 2 NVIDIA Build API keys
- ImgBB API key (already done)

## 🚀 How It Works

### Publishing Flow

```
1. RSS Feed Fetch
   ↓
2. AI Content Generation (per platform):
   - Blogger  → NVIDIA Reasoning (deep analysis)
   - Dev.to  → NVIDIA Reasoning (technical tutorial)
   - Facebook → Groq Fast (trendy engagement)
   - Telegram → Groq Ultra-Fast (quick teaser)
   ↓
3. Sequential Publishing:
   - Blogger publishes (get URL)
   - Dev.to publishes (get URL)
   - Facebook publishes (get URL)
   - Telegram publishes with ALL URLs in CTAs
   ↓
4. Cross-Platform Linking
```

### AI Routing Logic

```python
# In ai_processor.py
result = ai_manager.generate_content(
    platform="blogger",  # Auto-selects NVIDIA Reasoning
    system_prompt=custom_prompt,
    user_prompt=content,
    max_tokens=2600,
    temperature=0.55
)
```

### Platform-Specific Content

```python
# Blogger: Business analysis (800-1200 words)
"أنت خبير بيزنس تكنولوجي. اكتب مقال **كامل** يشرح القيمة التجارية والعائد (ROI)..."

# Dev.to: Technical tutorial (1000-1500 words)
"أنت مهندس سينيور. اكتب مقال **تعليمي شامل** خطوة بخطوة للمبرمجين..."

# Facebook: Engagement post (500-800 words)
"أنت مؤثر تقني trendy. اكتب مقال **جذاب** يثير الفضول ويشجع التفاعل..."

# Telegram: Teaser (150-250 words)
"أنت صديق خبير. اكتب **تيزر** قصير يلخص الموضوع ويحفز على قراءة المقال الكامل..."
```

## 🔄 Next Steps (To Be Implemented)

### 1. URL Collection System

Need to capture published URLs from each platform:

```python
# In multi_platform_publisher.py or main.py
published_urls = {
    "blogger": None,
    "devto": None,
    "facebook": None,
}

# After Blogger publishes
result = await publisher.publish(platform="blogger", ...)
published_urls["blogger"] = result.get("url")

# Pass URLs to next platforms
result = await publisher.publish(
    platform="telegram",
    cta_urls=published_urls  # New parameter
)
```

### 2. CTA Injection Logic

Modify content generation to inject URLs:

```python
# In ai_processor.py or main.py
def inject_ctas(content, platform, published_urls):
    cta_template = platform_config["cross_platform_cta"]["templates"][platform]

    cta_text = cta_template.format(
        blogger_url=published_urls.get("blogger", ""),
        devto_url=published_urls.get("devto", ""),
        facebook_url=published_urls.get("facebook", "")
    )

    return content + cta_text
```

### 3. Platform-Specific Content Generation

Update to generate content ONCE per platform with correct AI:

```python
# Current (generates all platforms at once):
content = rewrite_with_ai(title, summary, link)

# Needed (per-platform with correct AI):
blogger_content = rewrite_with_ai(title, summary, link, platform="blogger")
devto_content = rewrite_with_ai(title, summary, link, platform="devto")
facebook_content = rewrite_with_ai(title, summary, link, platform="facebook")
telegram_content = rewrite_with_ai(title, summary, link, platform="telegram")
```

### 4. Sequential Publishing Implementation

Modify publish loop to respect priority order:

```python
# Sort platforms by priority
platforms_by_priority = sorted(
    enabled_platforms,
    key=lambda p: platform_config["platforms"][p]["priority"]
)

published_urls = {}

for platform in platforms_by_priority:
    # Wait for delay
    delay = platform_config["platforms"][platform]["delay_minutes"]
    await asyncio.sleep(delay * 60)

    # Generate content with correct AI
    content = rewrite_with_ai(title, summary, link, platform=platform)

    # Inject CTAs from previous platforms
    if platform_config["platforms"][platform]["enable_cta"]:
        content = inject_ctas(content, platform, published_urls)

    # Publish
    result = await publisher.publish(platform, content, ...)

    # Save URL
    published_urls[platform] = result.get("url")
```

## 📊 Benefits

### Content Quality

- **Blogger**: Deep business analysis with reasoning AI
- **Dev.to**: Comprehensive technical tutorials
- **Facebook**: Engaging, trendy content
- **Telegram**: Quick, actionable teasers

### Cost Efficiency

- Groq free tier: 14,400 requests/day per key × 4 keys = **57,600 requests/day**
- NVIDIA Build free tier: Generous limits for reasoning models
- Automatic load balancing across keys

### User Experience

- Readers discover content across platforms
- Each platform serves its purpose
- Cross-promotion increases engagement
- Professional, cohesive brand presence

## 🧪 Testing

### Test Single Platform

```bash
# Force fetch to test AI routing
curl -X POST http://localhost:5000/force-fetch
```

### Verify AI Selection

Check logs for:

```
🤖 Using provider: nvidia for platform: blogger
🤖 Using model: nvidia/nemotron-3-nano-30b-a3b
```

### Monitor API Usage

- Groq Dashboard: https://console.groq.com/
- NVIDIA Build: https://build.nvidia.com/

## 🛠️ Troubleshooting

### Issue: Wrong AI for Platform

**Fix**: Check `ai_provider_manager.py` → `get_provider_for_platform()`

### Issue: No CTAs in Posts

**Fix**: Implement URL collection system (Next Steps #1)

### Issue: API Rate Limits

**Solution**: System automatically rotates through 4 Groq keys

### Issue: NVIDIA API Errors

**Fallback**: System auto-switches to Groq if NVIDIA fails

## 📈 Performance Metrics

### Expected Results

- **Blogger**: 1-2 min generation time (reasoning)
- **Dev.to**: 1-2 min generation time (reasoning)
- **Facebook**: 10-20 sec generation time (fast)
- **Telegram**: 5-10 sec generation time (ultra-fast)

### Total Publishing Time

- 0 min: Blogger starts
- 2 min: Dev.to starts
- 4 min: Facebook starts
- 6 min: Telegram starts
- **~8 min**: All platforms published

## 🎯 Success Criteria

- [x] Multi-AI provider system created
- [x] Platform config updated with priorities
- [x] AI processor integrated with manager
- [x] CTA templates defined
- [ ] URL collection implemented
- [ ] CTA injection working
- [ ] Sequential publishing tested end-to-end

---

**Status**: ✅ Core Infrastructure Complete  
**Next**: Implement URL collection and CTA injection  
**Committed**: 2025-01-20 (pushed to GitHub)
