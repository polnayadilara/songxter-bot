import os
import time
import requests
import telebot
import yt_dlp
import re
from supabase import create_client, Client

# Твои ключи
TELEGRAM_TOKEN = "8570417193:AAEJYVoZcxWKT6rCSx_wHtKgaMTBKuEJcps"
SUPABASE_URL = "https://jcrubxyvppxexskettfk.supabase.co"
SUPABASE_KEY = "sb_publishable_oLxlbi_TGD3pT9w3yl04Lg_cQ9rHq5t"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привет! Я твой личный Songxter-бот.\n"
                          "Скинь мне ссылку, и я добавлю трек.\n"
                          "💡 Лайфхак: можно написать название альбома через пробел после ссылки!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    
    # Разделяем текст на ссылку и ручной ввод альбома
    parts = text.split(" ", 1)
    url = parts[0]
    manual_album = parts[1].strip() if len(parts) > 1 else None
    
    if not url.startswith("http"):
        bot.reply_to(message, "Пожалуйста, отправь правильную ссылку (начинается с http/https).")
        return

    msg = bot.reply_to(message, "⏳ Начинаю скачивание трека... Это займет пару минут.")

    try:
        # 1. Настройки для скачивания
        ydl_opts = {
            'format': 'bestaudio/best',
            'cookiefile': 'cookies.txt',
            'extractor_args': {'youtube': ['player_client=android']}, # <--- ДОБАВЬ ВОТ ЭТУ СТРОЧКУ
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': True
        }
        # 2. Скачивание и извлечение данных
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            
            title = info.get('track', info.get('title', 'Неизвестное название'))
            artist = info.get('artist', info.get('uploader', 'Неизвестный артист'))
            album = info.get('album')
            description = info.get('description', '')
            thumbnail_url = info.get('thumbnail', None)

            # Если системного альбома нет, пробуем найти его в кавычках в описании
            if not album:
                match = re.search(r'"([^"]+)"', description)
                if match:
                    album = match.group(1)
                else:
                    album = 'Без альбома'
            
            # Если пользователь написал альбом вручную в ТГ - это всегда в приоритете!
            if manual_album:
                album = manual_album
            
            if " - " in title and info.get('track') is None:
                parts = title.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()

            local_mp3_filename = f"{video_id}.mp3"

        bot.edit_message_text("☁️ Скачано! Загружаю в облако Songxter...", chat_id=message.chat.id, message_id=msg.message_id)

        timestamp = int(time.time())
        
        # 3. Загрузка обложки
        cover_public_url = None
        if thumbnail_url:
            resp = requests.get(thumbnail_url)
            if resp.status_code == 200:
                cover_filename = f"cover_tg_{timestamp}.jpg"
                supabase.storage.from_("music_files").upload(cover_filename, resp.content)
                cover_public_url = supabase.storage.from_("music_files").get_public_url(cover_filename)

        # 4. Загрузка MP3 файла
        mp3_filename = f"tg_{timestamp}_{local_mp3_filename}"
        with open(local_mp3_filename, 'rb') as f:
            supabase.storage.from_("music_files").upload(mp3_filename, f)
        
        mp3_public_url = supabase.storage.from_("music_files").get_public_url(mp3_filename)

        # 5. Добавление записи в базу данных
        supabase.table("songs").insert({
            "title": title,
            "artist": artist,
            "album": album, 
            "file_url": mp3_public_url,
            "cover_url": cover_public_url,
            "track_number": 1
        }).execute()

        # 6. Удаляем локальный файл
        if os.path.exists(local_mp3_filename):
            os.remove(local_mp3_filename)

        bot.edit_message_text(f"✅ Успешно!\n\n🎵 Трек: **{artist} - {title}**\n💿 Альбом: **{album}**\n\nТрек уже в твоем приложении!", 
                              chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ Произошла ошибка:\n{str(e)}", chat_id=message.chat.id, message_id=msg.message_id)
        for file in os.listdir():
            if file.endswith(".webm") or file.endswith(".m4a") or file.endswith(".mp3"):
                os.remove(file)

print("Бот запущен и ждет ссылки...")
bot.infinity_polling()
