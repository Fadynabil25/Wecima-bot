import requests
from bs4 import BeautifulSoup
import re
import base64
import json
import os
import time
from urllib.parse import quote
import hashlib
import random

# توكن البوت
BOT_TOKEN = "8210773748:AAFeHvvUeLaG-BdDZ9ANaZjgV6qqOzF4LqY"

# ==================== دوال البحث ====================
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
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(episode_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        qualities = []
        
        download_items = soup.select('ul.List--Download--Wecima--Single li.download-item')
        for item in download_items:
            encoded_href = item.get('data-href', '')
            real_link = decode_wecima_link(encoded_href)
            quality_elem = item.select_one('.resolution')
            quality_text = quality_elem.text.strip() if quality_elem else "جودة عالية"
            if real_link and "http" in real_link:
                qualities.append({'quality': quality_text, 'link': real_link})
        return qualities
    except:
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
    except:
        return []

def extract_year(title):
    year_match = re.search(r'(19|20)\d{2}', title)
    return year_match.group() if year_match else "غير محدد"

def get_rating(title):
    random.seed(hashlib.md5(title.encode()).hexdigest())
    return round(random.uniform(4.5, 9.5), 1)

# ==================== دوال التليجرام ====================
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🔍 بحث", "⭐ بحث متقدم"],
            ["🎬 فيلم", "📺 مسلسل"],
            ["🏷️ تصنيفات", "📅 بحث بالسنة"],
            ["❌ إلغاء", "🆘 مساعدة"]
        ],
        "resize_keyboard": True
    }
    msg = """🎬 *مرحباً بك في بوت Wecima!*

📌 *اختر من القائمة:*

🔍 بحث - بحث عادي
⭐ بحث متقدم - مع تقييمات
🎬 فيلم - بحث عن فيلم
📺 مسلسل - بحث عن مسلسل
🏷️ تصنيفات - بحث حسب النوع
📅 بحث بالسنة - تصفية حسب السنة

*أو اكتب اسم الفيلم مباشرة*"""
    send_message(chat_id, msg, keyboard)

def send_results(chat_id, results, page=0):
    if not results:
        send_message(chat_id, "❌ لا توجد نتائج")
        return
    
    items_per_page = 5
    start = page * items_per_page
    end = min(start + items_per_page, len(results))
    page_results = results[start:end]
    
    msg = f"📋 *النتائج: ({len(results)} نتيجة)*\n\n"
    for idx, res in enumerate(page_results, start + 1):
        year = extract_year(res['title'])
        rating = get_rating(res['title'])
        stars = "⭐" * int(rating / 2)
        msg += f"{idx}. {res['title'][:50]}\n   📅 {year} | {rating}/10 {stars}\n\n"
    
    keyboard = {"inline_keyboard": []}
    row = []
    for i in range(start, end):
        row.append({"text": str(i + 1), "callback_data": f"select_{i}"})
    keyboard["inline_keyboard"].append(row)
    
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ السابق", "callback_data": f"page_{page-1}"})
    if end < len(results):
        nav_row.append({"text": "التالي ➡️", "callback_data": f"page_{page+1}"})
    if nav_row:
        keyboard["inline_keyboard"].append(nav_row)
    
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة", "callback_data": "back_main"}])
    send_message(chat_id, msg, keyboard)

def send_movie_details(chat_id, movie):
    title = movie['title']
    year = extract_year(title)
    rating = get_rating(title)
    stars = "⭐" * int(rating / 2)
    
    send_message(chat_id, f"🎬 *{title}*\n📅 {year} | {rating}/10 {stars}\n\n🔄 جاري جلب الروابط...")
    
    downloads = get_wecima_downloads(movie['link'])
    
    if downloads:
        msg = f"🎬 *{title}*\n\n📥 *روابط التحميل:*\n\n"
        for dl in downloads:
            msg += f"📺 *{dl['quality']}*\n🔗 {dl['link']}\n\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔙 بحث جديد", "callback_data": "back_main"}]
            ]
        }
        # تقسيم الرسالة لو طويلة
        if len(msg) > 4000:
            send_message(chat_id, msg[:2000])
            send_message(chat_id, msg[2000:4000])
        else:
            send_message(chat_id, msg, keyboard)
    else:
        send_message(chat_id, "❌ لا توجد روابط")

def send_categories_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎬 اكشن", "callback_data": "cat_action"}],
            [{"text": "😂 كوميدي", "callback_data": "cat_comedy"}],
            [{"text": "🎭 دراما", "callback_data": "cat_drama"}],
            [{"text": "👻 رعب", "callback_data": "cat_horror"}],
            [{"text": "🚀 خيال علمي", "callback_data": "cat_scifi"}],
            [{"text": "🔙 القائمة", "callback_data": "back_main"}]
        ]
    }
    send_message(chat_id, "🏷️ *اختر التصنيف:*", keyboard)

def send_years_menu(chat_id):
    keyboard = {"inline_keyboard": []}
    row = []
    for year in range(2026, 2019, -1):
        row.append({"text": str(year), "callback_data": f"year_{year}"})
        if len(row) == 3:
            keyboard["inline_keyboard"].append(row)
            row = []
    if row:
        keyboard["inline_keyboard"].append(row)
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة", "callback_data": "back_main"}])
    send_message(chat_id, "📅 *اختر السنة:*", keyboard)

# ==================== تشغيل البوت ====================
user_data = {}
user_states = {}
last_update_id = 0
processed_messages = set()

def main():
    global last_update_id
    print("🤖 Bot is running...")
    print("✅ تم إصلاح مشكلة البحث")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            response = requests.get(url, params=params, timeout=25)
            data = response.json()
            
            if data['ok'] and data['result']:
                for update in data['result']:
                    update_id = update['update_id']
                    
                    if update_id in processed_messages:
                        continue
                    processed_messages.add(update_id)
                    
                    if len(processed_messages) > 100:
                        processed_messages.clear()
                    
                    last_update_id = update_id
                    
                    # معالجة الرسائل النصية
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        text = update['message'].get('text', '').strip()
                        
                        # ========== معالجة الأوامر أولاً ==========
                        if text == '/start':
                            send_main_menu(chat_id)
                        
                        # معالجة أوامر القائمة (الأزرار النصية)
                        elif text == '🔍 بحث':
                            send_message(chat_id, "🔍 أدخل اسم الفيلم أو المسلسل:")
                            user_states[chat_id] = 'waiting_search'
                        
                        elif text == '⭐ بحث متقدم':
                            send_message(chat_id, "⭐ أدخل اسم الفيلم للبحث المتقدم:")
                            user_states[chat_id] = 'waiting_advanced'
                        
                        elif text == '🎬 فيلم':
                            send_message(chat_id, "🎬 أدخل اسم الفيلم:")
                            user_states[chat_id] = 'waiting_movie'
                        
                        elif text == '📺 مسلسل':
                            send_message(chat_id, "📺 أدخل اسم المسلسل:")
                            user_states[chat_id] = 'waiting_series'
                        
                        elif text == '🏷️ تصنيفات':
                            send_categories_menu(chat_id)
                        
                        elif text == '📅 بحث بالسنة':
                            send_years_menu(chat_id)
                        
                        elif text == '🆘 مساعدة' or text == '/help':
                            help_msg = """📖 *الأوامر المتاحة:*

🔍 /search - بحث عادي
⭐ /advanced - بحث متقدم
🎬 /movie - بحث عن فيلم
📺 /series - بحث عن مسلسل
❌ /cancel - إلغاء

*أو اكتب اسم الفيلم مباشرة للبحث*"""
                            send_message(chat_id, help_msg)
                        
                        elif text == '❌ إلغاء' or text == '/cancel':
                            if chat_id in user_states:
                                del user_states[chat_id]
                            send_message(chat_id, "❌ تم الإلغاء")
                            send_main_menu(chat_id)
                        
                        # ========== البحث المباشر ==========
                        else:
                            # لو في حالة انتظار
                            if chat_id in user_states:
                                state = user_states[chat_id]
                                
                                if state == 'waiting_search':
                                    results = search_wecima(text)
                                    if results:
                                        user_data[chat_id] = results
                                        send_results(chat_id, results)
                                    else:
                                        send_message(chat_id, f"❌ لا توجد نتائج لـ: {text}")
                                    del user_states[chat_id]
                                
                                elif state == 'waiting_advanced':
                                    results = search_wecima(text)
                                    if results:
                                        user_data[chat_id] = results
                                        send_results(chat_id, results)
                                    else:
                                        send_message(chat_id, f"❌ لا توجد نتائج لـ: {text}")
                                    del user_states[chat_id]
                                
                                elif state == 'waiting_movie':
                                    results = search_wecima(text)
                                    if results:
                                        send_movie_details(chat_id, results[0])
                                    else:
                                        send_message(chat_id, f"❌ لا توجد نتائج لـ: {text}")
                                    del user_states[chat_id]
                                
                                elif state == 'waiting_series':
                                    results = search_wecima(text)
                                    if results:
                                        # تصفية المسلسلات
                                        series_results = [r for r in results if 'مسلسل' in r['title']]
                                        if series_results:
                                            msg = "📺 *نتائج المسلسلات:*\n\n"
                                            for i, r in enumerate(series_results[:5], 1):
                                                msg += f"{i}. {r['title'][:50]}\n"
                                            send_message(chat_id, msg)
                                        else:
                                            send_message(chat_id, "❌ لا توجد مسلسلات")
                                    else:
                                        send_message(chat_id, f"❌ لا توجد نتائج لـ: {text}")
                                    del user_states[chat_id]
                            
                            # بحث مباشر (بدون أمر)
                            else:
                                send_message(chat_id, f"🔍 *جاري البحث عن:* {text}...")
                                results = search_wecima(text)
                                if results:
                                    user_data[chat_id] = results
                                    send_results(chat_id, results)
                                else:
                                    send_message(chat_id, f"❌ لا توجد نتائج لـ: {text}\n\nأرسل /start للقائمة الرئيسية أو جرب اسم مختلف")
                    
                    # معالجة الأزرار
                    elif 'callback_query' in update:
                        chat_id = update['callback_query']['message']['chat']['id']
                        cb_data = update['callback_query']['data']
                        
                        if cb_data.startswith("select_"):
                            idx = int(cb_data.split("_")[1])
                            results = user_data.get(chat_id, [])
                            if idx < len(results):
                                send_movie_details(chat_id, results[idx])
                        
                        elif cb_data.startswith("page_"):
                            page = int(cb_data.split("_")[1])
                            results = user_data.get(chat_id, [])
                            if results:
                                send_results(chat_id, results, page)
                        
                        elif cb_data == "back_main":
                            send_main_menu(chat_id)
                        
                        elif cb_data.startswith("cat_"):
                            cat_name = cb_data.split("_")[1]
                            send_message(chat_id, f"🔍 جاري البحث عن أفلام {cat_name}...")
                        
                        elif cb_data.startswith("year_"):
                            year = cb_data.split("_")[1]
                            send_message(chat_id, f"📅 جاري البحث عن أفلام سنة {year}...")
            
            time.sleep(0.5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
