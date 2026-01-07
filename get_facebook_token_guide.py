"""
Get Facebook Page Access Token
Guide to obtaining Page Access Token for Facebook Graph API
"""

print("=" * 70)
print("📘 How to Get Facebook Page Access Token")
print("كيفية الحصول على Facebook Page Access Token")
print("=" * 70)

print("""
STEP 1: Create a Facebook App
الخطوة 1: إنشاء تطبيق فيسبوك
----------------------------------------------------------------------
1. Go to: https://developers.facebook.com/apps
   اذهب إلى: https://developers.facebook.com/apps

2. Click "Create App" → Choose "Business" type
   اضغط "Create App" → اختر نوع "Business"

3. Enter app name (e.g., "Tech News Bot")
   أدخل اسم التطبيق (مثل: "Tech News Bot")

4. Fill in contact email and click "Create App"
   املأ البريد الإلكتروني واضغط "Create App"


STEP 2: Add Permissions
الخطوة 2: إضافة الصلاحيات
----------------------------------------------------------------------
1. In your app dashboard, go to "App Settings" → "Basic"
   في لوحة التطبيق، اذهب إلى "App Settings" → "Basic"

2. Copy your "App ID" and "App Secret" (you'll need these)
   انسخ "App ID" و "App Secret" (ستحتاجهما)


STEP 3: Get User Access Token
الخطوة 3: الحصول على User Access Token
----------------------------------------------------------------------
1. Go to: https://developers.facebook.com/tools/explorer
   اذهب إلى: https://developers.facebook.com/tools/explorer

2. Select your app from the dropdown
   اختر تطبيقك من القائمة المنسدلة

3. Click "Generate Access Token"
   اضغط "Generate Access Token"

4. Grant permissions:
   امنح الصلاحيات:
   - pages_show_list (View pages you manage)
   - pages_read_engagement
   - pages_manage_posts (Create posts on your pages)
   - pages_read_user_content

5. Click "Generate Access Token" and login with Facebook
   اضغط "Generate Access Token" وسجل دخول بحساب فيسبوك

6. Copy the generated token (this is a SHORT-LIVED token, ~1 hour)
   انسخ التوكن المنشأ (هذا توكن قصير المدى، ~ساعة)


STEP 4: Get Long-Lived User Token (60 days)
الخطوة 4: الحصول على User Token طويل المدى (60 يوم)
----------------------------------------------------------------------
Open this URL in your browser (replace YOUR_APP_ID, YOUR_APP_SECRET, and SHORT_LIVED_TOKEN):
افتح هذا الرابط في المتصفح (استبدل YOUR_APP_ID و YOUR_APP_SECRET و SHORT_LIVED_TOKEN):

https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN

This will return JSON with "access_token" - this is your LONG-LIVED USER TOKEN
سيعود بـ JSON يحتوي على "access_token" - هذا هو USER TOKEN طويل المدى


STEP 5: Get Page Access Token (NEVER EXPIRES!)
الخطوة 5: الحصول على Page Access Token (لا ينتهي أبداً!)
----------------------------------------------------------------------
1. Go back to Graph API Explorer: https://developers.facebook.com/tools/explorer
   ارجع لـ Graph API Explorer: https://developers.facebook.com/tools/explorer

2. Paste your LONG-LIVED USER TOKEN from Step 4
   الصق USER TOKEN طويل المدى من الخطوة 4

3. Change the request to: /me/accounts
   غير الطلب إلى: /me/accounts

4. Click "Submit"
   اضغط "Submit"

5. You'll see a list of pages you manage. Find your page and copy:
   سترى قائمة بالصفحات التي تديرها. ابحث عن صفحتك وانسخ:
   - "access_token" → This is your PAGE ACCESS TOKEN (永久 PERMANENT!)
   - "id" → This is your PAGE ID

6. Add to .env file:
   أضف لملف .env:

   FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   FACEBOOK_PAGE_ID=123456789012345


STEP 6 (IMPORTANT): Verify Token Never Expires
الخطوة 6 (مهم): تأكد أن التوكن لا ينتهي
----------------------------------------------------------------------
1. Go to: https://developers.facebook.com/tools/debug/accesstoken
   اذهب إلى: https://developers.facebook.com/tools/debug/accesstoken

2. Paste your PAGE ACCESS TOKEN
   الصق PAGE ACCESS TOKEN

3. Check that:
   تأكد من:
   - Type: Page
   - Expires: Never
   - Permissions include: pages_manage_posts, pages_read_engagement


QUICK METHOD (Using Graph API Explorer directly):
الطريقة السريعة (استخدام Graph API Explorer مباشرة):
----------------------------------------------------------------------
1. Go to: https://developers.facebook.com/tools/explorer
2. Select your app
3. Click "Generate Access Token" with page permissions
4. Request: /me/accounts
5. Copy page "access_token" and "id" from the response

That's it! You're ready to post to your Facebook page!
هذا كل شيء! أنت جاهز للنشر على صفحتك!

""")

print("=" * 70)
print("📝 Test Your Setup:")
print("   python facebook_publisher.py")
print("=" * 70)
