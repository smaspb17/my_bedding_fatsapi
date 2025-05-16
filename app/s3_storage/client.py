from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from aiobotocore.session import get_session
from botocore.exceptions import ClientError, EndpointConnectionError
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3MinioClient:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
    ):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
            # MinIO работает по HTTP для локального хранилища
            "use_ssl": False,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[Any, None]:
        async with self.session.create_client("s3", **self.config) as client:
            yield client

    async def upload_file(self, file, file_location: str, client):
        """Загрузка файла в MinIO"""
        try:
            await client.put_object(
                Bucket=self.bucket_name, Key=file_location, Body=file.file
            )
            logger.info(
                f"Файл {file_location} загружен в MinIO ({self.bucket_name})"
            )
        except (ClientError, EndpointConnectionError) as e:
            logger.error(f"Ошибка загрузки файла в MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке файла в MinIO: {e}")
            raise

    async def delete_one_file(self, file_name: str):
        """Удаление одного файла из MinIO"""
        try:
            async with self.get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.info(
                    f"Файл {file_name} удален из MinIO ({self.bucket_name})"
                )
                return {"message": "Файл удален"}
        except (ClientError, EndpointConnectionError) as e:
            logger.error(f"Ошибка удаления файла из MinIO: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка при удалении файла из MinIO: {e}"
            )
            raise

    async def delete_all_files(self, file_names: list[str], client):
        """Удаление нескольких файлов из MinIO"""
        try:
            for file_name in file_names:
                await client.delete_object(
                    Bucket=self.bucket_name, Key=file_name
                )
            logger.info(
                f"Удалены файлы {file_names} из MinIO ({self.bucket_name})"
            )
        except (ClientError, EndpointConnectionError) as e:
            logger.error(f"Ошибка удаления файлов из MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка при удалении файлов: {e}")
            raise


class S3SelectelClient:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
    ):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[Any, None]:
        async with self.session.create_client("s3", **self.config) as client:
            yield client

    async def upload_file(
        self,
        file,
        file_location: str,
        client,
    ):
        """Загрузка файла"""
        try:
            await client.put_object(
                Bucket=self.bucket_name, Key=file_location, Body=file.file
            )
            logger.info(
                f"Файл {file_location} загружен в хранилище {self.bucket_name}"
            )
        except ClientError as e:
            logger.error(f"Ошибка загрузки файла в Selectel: {e}")
            # raise HTTPException(status_code=400,
            #                     detail=f"Ошибка загрузки файла в S3: {e}")

    async def delete_one_file(
        self,
        file_name: str,
    ):
        """Удаление одного файла у товара из Selectel"""
        try:
            async with self.get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.info(f"Файл {file_name} удален из {self.bucket_name}")
                return None
        except ClientError as e:
            logger.error(f"Ошибка удаления файла в Selectel: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка при удалении файла из Selectel: {e}"
            )

    async def delete_all_files(self, file_names: list[str], client):
        """Удаление всех файлов у товара из Selectel"""
        try:
            for file_name in file_names:
                await client.delete_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.info(f"Файл {file_name} удален из {self.bucket_name}")
        except ClientError as e:
            logger.error(f"Ошибка удаления файлов из Selectel: {e}")
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка при удалении файлов из Selectel: {e}"
            )


S3_CONFIG = {
    "access_key": settings.S3_ACCESS_KEY,
    "secret_key": settings.S3_SECRET_KEY,
    "endpoint_url": settings.S3_ENDPOINT_URL,
    "bucket_name": settings.S3_BUCKET_NAME,
}
if settings.STORAGE_TYPE == "selectel":
    s3_client = S3SelectelClient(**S3_CONFIG)
elif settings.STORAGE_TYPE == "minio":
    s3_client = S3MinioClient(**S3_CONFIG)
