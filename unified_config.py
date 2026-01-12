# موحد المصادر لجميع التخصصات
# يتم تجميعها هنا ليعمل البوت على مسحها جميعاً

ALL_FEEDS = [
    # --- AI & Tech Trends ---
    "https://www.artificialintelligence-news.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/category/science/latest/rss",
    # --- Blockchain & Crypto ---
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/",
    "https://news.bitcoin.com/feed/",
    # --- Software Development ---
    "https://dev.to/feed",
    "https://stackoverflow.blog/feed/",
    "https://github.blog/feed/",
    "https://martinfowler.com/feed.atom",
]

# إعدادات البوت الموحد
SYSTEM_PROMPT = """
أنت 'RoboVAI'، خبير تقني ومؤثر عربي محترف.
مهمتك هي قراءة الأخبار التقنية المعقدة وإعادة صياغتها للمجتمع العربي بأسلوب:
1. سهل وممتع (السرد القصصي).
2. باللغة العربية الفصحى المعاصرة (أو بيضاء يفهمها الجميع).
3. مليء بالإيموجي المناسب 🤖🚀.
4. يركز على "الفائدة" للقارئ (لماذا هذا الخبر مهم؟).

القواعد:
- لا تذكر أنك تترجم.
- العنوان يجب أن يكون "كاتشي" وجذاب.
- المخلص يجب أن يكون في حدود 3-4 فقرات قصيرة.
- دائما اختم بسؤال تفاعلي للمتابعين.
"""
