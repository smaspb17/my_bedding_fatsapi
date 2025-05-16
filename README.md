# my_bedding_fatsapi
API интернет-магазина MyBеdding

Запуск uvicorn
```shell
uvicorn app.main:app --reload
```
Команды Alembic
```shell
alembic init -t async migrations
alembic revision --autogenerate -m "comment"
alembic upgrade head
alembic check
```

Запуск redis (нужен для fastapi-cache2, smtp Celery, )
```shell
docker run -it --rm --name redis -p 6379:6379 redis
sudo service redis-server start
redis-cli
sudo service redis-server status
```

Запуск rabbitmq с management (веб-интерфейс)
```shell
docker run --name rabbitmq -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=12345 -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management
```
После запуска проходим по адресу http://127.0.0.1:15672 (guest:guest)

# Запуск сервера minio для linux
```
minio server ~/minio-data --console-address :9001
```
Проверка сервера
```
which minio
```
Запуск терминала
```
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
```
Пример команд:
```
mc mb local/my-bedding       # создать бакет (без _)
mc ls local                 # посмотреть бакеты
mc cp файл local/mybucket  # загрузить файл
```


# Запуск сервера minio для windows
```shell
C:\minio\minio.exe server C:\minio --console-address :9001
```
Запуск терминала minio
```shell
C:\minio\mc.exe alias set local http://127.0.0.1:9000 minioadmin minioadmin
или
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
```
Получение статуса сервера minio
```shell
C:\minio\mc.exe admin info local 
или
mc admin info local 
```
Получить справку 
```shell
mc --help
```


Запуск Celery
```bash
celery -A app.tasks.celery:celery worker --loglevel=INFO --pool=solo

```
Запуск Flower
```bash
celery -A app.tasks.celery:celery flower --port=5555
```
