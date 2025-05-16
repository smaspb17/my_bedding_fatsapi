FROM python:3.12-slim

# Установка зависимостей для сборки C-расширений (без linux-headers для WSL)
RUN apt-get update --fix-missing && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*


# отключает создание .pyc-файлов
ENV PYTHONDONTWRITEBYTECODE=1
# отключение буферизации вывода - гарантия вывода в терминал
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# указание информации о порте по умолчанию при команде docker ps или docker port <container>
#EXPOSE 8000
#
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# параметры жетские - выполняться в любом случае даже если при запуске есть параметры в командной строке


