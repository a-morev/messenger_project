"""Программа сервера"""

import argparse
import configparser
import os
import sys
import threading

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from base.utils import *
from base.variables import *
from server.center import MessageProcessor
from server.database import ServerRepository
from server.main_window import MainWindow
import log.config.server_log_config


def log_dec(func):
    """Функция-декоратор"""

    def wrap(*args, **kwargs):
        """Обертка"""
        conclusion = func(*args, **kwargs)
        SERVER_LOGGER.debug(f'Вызвана функция {func.__name__} с параметрами ({args}, {kwargs}). '
                            f'Из модуля {func.__module__}')
        return conclusion

    return wrap


# Инициализация регистратора
SERVER_LOGGER = logging.getLogger('server')


@log_dec
def argument_parser(default_port, default_address):
    """
    Парсер параметров коммандной строки,
    чтение параметров, возвращает 2 параметров.
    """
    SERVER_LOGGER.debug(
        f'Инициализация парсера аргументов коммандной строки: {sys.argv}')
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_port = namespace.p
    listen_address = namespace.a
    gui = namespace.no_gui
    SERVER_LOGGER.debug('Аргументы успешно загружены.')
    return listen_address, listen_port, gui


# Загрузка файла конфигурации
@log_dec
def config_load():
    """Парсер конфигурационного ini файла."""
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'listen_address', '')
        config.set('SETTINGS', 'database_path', '')
        config.set('SETTINGS', 'database_file', 'server_database.db3')
        return config


@log_dec
def main():
    # Загрузка файла конфигурации сервера
    config = config_load()

    # загрузка параметров командной строки, если нет параметров, то значения по умоланию.
    listen_address, listen_port, gui = argument_parser(config['SETTINGS']['default_port'],
                                                       config['SETTINGS']['listen_address'])

    # объявление БД
    database = ServerRepository(os.path.join(config['SETTINGS']['database_path'],
                                             config['SETTINGS']['database_file']))

    server = MessageProcessor(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Если  указан параметр без GUI, то запускается
    # простой обработчик консольного ввода
    if gui:
        while True:
            command = input('Введите exit для завершения работы сервера.')
            if command == 'exit':
                # Если выход, то завршаем основной цикл сервера.
                server.running = False
                server.join()
                break

    # иначе, создается графическое окружение для сервера
    else:
        server_app = QApplication(sys.argv)
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(database, server, config)

        # Запускаем GUI
        server_app.exec_()

        # По закрытию окон останавливаем обработчик сообщений
        server.running = False


if __name__ == '__main__':
    main()
