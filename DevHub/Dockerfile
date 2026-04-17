# 1. Беремо офіційний легкий образ Python
FROM python:3.11-slim

# 2. Встановлюємо системні бібліотеки, необхідні для Tkinter та PostgreSQL
# Це потрібно, бо в чистому Python-образі немає графічних пакетів
RUN apt-get update && apt-get install -y \
    python3-tk \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. Створюємо робочу директорію всередині контейнера
WORKDIR /app

# 4. Копіюємо файл зі списком бібліотек
COPY requirements.txt .

# 5. Встановлюємо всі залежності (psycopg2, pandas, dotenv тощо)
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копіюємо весь твій код (main.py, model.py, папка img тощо) у контейнер
COPY . .

# 7. Команда для запуску твоєї програми
CMD ["python", "main.py"]