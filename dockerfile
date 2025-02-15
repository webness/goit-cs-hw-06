# Використаємо офіційний Python-образ
FROM python:3.11

# Встановимо робочу директорію
WORKDIR /app

# Скопіюємо усі файли в контейнер
COPY . /app

# Встановимо залежності (pymongo тощо). За потреби додайте інші.
RUN pip install --no-cache-dir pymongo

# Запускаємо main.py
CMD ["python", "main.py"]
