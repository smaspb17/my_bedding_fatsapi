# my_bedding_fatsapi
API интернет-магазина MyBеdding


Запуск redis (нужен для fastapi-admin, )
```shell
docker run -it --rm --name redis -p 6379:6379 redis
sudo service redis-server start
redis-cli
sudo service redis-server status
```

Запуск сервера minio
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
