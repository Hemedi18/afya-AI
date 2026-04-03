#!/usr/bin/env python
"""
One-shot script: fills in English and Arabic translations in the .po files.
Run from project root: python ztest/fill_translations.py
"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Translation table  {msgid_sw: (en_msgstr, ar_msgstr)}
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    # ── settings labels ────────────────────────────────────────────────────
    "Swahili": ("Swahili", "السواحيلية"),
    "English": ("English", "الإنجليزية"),
    "Arabic": ("Arabic", "العربية"),

    # ── hero ────────────────────────────────────────────────────────────────
    "Karibu": ("Welcome", "أهلاً وسهلاً"),

    (
        "AfyaSmart ni platform ya afya ya uzazi na ustawi wa kila siku. "
        "Hapa utapata mfumo wa ku-track mzunguko, AI chat kwa majibu ya "
        "haraka, support ya jamii, na mwongozo wa wataalamu. Mtumiaji mpya "
        "anayejisajili ataelekezwa hapa kwanza ili apate maelezo kamili ya "
        "huduma, documentation, na njia za mawasiliano."
    ): (
        "AfyaSmart is a reproductive health and daily wellness platform. "
        "Here you will find a cycle-tracking system, AI chat for quick "
        "answers, community support, and expert guidance. New users who "
        "register are directed here first to get full information about "
        "services, documentation, and ways to get in touch.",
        "AfyaSmart منصة للصحة الإنجابية والرفاهية اليومية. ستجد هنا نظاماً "
        "لتتبع الدورة، ومحادثات الذكاء الاصطناعي للإجابات السريعة، ودعم "
        "المجتمع، وإرشادات الخبراء. يُوجَّه المستخدمون الجدد إلى هنا أولاً "
        "للحصول على معلومات شاملة عن الخدمات والتوثيق وطرق التواصل."
    ),

    "Jaribu AI Chat": ("Try AI Chat", "جرّب المساعد الذكي"),
    "Soma Guide": ("Read Guide", "اقرأ الدليل"),
    "Weka rekodi kwa urahisi kila siku": (
        "Record daily with ease", "سجّل يومياً بسهولة"),
    "Mapendekezo yanayobinafsishwa": (
        "Personalized recommendations", "توصيات مخصصة"),
    "Data inalindwa kwa mipangilio ya privacy": (
        "Data protected with privacy settings", "بياناتك محمية بالخصوصية"),
    "AI inaendelea kujifunza": ("AI keeps learning", "الذكاء الاصطناعي يتعلم"),
    "Community support 24/7": ("Community support 24/7", "دعم المجتمع 24/7"),
    "Track • Predict • Improve": (
        "Track • Predict • Improve", "تتبع • تنبأ • تحسّن"),

    # ── services ────────────────────────────────────────────────────────────
    "Services": ("Services", "الخدمات"),
    "Cycle Tracking": ("Cycle Tracking", "تتبع الدورة الشهرية"),
    (
        "Log za kila siku, flow intensity, dalili, na trend analysis. "
        "Mfumo unakusaidia kuona pattern ya mzunguko mapema."
    ): (
        "Daily logs, flow intensity, symptoms, and trend analysis. "
        "The system helps you spot cycle patterns early.",
        "السجلات اليومية وشدة التدفق والأعراض وتحليل الأنماط. "
        "يساعدك النظام على رصد أنماط الدورة مبكراً."
    ),
    "AI Assistant": ("AI Assistant", "المساعد الذكي"),
    (
        "Majibu ya haraka kwa maswali ya afya, ushauri wa lifestyle, na "
        "mapendekezo personalized kulingana na data yako."
    ): (
        "Quick answers to health questions, lifestyle advice, and "
        "personalized recommendations based on your data.",
        "إجابات سريعة على أسئلة الصحة ونصائح نمط الحياة "
        "وتوصيات مخصصة بناءً على بياناتك."
    ),
    "Community": ("Community", "المجتمع"),
    (
        "Jamii salama ya kuuliza, kujifunza, na kupata support. "
        "Unaweza kushiriki updates na kujifunza kutoka uzoefu wa wengine."
    ): (
        "A safe community to ask questions, learn, and get support. "
        "You can share updates and learn from others' experiences.",
        "مجتمع آمن للسؤال والتعلم والحصول على الدعم. "
        "يمكنك مشاركة التحديثات والتعلم من تجارب الآخرين."
    ),
    "Doctor Access": ("Doctor Access", "الوصول إلى الطبيب"),
    (
        "Unganishwa na madaktari wa mfumo kwa mwongozo wa ziada, hasa "
        "unapohitaji ufafanuzi wa kitaalamu kwa haraka."
    ): (
        "Connect with doctors in the system for extra guidance, especially "
        "when you need expert clarification quickly.",
        "تواصل مع أطباء النظام للحصول على إرشادات إضافية، "
        "خاصةً حين تحتاج توضيحاً متخصصاً بسرعة."
    ),

    # ── how it works ────────────────────────────────────────────────────────
    "How It Works": ("How It Works", "كيف يعمل"),
    "Jisajili": ("Register", "سجّل"),
    "Unda account na ukamilishe AI persona ili mfumo uanze kukuelewa.": (
        "Create an account and complete your AI persona so the system "
        "starts understanding you.",
        "أنشئ حساباً وأكمل ملفك الشخصي الذكي حتى يبدأ النظام في فهمك."
    ),
    "Weka Daily Log": ("Add Daily Log", "أضف سجلاً يومياً"),
    "Andika flow, dalili, hisia, na notes kila siku kwa matokeo bora.": (
        "Write flow, symptoms, mood, and notes every day for better results.",
        "اكتب التدفق والأعراض والمزاج والملاحظات يومياً للحصول على نتائج أفضل."
    ),
    "Pata Insights": ("Get Insights", "احصل على رؤى"),
    "Tazama trends, reminders, na mapendekezo ya AI kwenye dashboard.": (
        "View trends, reminders, and AI recommendations on your dashboard.",
        "اعرض الأنماط والتذكيرات وتوصيات الذكاء الاصطناعي على لوحة التحكم."
    ),
    "Shirikiana": ("Collaborate", "تعاون"),
    "Uliza jamii au doctor pale unapotaka ushauri wa ziada.": (
        "Ask the community or a doctor whenever you want extra advice.",
        "اسأل المجتمع أو الطبيب متى أردت مزيداً من المشورة."
    ),

    # ── documentation ───────────────────────────────────────────────────────
    "Documentation": ("Documentation", "التوثيق"),
    (
        "Documentation yetu inaelezea kila kitu: kuanza kutumia mfumo, "
        "jinsi ya kuweka data sahihi, namna ya kutumia AI Chat, moderation "
        "ya jamii, na usalama wa taarifa zako."
    ): (
        "Our documentation explains everything: getting started, how to "
        "enter data correctly, how to use AI Chat, community moderation, "
        "and the security of your information.",
        "يشرح توثيقنا كل شيء: البدء باستخدام النظام، وكيفية إدخال البيانات "
        "بشكل صحيح، واستخدام المحادثة الذكية، وإدارة المجتمع، وأمان معلوماتك."
    ),
    (
        "Ukifuata guide hii, experience yako itakuwa laini na taarifa "
        "zitakuwa na ubora wa juu kwa personalized insights."
    ): (
        "By following this guide, your experience will be smooth and your "
        "data will be high-quality for personalized insights.",
        "باتباع هذا الدليل، ستكون تجربتك سلسة وستكون بياناتك عالية الجودة "
        "للحصول على رؤى مخصصة."
    ),
    "Fungua Documentation": ("Open Documentation", "افتح التوثيق"),

    # ── contact & support ───────────────────────────────────────────────────
    "Contact & Support": ("Contact & Support", "التواصل والدعم"),
    "Unahitaji msaada?": ("Need help?", "تحتاج مساعدة؟"),
    (
        "Kwa changamoto za account, technical issue, au ushauri wa matumizi, "
        "tumia ukurasa wa mawasiliano. Timu yetu itakusaidia haraka kulingana "
        "na aina ya tatizo."
    ): (
        "For account challenges, technical issues, or usage advice, use the "
        "contact page. Our team will help you quickly based on the type of "
        "problem.",
        "لتحديات الحساب أو المشكلات التقنية أو الاستفسارات، استخدم صفحة "
        "التواصل. سيساعدك فريقنا سريعاً بحسب نوع المشكلة."
    ),
    "Support ya login, profile, na usalama wa account": (
        "Support for login, profile, and account security",
        "دعم تسجيل الدخول والملف الشخصي وأمان الحساب"
    ),
    "Msaada wa AI chat, notifications, na doctor channel": (
        "Help with AI chat, notifications, and doctor channel",
        "مساعدة في المحادثة الذكية والإشعارات وقناة الطبيب"
    ),
    "Mwongozo wa jinsi ya kutumia features kwa ufanisi": (
        "Guidance on how to use features effectively",
        "إرشادات حول كيفية استخدام الميزات بفاعلية"
    ),
    "Nenda Contact": ("Go to Contact", "انتقل للتواصل"),
    "Kuhusu AfyaSmart": ("About AfyaSmart", "عن AfyaSmart"),
    (
        "Fahamu dhamira, usalama wa data, na mwelekeo wa huduma zetu za afya "
        "kidigitali kwa muda mrefu."
    ): (
        "Learn about our mission, data security, and the long-term direction "
        "of our digital health services.",
        "تعرّف على مهمتنا وأمان البيانات والمسار المستقبلي لخدماتنا الصحية الرقمية."
    ),
    "Soma About": ("Read About", "اقرأ عنّا"),

    # ── faq ─────────────────────────────────────────────────────────────────
    "FAQ": ("FAQ", "الأسئلة الشائعة"),
    "Kwa nini niweke log kila siku?": (
        "Why should I log daily?", "لماذا يجب أن أسجّل يومياً؟"),
    (
        "Daily logs husaidia mfumo kugundua patterns zako mapema na kutoa "
        "mapendekezo sahihi zaidi."
    ): (
        "Daily logs help the system discover your patterns early and provide "
        "more accurate recommendations.",
        "تساعد السجلات اليومية النظام على اكتشاف أنماطك مبكراً وتقديم "
        "توصيات أكثر دقة."
    ),
    "Data yangu iko salama?": ("Is my data safe?", "هل بياناتي آمنة؟"),
    (
        "Ndiyo. Mfumo una mipangilio ya privacy na controls za account ili "
        "taarifa zako zibaki salama."
    ): (
        "Yes. The system has privacy settings and account controls to keep "
        "your information safe.",
        "نعم. يحتوي النظام على إعدادات الخصوصية وضوابط الحساب "
        "للحفاظ على أمان معلوماتك."
    ),
    "Gender selective inafanyaje kazi?": (
        "How does gender selection work?", "كيف يعمل اختيار الجنس؟"),
    (
        "Baada ya onboarding, mfumo unaonyesha njia/stori zinazolingana na "
        "gender uliyochagua kwenye AI persona."
    ): (
        "After onboarding, the system shows paths/stories that match the "
        "gender you chose in your AI persona.",
        "بعد الإعداد الأولي، يعرض النظام مسارات وقصصاً تتوافق مع الجنس "
        "الذي اخترته في ملفك الشخصي الذكي."
    ),

    # ── view-level welcome strings ───────────────────────────────────────────
    "Karibu dada! Safari yako ya afya ya mzunguko inaanza hapa.": (
        "Welcome sis! Your cycle health journey starts here.",
        "مرحباً أختي! رحلتك الصحية تبدأ هنا."
    ),
    "Fungua Dashboard ya Mzunguko": (
        "Open Cycle Dashboard", "افتح لوحة الدورة"),
    "Karibu kaka! Pata mwongozo wa afya na ustawi wako hapa.": (
        "Welcome bro! Find your health and wellness guide here.",
        "مرحباً أخي! احصل على دليل صحتك ورفاهيتك هنا."
    ),
    "Fungua Male Dashboard": (
        "Open Male Dashboard", "افتح لوحة تحكم الرجال"),
    "Karibu AfyaSmart — Jisajili ili upate huduma zilizobinafsishwa.": (
        "Welcome to AfyaSmart — Register for personalized services.",
        "مرحباً في AfyaSmart — سجّل للحصول على خدمات مخصصة."
    ),
    "Anza Kujisajili": ("Start Registering", "ابدأ التسجيل"),

    # ── settings section labels ──────────────────────────────────────────────
    "General Settings": ("General Settings", "الإعدادات العامة"),
    "Display & Profile": ("Display & Profile", "العرض والملف الشخصي"),
    "Security & Privacy": ("Security & Privacy", "الأمان والخصوصية"),
    "Language": ("Language", "اللغة"),
    "General settings updated successfully!": (
        "General settings updated successfully!",
        "تم تحديث الإعدادات العامة بنجاح!"
    ),
    "Display settings updated!": (
        "Display settings updated!", "تم تحديث إعدادات العرض!"),
    "Password changed successfully!": (
        "Password changed successfully!", "تم تغيير كلمة المرور بنجاح!"),
    "Language updated successfully!": (
        "Language updated successfully!", "تم تحديث اللغة بنجاح!"),
}


def normalize(s):
    """Collapse all internal whitespace/newlines to a single space."""
    return re.sub(r'\s+', ' ', s).strip()


def parse_po(filepath):
    """Parse a .po file and return its raw text."""
    with open(filepath, encoding='utf-8') as f:
        return f.read()


def build_lookup(po_text):
    """
    Return dict  { normalized_msgid: (start_of_msgstr_line, end) }
    where start/end are character offsets into po_text so we can replace.
    """
    # We'll work entry by entry using regex.
    entries = {}
    # Pattern: msgid "..." (possibly multi-line) followed by msgstr "..."
    pattern = re.compile(
        r'(msgid\s+"((?:[^"\\]|\\.)*)"\s*(?:\n"(?:[^"\\]|\\.)*"\s*)*)'
        r'(msgstr\s+"((?:[^"\\]|\\.)*)")',
        re.MULTILINE
    )
    for m in pattern.finditer(po_text):
        raw_id = m.group(2)
        # collect continuation lines from the msgid block
        full_id_block = m.group(1)
        continuations = re.findall(r'\n"((?:[^"\\]|\\.)*)"', full_id_block)
        full_id = raw_id + ''.join(continuations)
        # Unescape
        full_id = full_id.replace('\\n', '\n').replace('\\"', '"')
        norm = normalize(full_id)
        if norm:
            entries[norm] = m
    return entries


def fill_po(filepath, lang_index):
    """Fill msgstr entries in a .po file.
    lang_index: 0 = English, 1 = Arabic
    """
    text = parse_po(filepath)

    # Build a normalised-id → translation lookup
    xlat = {}
    for key, val in TRANSLATIONS.items():
        if isinstance(key, tuple):
            # shouldn't happen but guard
            k = normalize(' '.join(key))
        else:
            k = normalize(key)
        xlat[k] = val[lang_index]

    # We process the file sequentially, replacing empty msgstr "" entries.
    # Strategy: find each  msgid block + its msgstr, normalise msgid, look up.
    def replacer(m):
        raw_id = m.group(2)
        full_id_block = m.group(1)
        continuations = re.findall(r'\n"((?:[^"\\]|\\.)*)"', full_id_block)
        full_id = raw_id + ''.join(continuations)
        full_id = full_id.replace('\\n', '\n').replace('\\"', '"')
        norm = normalize(full_id)
        translation = xlat.get(norm, '')
        if translation:
            # Escape for PO format
            escaped = translation.replace('\\', '\\\\').replace('"', '\\"')
            return m.group(1) + f'msgstr "{escaped}"'
        return m.group(0)  # leave as-is

    pattern = re.compile(
        r'(msgid\s+"((?:[^"\\]|\\.)*)"\s*(?:\n"(?:[^"\\]|\\.)*"\s*)*)'
        r'(msgstr\s+"(?:[^"\\]|\\.)*")',
        re.MULTILINE
    )

    new_text = pattern.sub(replacer, text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print(f"  ✓ Written: {filepath}")


if __name__ == '__main__':
    en_po = os.path.join(BASE, 'locale', 'en', 'LC_MESSAGES', 'django.po')
    ar_po = os.path.join(BASE, 'locale', 'ar', 'LC_MESSAGES', 'django.po')

    print("Filling English translations …")
    fill_po(en_po, 0)
    print("Filling Arabic translations …")
    fill_po(ar_po, 1)
    print("Done. Now run: python manage.py compilemessages")
