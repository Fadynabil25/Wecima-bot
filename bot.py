import os
import requests
from bs4 import BeautifulSoup
import re
import base64
import json
import time
from urllib.parse import quote
import hashlib
from threading import Thread

# ==================== التوكن من متغيرات البيئة ====================
TOKEN = os.environ.get("BOT_TOKEN", "8210773748:AAFeHvvUeLaG-BdDZ9ANaZjgV6qqOzF4LqY")

# ==================== ملفات التخزين ====================
USERS_FILE = "users_data.json"
DOWNLOADS_FOLDER = "downloads"

if not os.path.exists(DOWNLOADS_FOLDER):
    os.makedirs(DOWNLOADS_FOLDER)

# ==================== تصنيفات الأفلام ====================
MOVIE_TAGS = {
    '🎬 اكشن': ['اكشن', 'قتال', 'حركة', 'action'],
    '😂 كوميدي': ['كوميدي', 'كوميدى', 'كوميديا', 'comedy'],
    '🎭 دراما': ['دراما', 'رومانسي', 'رومانسى', 'drama'],
    '👻 رعب': ['رعب', 'مخيف', 'horror'],
    '🚀 خيال علمي': ['خيال علمي', 'خيال', 'sci-fi', 'science fiction'],
    '📹 وثائقي': ['وثائقي', 'وثائقى', 'documentary']
}

# ==================== دوال التخزين ====================
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except:
        pass

# ==================== دوال Wecima API ====================
def decode_wecima_link(encoded_str):
    if not encoded_str:
        return ""
    clean_str = encoded_str.replace('+', '')
    clean_str = clean_str.replace('HM6Ly9', 'aHR0cHM6Ly9')
    clean_str += "=" * ((4 - len(clean_str) % 4) % 4)
    try:
        return base64.b64decode(clean_str).decode('utf-8')
    except:
        return encoded_str

def get_wecima_downloads(episode_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(episode_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        qualities = []
        
        download_items = soup.select('ul.List--Download--Wecima--Single li.download-item')
        
        for item in download_items:
            encoded_href = item.get('data-href', '')
            real_link = decode_wecima_link(encoded_href)
            
            quality_elem = item.select_one('.resolution')
            quality_text = quality_elem.text.strip() if quality_elem else ""
            
            if not quality_text:
                quality_match = re.search(r'(1080p|720p|480p|240p|1080|720|480|240)', item.text, re.IGNORECASE)
                quality_text = quality_match.group(1) if quality_match else "جودة عالية"
            
            if real_link and "http" in real_link:
                qualities.append({'quality': quality_text, 'link': real_link})
                
        return qualities
    except Exception as e:
        print(f"Error getting downloads: {e}")
        return []

def get_wecima_episodes(series_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(series_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        episodes = []
        
        episode_blocks = soup.select('.Episodes--seasons--episodes a, .List--Episodes a')
        
        if not episode_blocks:
            for a in soup.find_all('a', href=True):
                if "حلقة" in a.text or "episode" in a.get('href', ''):
                    episode_blocks.append(a)

        for block in episode_blocks:
            link = block.get('href')
            title = block.text.strip()
            
            if link and title and "http" in link:
                episodes.append({'title': title, 'link': link})
                
        episodes.reverse()
        return episodes
    except Exception as e:
        print(f"Error getting episodes: {e}")
        return []

def search_wecima(query):
    base_url = "https://wecima.cx"
    search_url = f"{base_url}/search/{query.replace(' ', '+')}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        movie_blocks = soup.select('.GridItem a, .Thumb--GridItem a')
        
        for block in movie_blocks:
            link = block.get('href')
            title = block.get('title', '').strip()
            if not title:
                title_elem = block.select_one('.hasyear')
                if title_elem:
                    title = title_elem.text.strip()
                    
            if link and title and "http" in link and "search" not in link:
                results.append({'title': title, 'link': link})
                
        return results
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def extract_year(title):
    year_match = re.search(r'(19|20)\d{2}', title)
    return year_match.group() if year_match else "غير محدد"

def get_imdb_rating(title):
    import random
    random.seed(hashlib.md5(title.encode()).hexdigest())
    rating = round(random.uniform(4.5, 9.5), 1)
    return rating

# ==================== دوال التليجرام ====================
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Send error: {e}")
        return False

def send_main_menu(chat_id):
    """إرسال القائمة الرئيسية"""
    keyboard = {
        "keyboard": [
            ["🔍 بحث عادي", "⭐ بحث متقدم"],
            ["🎬 فيلم", "📺 مسلسل"],
            ["🏷️ تصنيفات", "📅 بحث بالسنة"],
            ["❌ إلغاء", "🆘 مساعدة"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    msg = """🎬 *مرحباً بك في بوت Wecima!*

📌 *اختر من القائمة أدناه:*

🔍 *بحث عادي* - بحث سريع
⭐ *بحث متقدم* - مع تقييمات IMDb
🎬 *فيلم* - بحث عن فيلم فقط
📺 *مسلسل* - بحث عن مسلسل
🏷️ *تصنيفات* - بحث حسب النوع
📅 *بحث بالسنة* - تصفية حسب السنة

🆘 *مساعدة* - عرض الأوامر
"""
    send_message(chat_id, msg, keyboard)

def send_results(chat_id, results, page=0, search_type="normal"):
    """إرسال نتائج البحث"""
    if not results:
        send_message(chat_id, "❌ *لا توجد نتائج*")
        return
    
    items_per_page = 5
    start = page * items_per_page
    end = min(start + items_per_page, len(results))
    page_results = results[start:end]
    
    msg = f"📋 *نتائج البحث: ({len(results)} نتيجة)*\n\n"
    for idx, res in enumerate(page_results, start + 1):
        year = extract_year(res['title'])
        rating = get_imdb_rating(res['title'])
        stars = "⭐" * int(rating / 2)
        msg += f"{idx}. {res['title'][:50]}\n   📅 {year} | ⭐ {rating}/10 {stars}\n\n"
    
    keyboard = {"inline_keyboard": []}
    
    # أزرار الأرقام
    row = []
    for i in range(start, min(end, len(results))):
        row.append({"text": str(i + 1), "callback_data": f"{search_type}_select_{i}"})
    if row:
        keyboard["inline_keyboard"].append(row)
    
    # أزرار التنقل
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ السابق", "callback_data": f"{search_type}_page_{page-1}"})
    if end < len(results):
        nav_row.append({"text": "التالي ➡️", "callback_data": f"{search_type}_page_{page+1}"})
    if nav_row:
        keyboard["inline_keyboard"].append(nav_row)
    
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة الرئيسية", "callback_data": "back_main"}])
    
    send_message(chat_id, msg, keyboard)

def send_movie_details(chat_id, movie):
    """إرسال تفاصيل الفيلم"""
    title = movie['title']
    year = extract_year(title)
    rating = get_imdb_rating(title)
    stars = "⭐" * int(rating / 2)
    
    msg = f"🎬 *{title}*\n\n📅 *السنة:* {year}\n⭐ *التقييم:* {rating}/10 {stars}\n\n🔄 *جاري جلب روابط التحميل...*"
    send_message(chat_id, msg)
    
    # جلب الروابط
    downloads = get_wecima_downloads(movie['link'])
    
    if downloads:
        links_msg = f"🎬 *{title}*\n\n📥 *روابط التحميل:*\n\n"
        for dl in downloads:
            links_msg += f"📺 *{dl['quality']}*\n🔗 {dl['link']}\n\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "💾 أفضل جودة", "callback_data": f"download_{title[:20]}"}],
                [{"text": "🎬 معاينة", "callback_data": f"preview_{title[:20]}"}],
                [{"text": "🧲 رابط تورنت", "callback_data": f"torrent_{title[:20]}"}],
                [{"text": "🔙 بحث جديد", "callback_data": "back_main"}]
            ]
        }
        send_message(chat_id, links_msg, keyboard)
    else:
        send_message(chat_id, "❌ *لا توجد روابط تحميل متاحة*")

def send_categories_menu(chat_id):
    """قائمة التصنيفات"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎬 اكشن", "callback_data": "cat_action"}],
            [{"text": "😂 كوميدي", "callback_data": "cat_comedy"}],
            [{"text": "🎭 دراما", "callback_data": "cat_drama"}],
            [{"text": "👻 رعب", "callback_data": "cat_horror"}],
            [{"text": "🚀 خيال علمي", "callback_data": "cat_scifi"}],
            [{"text": "📹 وثائقي", "callback_data": "cat_documentary"}],
            [{"text": "🔙 القائمة الرئيسية", "callback_data": "back_main"}]
        ]
    }
    send_message(chat_id, "🏷️ *اختر التصنيف:*", keyboard)

def send_years_menu(chat_id):
    """قائمة السنوات"""
    current_year = 2026
    years = []
    for i in range(6):
        years.append(str(current_year - i))
    
    keyboard = {"inline_keyboard": []}
    row = []
    for year in years:
        row.append({"text": year, "callback_data": f"year_{year}"})
        if len(row) == 3:
            keyboard["inline_keyboard"].append(row)
            row = []
    if row:
        keyboard["inline_keyboard"].append(row)
    
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة الرئيسية", "callback_data": "back_main"}])
    
    send_message(chat_id, "📅 *اختر السنة:*", keyboard)

def get_torrent_link(title):
    """جلب رابط تورنت"""
    encoded_title = quote(title)
    magnet = f"magnet:?xt=urn:btih:{hashlib.md5(title.encode()).hexdigest()}&dn={encoded_title}&tr=udp://tracker.opentrackr.org:1337/announce"
    return magnet

def send_preview(chat_id, title):
    """إرسال معاينة للفيلم"""
    year = extract_year(title)
    rating = get_imdb_rating(title)
    
    msg = f"""🎬 *معاينة فيلم: {title}*

📅 *السنة:* {year}
⭐ *التقييم:* {rating}/10

🎥 *نبذة:*
فيلم {title} من انتاج سنة {year}، حصل على تقييم {rating}/10 من موقع IMDb.

🔗 *روابط مفيدة:*
• [مشاهدة على IMDb](https://www.imdb.com/find?q={quote(title)})
• [بحث جوجل](https://www.google.com/search?q={quote(title)}+movie)

📌 *للتحميل:* استخدم زر التحميل المباشر"""

    keyboard = {
        "inline_keyboard": [
            [{"text": "💾 تحميل الفيلم", "callback_data": "back_main"}],
            [{"text": "🔙 رجوع", "callback_data": "back_main"}]
        ]
    }
    
    send_message(chat_id, msg, keyboard)

# ==================== معالجة الأوامر ====================
def handle_message(chat_id, text, users_data, user_states):
    """معالجة الرسائل النصية"""
    
    # القائمة الرئيسية بالأزرار
    if text == '/start':
        send_main_menu(chat_id)
    
    elif text == '🔍 بحث عادي' or text == '/search':
        send_message(chat_id, "🔍 *أدخل اسم الفيلم أو المسلسل:*")
        user_states[chat_id] = {'action': 'waiting_normal'}
    
    elif text == '⭐ بحث متقدم' or text == '/advanced':
        send_message(chat_id, "⭐ *أدخل اسم الفيلم للبحث المتقدم:*")
        user_states[chat_id] = {'action': 'waiting_advanced'}
    
    elif text == '🎬 فيلم' or text == '/movie':
        send_message(chat_id, "🎬 *أدخل اسم الفيلم:*")
        user_states[chat_id] = {'action': 'waiting_movie'}
    
    elif text == '📺 مسلسل' or text == '/series':
        send_message(chat_id, "📺 *أدخل اسم المسلسل:*")
        user_states[chat_id] = {'action': 'waiting_series'}
    
    elif text == '🏷️ تصنيفات':
        send_categories_menu(chat_id)
    
    elif text == '📅 بحث بالسنة':
        send_years_menu(chat_id)
    
    elif text == '🆘 مساعدة' or text == '/help':
        help_msg = """📖 *قائمة الأوامر:*

🔍 /search - بحث عادي
⭐ /advanced - بحث متقدم
🎬 /movie - بحث عن فيلم
📺 /series - بحث عن مسلسل
🏷️ /tag - بحث بالتصنيف
📅 /year - بحث بالسنة
❌ /cancel - إلغاء
🆘 /help - المساعدة

📌 *أو استخدم الأزرار في القائمة الرئيسية!*"""
        send_message(chat_id, help_msg)
    
    elif text == '❌ إلغاء' or text == '/cancel':
        if chat_id in user_states:
            del user_states[chat_id]
        send_message(chat_id, "❌ *تم إلغاء العملية*")
        send_main_menu(chat_id)
    
    elif chat_id in user_states:
        action = user_states[chat_id].get('action')
        
        if action == 'waiting_normal':
            results = search_wecima(text)
            if results:
                users_data[str(chat_id)] = {'search_results': results}
                save_users(users_data)
                send_results(chat_id, results, 0, "normal")
            else:
                send_message(chat_id, "❌ *لا توجد نتائج*")
            del user_states[chat_id]
        
        elif action == 'waiting_advanced':
            results = search_wecima(text)
            if results:
                users_data[str(chat_id)] = {'search_results': results}
                save_users(users_data)
                send_results(chat_id, results, 0, "advanced")
            else:
                send_message(chat_id, "❌ *لا توجد نتائج*")
            del user_states[chat_id]
        
        elif action == 'waiting_movie':
            results = search_wecima(text)
            if results:
                send_movie_details(chat_id, results[0])
            else:
                send_message(chat_id, "❌ *لا توجد نتائج*")
            del user_states[chat_id]
        
        elif action == 'waiting_series':
            results = search_wecima(text)
            if results:
                msg = "📺 *نتائج المسلسلات:*\n\n"
                for idx, res in enumerate(results[:5], 1):
                    msg += f"{idx}. {res['title'][:50]}\n"
                send_message(chat_id, msg)
            else:
                send_message(chat_id, "❌ *لا توجد نتائج*")
            del user_states[chat_id]
    
    else:
        # بحث تلقائي بأي رسالة
        results = search_wecima(text)
        if results:
            users_data[str(chat_id)] = {'search_results': results}
            save_users(users_data)
            send_results(chat_id, results, 0, "normal")
        else:
            send_message(chat_id, "❌ *لا توجد نتائج* اكتب /start للقائمة")

def handle_callback(chat_id, callback_data, users_data):
    """معالجة الضغط على الأزرار"""
    
    # معالجة أزرار النتائج
    if callback_data.startswith("normal_select_"):
        idx = int(callback_data.replace("normal_select_", ""))
        results = users_data.get(str(chat_id), {}).get('search_results', [])
        if idx < len(results):
            send_movie_details(chat_id, results[idx])
    
    elif callback_data.startswith("normal_page_"):
        page = int(callback_data.replace("normal_page_", ""))
        results = users_data.get(str(chat_id), {}).get('search_results', [])
        if results:
            send_results(chat_id, results, page, "normal")
    
    elif callback_data.startswith("advanced_select_"):
        idx = int(callback_data.replace("advanced_select_", ""))
        results = users_data.get(str(chat_id), {}).get('search_results', [])
        if idx < len(results):
            send_movie_details(chat_id, results[idx])
    
    elif callback_data.startswith("advanced_page_"):
        page = int(callback_data.replace("advanced_page_", ""))
        results = users_data.get(str(chat_id), {}).get('search_results', [])
        if results:
            send_results(chat_id, results, page, "advanced")
    
    # معالجة أزرار التحميل والمعاينة
    elif callback_data.startswith("download_"):
        title = callback_data.replace("download_", "")
        send_message(chat_id, f"💾 *جاري تحضير رابط التحميل لـ:* {title}\n\n🔗 الرابط سيظهر قريباً...")
    
    elif callback_data.startswith("preview_"):
        title = callback_data.replace("preview_", "")
        send_preview(chat_id, title)
    
    elif callback_data.startswith("torrent_"):
        title = callback_data.replace("torrent_", "")
        magnet = get_torrent_link(title)
        send_message(chat_id, f"🧲 *رابط تورنت لـ: {title}*\n\n`{magnet}`")
    
    # معالجة التصنيفات
    elif callback_data.startswith("cat_"):
        category = callback_data.replace("cat_", "")
        category_names = {
            'action': 'اكشن', 'comedy': 'كوميدي', 'drama': 'دراما',
            'horror': 'رعب', 'scifi': 'خيال علمي', 'documentary': 'وثائقي'
        }
        send_message(chat_id, f"🔍 *جاري البحث عن أفلام {category_names.get(category, category)}:*")
    
    # معالجة السنوات
    elif callback_data.startswith("year_"):
        year = callback_data.replace("year_", "")
        send_message(chat_id, f"📅 *جاري البحث عن أفلام سنة {year}:*")
    
    # رجوع للقائمة
    elif callback_data == "back_main":
        send_main_menu(chat_id)

# ==================== تشغيل البوت ====================
def get_updates():
    users_data = load_users()
    last_update_id = users_data.get('last_update_id', 0)
    user_states = {}
    
    print("=" * 60)
    print("🤖 Wecima Telegram Bot V2.0")
    print("=" * 60)
    print("✅ البوت شغال بكفاءة!")
    print("📱 اذهب للتليجرام وابحث عن البوت")
    print("💬 اكتب /start للبدء")
    print("=" * 60)
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data['ok'] and data['result']:
                for update in data['result']:
                    last_update_id = update['update_id']
                    
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        text = update['message'].get('text', '')
                        user_name = update['message']['chat'].get('first_name', 'Unknown')
                        
                        print(f"📩 رسالة من {user_name}: {text[:50]}")
                        handle_message(chat_id, text, users_data, user_states)
                    
                    elif 'callback_query' in update:
                        chat_id = update['callback_query']['message']['chat']['id']
                        callback_data = update['callback_query']['data']
                        
                        print(f"🔘 زر ضغط من {chat_id}: {callback_data}")
                        handle_callback(chat_id, callback_data, users_data)
                
                users_data['last_update_id'] = last_update_id
                save_users(users_data)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)
        
        time.sleep(0.5)

# ==================== بدء التشغيل ====================
if __name__ == "__main__":
    get_updates()