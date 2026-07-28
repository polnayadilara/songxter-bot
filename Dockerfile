FROM python:3.11-slim

# Устанавливаем FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Устанавливаем библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЕ файлы (включая bot.py и cookies.txt)
COPY . .

# Запускаем
CMD ["python", "bot.py"]
