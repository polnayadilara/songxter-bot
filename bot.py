import os
import time
import requests
import telebot
import yt_dlp
import re
import threading
from flask import Flask
from supabase import create_client, Client

# --- МИКРО-СЕРВЕР ДЛЯ ОБЛАКА ---
# Облачные сервисы требуют, чтобы программа прослушивала веб-порт, иначе они её убивают.
app = Flask(__name__)

@app.route('/')
def alive():
    return "Songxter Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Запускаем веб-сервер в фоновом режиме
threading.Thread(target=run_web, daemon=True).start()
# -------------------------------

# Твои ключи
TELEGRAM_TOKEN = "8570417193:AAEJYVoZcxWKT6rCSx_wHtKgaMTBKuEJcps"
SUPABASE_URL = "https://jcrubxyvppxexskettfk.supabase.co"
SUPABASE_KEY = "sb_publishable_oLxlbi_TGD3pT9w3yl04Lg_cQ9rHq5t"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привет! Я твой личный Songxter-бот.\n"
                          "Скинь мне ссылку, и я добавлю трек 24/7!\n"
                          "💡 Можно написать название альбома через пробел после ссылки.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    
    parts = text.split(" ", 1)
    url = parts[0]
    manual_album = parts[1].strip() if len(parts) > 1 else None
    
    if not url.startswith("http"):
        bot.reply_to(message, "Пожалуйста, отправь правильную ссылку (начинается с http/https).")
        return

    msg = bot.reply_to(message, "⏳ Начинаю скачивание трека (из облака)...")

    try:
        # ОБНОВЛЕННЫЕ НАСТРОЙКИ: удален ffmpeg_location, Linux найдет его сам!
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            
            title = info.get('track', info.get('title', 'Неизвестное название'))
            artist = info.get('artist', info.get('uploader', 'Неизвестный артист'))
            album = info.get('album')
            description = info.get('description', '')
            thumbnail_url = info.get('thumbnail', None)

            if not album:
                match = re.search(r'"([^"]+)"', description)
                album = match.group(1) if match else 'Без альбома'
            
            if manual_album:
                album = manual_album
            
            if " - " in title and info.get('track') is None:
                parts = title.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()

            local_mp3_filename = f"{video_id}.mp3"

        bot.edit_message_text("☁️ Скачано! Загружаю в базу Songxter...", chat_id=message.chat.id, message_id=msg.message_id)

        timestamp = int(time.time())
        cover_public_url = None
        
        if thumbnail_url:
            resp = requests.get(thumbnail_url)
            if resp.status_code == 200:
                cover_filename = f"cover_tg_{timestamp}.jpg"
                supabase.storage.from_("music_files").upload(cover_filename, resp.content)
                cover_public_url = supabase.storage.from_("music_files").get_public_url(cover_filename)

        mp3_filename = f"tg_{timestamp}_{local_mp3_filename}"
        with open(local_mp3_filename, 'rb') as f:
            supabase.storage.from_("music_files").upload(mp3_filename, f)
        
        mp3_public_url = supabase.storage.from_("music_files").get_public_url(mp3_filename)

        supabase.table("songs").insert({
            "title": title,
            "artist": artist,
            "album": album, 
            "file_url": mp3_public_url,
            "cover_url": cover_public_url,
            "track_number": 1
        }).execute()

        if os.path.exists(local_mp3_filename):
            os.remove(local_mp3_filename)

        bot.edit_message_text(f"✅ Успешно!\n\n🎵 Трек: **{artist} - {title}**\n💿 Альбом: **{album}**", 
                              chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка:\n{str(e)}", chat_id=message.chat.id, message_id=msg.message_id)
        for file in os.listdir():
            if file.endswith((".webm", ".m4a", ".mp3")):
                os.remove(file)

print("Бот запущен в облаке!")
bot.infinity_polling()