FROM python:3.11-slim

# Устанавливаем FFmpeg прямо на облачный сервер
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Копируем и устанавливаем библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем нашего бота
COPY bot.py .

# Запускаем
CMD ["python", "bot.py"]