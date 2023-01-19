import logging
import os
import requests
import sys
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus
from exception import ApiRequestError
from logger import new_logger


load_dotenv()
logger = new_logger(logging.getLogger(__name__))

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
RETRY_PERIOD = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(env_vars)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.debug('Отправляем сообщение в Телеграм')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        logger.debug('Сообщение в Телеграм успешно отправлено')
    except telegram.error.TelegramError as error:
        logger.error(error, exc_info=True)  # без этого pytest не проходит
        raise Exception(f'Сообщение в Телеграм нe отправлено {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        logger.debug('Отправляем запрос к API')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise ApiRequestError(
                f'Endpoint {ENDPOINT} не доступен: {response.status_code}')
        logger.debug('Ответ API получен')
        return response.json()
    except requests.RequestException as error:
        raise ApiRequestError(f'Endpoint {ENDPOINT} не доступен: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if isinstance(response, dict) is False:
        message = f'Некорректный формат ответа API: {type(response)}'
        raise TypeError(message)
    if 'homeworks' not in response:
        message = "В ответе отсутствует ключ 'homeworks'"
        raise KeyError(message)
    if 'current_date' not in response:
        message = "В ответе отсутствует ключ 'current_date'"
        raise KeyError(message)
    homework = response.get('homeworks')
    if isinstance(homework, list) is False:
        message = f'Некорректный формат списка работ: {type(homework)}'
        raise TypeError(message)
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе."""
    message = ''
    if 'homework_name' not in homework:
        message = "Отсутствует ключ 'homework_name'"
        raise KeyError(message)
    if 'status' not in homework:
        message = "Отсутствует ключ 'status'"
        raise KeyError(message)
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise IndexError(f'Неизвестный статус работы: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Переменные окружения отсутствуют. Работа невозможна.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # timestamp = timestamp - 2 * 24 * 3600
    status = ''
    message = ''
    prev_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            logger.debug(f'{homeworks}')
            if not homeworks:
                message = 'В ответе пустой список работ'
                logger.debug(f'{message}')
                continue
            message = parse_status(homeworks[0])
            logger.debug(f'{message}')
            if status != message:
                status = message
                logger.debug('Статус домашней работы обновился.')
            else:
                logger.debug('Статус домашней работы не изменился.')
        except Exception as error:
            logger.error(error, exc_info=True)
            message = f'{error}'
        finally:
            if prev_message != message:
                send_message(bot, message)
                prev_message = message
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
