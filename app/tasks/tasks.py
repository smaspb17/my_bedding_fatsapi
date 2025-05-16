# tasks/tasks.py
import asyncio
from aiosmtplib import SMTPException, SMTPResponseException

from celery.utils.log import get_task_logger


from app.tasks.celery import celery
from app.email.service import send_email
from app.users.services.security import (
    generate_email_confirmation_link,
    generate_reset_password_link,
)

# время задержек при повторных отправках писем
retry_delays = [60, 300, 900, 1800, 3600]  # 1м, 5м, 15м, 30м, 60м

logger = get_task_logger(__name__)


@celery.task(bind=True, max_retries=5)
def send_registration_email(
    self, token: str, email: str, first_name: str, password: str
):
    """
    Отправка эл.письма о регистрации пользователя
    При ошибке 450 (временная проблема) делаем
    повторную попытку с увеличивающейся задержкой.
    """
    name = first_name if first_name else "дорогой покупатель"
    html_body = f"""
            <html>
                <body>
                    <h3>Здравствуйте {name}!</h3>
                    <p>Просим Вас подтвердить свою электронную почту, пройдя по 
                    ссылке ниже:</p>
                    <p><a href="{generate_email_confirmation_link(token)}">Подтвердить 
                    почту</a></p>
                    <p>Это необходимо для отправки Вам информации о статусе заказов,
                    а также объявлениях о проводимых акциях и промокодах.</p>
                    <p>Для входа в свою учетную запись на сайте нажмите на иконку: <img
                    src="https://img.icons8.com/?size=100&id=fJ7hcfUGpKG7&format=png&color=000000" alt=""
                    style="width:20px;height:20px;"></p>
                    <p><strong>Данные для входа:</strong><br>
                    Email: {email}<br>
                    Пароль: {password}</p>
                    <p>Когда вы войдете в свою учетную запись, вам будут доступны:
                        <ul>
                            <li>Быстрое оформление заказов</li>
                            <li>Проверка статуса заказов</li>
                            <li>Просмотр истории заказов</li>
                            <li>Изменение информации учетной записи</li>
                            <li>Сохранение дополнительных адресов</li>
                        </ul>
                    </p>
                    <p>Если у Вас возникли вопросы по поводу Вашей учетной<br>
                    записи или любой другой вопрос, пожалуйста, свяжитесь<br>
                    с нами по адресу info@mybedding.ru или по телефону<br>
                    8(800)800-00-00</p>
                    <p>Если Вы не хотите получать информацию<br>
                    о новых скидках и акциях с сайта mybedding.ru<br>
                    отпишитесь по ссылке.</p>
                    <p>С уважением,<br>Магазин MyBedding.<br>
                    Адрес сайта - https://mybedding.ru</p>
                </body>
            </html>
            """
    try:
        asyncio.run(send_email(email, "Добро пожаловать!", html_body))
        logger.info(
            "Отправлено эл.письмо о регистрации пользователя: %s", email
        )
        return 1

    except SMTPResponseException as e:
        if e.code == 450:
            delay = retry_delays[self.request.retries]
            logger.warning(
                "SMTP 450 ошибка при отправке письма %s. "
                "Повторная попытка #%d через %d секунд...",
                email,
                self.request.retries + 1,
                delay,
            )
            raise self.retry(exc=e, countdown=delay)
        logger.error("SMTPResponseException (код %s): %s", e.code, e.message)
        return 0

    except SMTPException as e:
        logger.error(
            "Ошибка отправки эл.письма о регистрации пользователя: %s", e
        )
        return 0
    except Exception as e:
        logger.error(
            "Неизвестная ошибка при отправке эл.письма о регистрации пользователя: %s",
            e,
        )
        return 0


@celery.task
def send_resend_email_confirmation(token: str, email: str, first_name: str):
    """
    Отправка эл.письма о повторном подтверждении email пользователя
    При ошибке 450 (временная проблема) делаем
    повторную попытку с увеличивающейся задержкой.
    """
    name = first_name if first_name else "дорогой покупатель"
    html_body = f"""
            <html>
                <body>
                    <h3>Здравствуйте {name}!</h3>
                    <p>Просим Вас подтвердить свою электронную почту, пройдя по 
                    ссылке ниже:</p>
                    <p><a href="{generate_email_confirmation_link(token)}">Подтвердить 
                    почту</a></p>
                    <p>Это необходимо для отправки Вам информации о статусе заказов,
                    а также объявлениях о проводимых акциях и промокодах.</p>
                    <p>Для входа в свою учетную запись на сайте нажмите на иконку: <img
                    src="https://img.icons8.com/?size=100&id=fJ7hcfUGpKG7&format=png&color=000000" alt=""
                    style="width:20px;height:20px;"></p>
                    <p>Если у Вас возникли вопросы по поводу Вашей учетной<br>
                    записи или любой другой вопрос, пожалуйста, свяжитесь<br>
                    с нами по адресу info@mybedding.ru или по телефону<br>
                    8(800)800-00-00</p>
                    <p>Если Вы не хотите получать информацию<br>
                    о новых скидках и акциях с сайта mybedding.ru<br>
                    отпишитесь по ссылке.</p>
                    <p>С уважением,<br>Магазин MyBedding.<br>
                    Адрес сайта - https://mybedding.ru</p>
                </body>
            </html>
            """
    try:
        asyncio.run(
            send_email(email, "Повторное подтверждение email", html_body)
        )
        logger.info(
            "Отправлено эл.письмо о повторном подтверждении email: %s", email
        )
        return 1
    except SMTPException as e:
        logger.error(
            "Ошибка отправки эл.письма о повторном подтверждении email: %s", e
        )
        return 0
    except Exception as e:
        logger.error(
            "Неизвестная ошибка при отправке эл.письма "
            "о повторном подтверждении email: %s",
            e,
        )
        return 0


@celery.task
def send_change_password(email: str, password: str, first_name: str):
    """
    Отправка эл.письма о смене пароля пользователя
    При ошибке 450 (временная проблема) делаем
    повторную попытку с увеличивающейся задержкой.
    """
    name = first_name if first_name else "дорогой покупатель"
    html_body = f"""
            <html>
                <body>
                    <h3>Здравствуйте {name}!</h3>
                    <p>Ваш пароль был успешно изменен.</p>
                    <p>Для входа в свою учетную запись на сайте нажмите
                    на иконку: <imgsrc="https://img.icons8.com/?size=100&id=
                    fJ7hcfUGpKG7&format=png&color=000000" alt=""
                    style="width:20px;height:20px;"></p>
                    <p><strong>Данные для входа:</strong><br>
                    Email: {email}<br>
                    Пароль: {password}</p>
                    <p>Если у Вас возникли вопросы по поводу Вашей учетной<br>
                    записи или любой другой вопрос, пожалуйста, свяжитесь<br>
                    с нами по адресу info@mybedding.ru или по телефону<br>
                    8(800)800-00-00</p>
                    <p>С уважением,<br>Магазин MyBedding.<br>
                    Адрес сайта - https://mybedding.ru</p>  
                </body>
            </html>
            """
    try:
        asyncio.run(send_email(email, "Смена пароля", html_body))
        logger.info("Отправлено эл.письмо о смене пароля: %s", email)
        return 1
    except SMTPException as e:
        logger.error("Ошибка отправки эл.письма о смене пароля: %s", e)
        return 0
    except Exception as e:
        logger.error(
            "Неизвестная ошибка при отправке эл.письма о смене пароля: %s", e
        )
        return 0


@celery.task
def send_reset_password(email: str, token: str):
    """
    Отправка эл.письма для сброса пароля пользователя
    При ошибке 450 (временная проблема) делаем
    повторную попытку с увеличивающейся задержкой.
    """
    html_body = f"""
            <html>
                <body>
                    <h3>Здравствуйте!</h3>
                    <p>Для сброса пароля нажмите на ссылку ниже:</p>
                    <p><a href="{generate_reset_password_link(email, token)}">
                    Сбросить пароль</a></p>
                    <p>Если у Вас возникли вопросы по поводу Вашей учетной<br>
                    записи или любой другой вопрос, пожалуйста, свяжитесь<br>
                    с нами по адресу info@mybedding.ru или по телефону<br>
                    8(800)800-00-00</p>
                    <p>С уважением,<br>Магазин MyBedding.<br>
                    Адрес сайта - https://mybedding.ru</p>
                </body>
            </html>
            """
    try:
        asyncio.run(send_email(email, "Сброс пароля", html_body))
        logger.info("Отправлено эл.письмо о сбросе пароля: %s", email)
        return 1
    except SMTPException as e:
        logger.error("Ошибка отправки эл.письма о сбросе пароля: %s", e)
        return 0
    except Exception as e:
        logger.error(
            "Неизвестная ошибка при отправке эл.письма о сбросе пароля: %s", e
        )
        return 0


@celery.task
def send_set_password(email: str, password: str, first_name: str):
    """
    Отправка эл.письма для установки пароля пользователя
    При ошибке 450 (временная проблема) делаем повторную
    попытку с увеличивающейся задержкой.
    """
    name = first_name if first_name else "дорогой покупатель"
    html_body = f"""
            <html>
                <body>
                    <h3>Здравствуйте {name}!</h3>
                    <p>Вы успешно сбросили пароль на сайте mybedding.ru.</p>
                    <p>Для входа в свою учетную запись на сайте нажмите на иконку: <img
                    src="https://img.icons8.com/?size=100&id=fJ7hcfUGpKG7&format=png&color=000000" alt=""
                    style="width:20px;height:20px;"></p>
                    <p><strong>Данные для входа:</strong><br>
                    Email: {email}<br>
                    Пароль: {password}</p>
                    <p>Если у Вас возникли вопросы по поводу Вашей учетной<br>
                    записи или любой другой вопрос, пожалуйста, свяжитесь<br>
                    с нами по адресу info@mybedding.ru или по телефону<br>
                    8(800)800-00-00</p>
                    <p>С уважением,<br>Магазин MyBedding.<br>
                    Адрес сайта - https://mybedding.ru</p>
                </body>
            </html>
            """
    try:
        asyncio.run(send_email(email, "Установка пароля", html_body))
        logger.info("Отправлено эл.письмо о установке пароля: %s", email)
        return 1
    except SMTPException as e:
        logger.error("Ошибка отправки эл.письма о установке пароля: %s", e)
        return 0
    except Exception as e:
        logger.error(
            "Неизвестная ошибка при отправке эл.письма о установке пароля: %s",
            e,
        )
        return 0
