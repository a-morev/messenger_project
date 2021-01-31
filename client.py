"""Программа клиента"""

import argparse
import os
import sys

from Crypto.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox

from base.variables import *
import log.config.client_log_config
from client.database import ClientDatabase
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
from client.transport import ClientTransport


def log_dec(func):
    """Функция-декоратор"""

    def wrap(*args, **kwargs):
        """Обертка"""
        conclusion = func(*args, **kwargs)
        CLIENT_LOGGER.debug(f'Вызвана функция {func.__name__} с параметрами ({args}, {kwargs}). '
                            f'Из модуля {func.__module__}')
        return conclusion

    return wrap


# Инициализация регистратора
CLIENT_LOGGER = logging.getLogger('client')


# noinspection PyShadowingNames
@log_dec
def argument_parser():
    """Парсер параметров коммандной строки,
    чтение параметров, возвращаем 3 параметра.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('host', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.host
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    # проверка корректности номера порта
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(f'Попытка запуска клиента с указанием некорректного порта {server_port}')
        sys.exit(1)

    return server_address, server_port, client_name, client_passwd


if __name__ == '__main__':
    """
    Загрузка параметров коммандной строки
    """
    server_address, server_port, client_name, client_passwd = argument_parser()

    # создание клиентского приложения
    client_app = QApplication(sys.argv)

    # Если пользователь не был указан в командной строке, запрашивается его имя
    start_dialog = UserNameDialog()
    if not client_name or not client_passwd:
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
            CLIENT_LOGGER.debug(f'Using USERNAME = {client_name}, PASSWD = {client_passwd}.')
        else:
            sys.exit(0)

    CLIENT_LOGGER.info(f'Клиент запущен - адрес хоста: {server_address} порт: {server_port}, '
                       f'пользователь: {client_name}')

    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    # !!!keys.publickey().export_key()
    CLIENT_LOGGER.debug("Keys successfully loaded.")

    # Инициализация БД
    database = ClientDatabase(client_name)

    # Инициализация сокета и запуск потока
    try:
        tcp_sock = ClientTransport(server_port, server_address, database, client_name, client_passwd, keys)
        CLIENT_LOGGER.debug("Socket ready.")
    except Exception as ErrorNotConnection:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', f'{ErrorNotConnection} - нет соединения')
        CLIENT_LOGGER.error(f'Не удалось подключиться к серверу {server_address}:{server_port}')
        sys.exit(1)
    tcp_sock.setDaemon(True)
    tcp_sock.start()

    # Создание GUI
    main_window = ClientMainWindow(database, tcp_sock, keys)
    main_window.make_connection(tcp_sock)
    main_window.setWindowTitle(f'Чат-программа b-release - {client_name}')
    client_app.exec_()

    # После закрытия графической оболочки, закрываем сокет
    tcp_sock.transport_shutdown()
    tcp_sock.join()
