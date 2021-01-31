"""Конфигурация логирования серверной части"""

import logging.handlers
import logging
import os
from base.variables import LOGGING_LEVEL

# Создание объекта-логгера с именем server
_LOGGER = logging.getLogger('server')

# Создание пути и подготовка имени файла для логирования
LOG_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(LOG_PATH, '../logs/server.log')

# Определен формат сообщений
SERVER_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')

# Создание файлового обработчика логирования
LOG_FILE = logging.handlers.TimedRotatingFileHandler(LOG_PATH, encoding='utf8', interval=1, when='D')
LOG_FILE.setFormatter(SERVER_FORMATTER)
LOG_FILE.setLevel(LOGGING_LEVEL)

# Подключение файлового обработчика к объекту-логгеру
_LOGGER.addHandler(LOG_FILE)
_LOGGER.setLevel(LOGGING_LEVEL)

# для отладки
if __name__ == '__main__':
    _LOGGER.critical('ОТЛАДКА Критическая ошибка')
    _LOGGER.error('ОТЛАДКА Ошибка')
    _LOGGER.debug('ОТЛАДКА Отладочная информация')
    _LOGGER.info('ОТЛАДКА Информационное сообщение')
