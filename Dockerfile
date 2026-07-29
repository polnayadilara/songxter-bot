FROM python:3.11-slim

# Устанавливаем FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Устанавливаем библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ YT-DLP ДО САМОЙ СВЕЖЕЙ ВЕРСИИ
RUN pip install --no-cache-dir --upgrade yt-dlp

# Копируем ВСЕ файлы
COPY . .

# Запускаем
CMD ["python", "bot.py"]
