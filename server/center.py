import threading
import select
import socket
import json
import hmac
import binascii
import os

from base.decorators import login_required
from base.metaclasses import ServerVerifier
from base.descriptors import PortValidator
from base.variables import *
from base.utils import sending_message, getting_message
import log.config.server_log_config

# Загрузка логера
SERVER_LOGGER = logging.getLogger('server')


class MessageProcessor(threading.Thread):
    """
    Основной класс сервера. Принимает содинения, словари - пакеты
    от клиентов, обрабатывает поступающие сообщения.
    Работает в качестве отдельного потока.
    """
    port = PortValidator()

    def __init__(self, listen_address, listen_port, database):
        # Параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера
        self.database = database

        # Сокет, через который будет осуществляться работа
        self.sock = None

        # Список подключённых клиентов.
        self.clients = []

        # Сокеты
        self.listen_sockets = None
        self.error_sockets = None

        # Флаг продолжения работы
        self.running = True

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # Конструктор предка
        super().__init__()

    def run(self):
        """Метод основной цикл потока."""
        # Инициализация Сокета
        self.init_socket()

        # Основной цикл программы сервера
        while self.running:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                SERVER_LOGGER.error(f'Ошибка работы с сокетами: {err.errno}')

            # принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(
                            getting_message(client_with_message), client_with_message)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        SERVER_LOGGER.debug(f'Getting data from client exception.', exc_info=err)
                        self.remove_client(client_with_message)

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
        SERVER_LOGGER.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def init_socket(self):
        """Метод инициализатор сокета."""
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, адрес с которого принимаются подключения: {self.addr}.'
            f' Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.75)

        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen(MAX_CONNECTIONS)

    def process_message(self, message):
        """
        Метод отправки сообщения клиенту.
        """
        if message[TO] in self.names and self.names[message[TO]] in self.listen_sockets:
            try:
                sending_message(self.names[message[TO]], message)
                SERVER_LOGGER.info(
                    f'Отправлено сообщение пользователю {message[TO]} от пользователя {message[FROM]}.')
            except OSError:
                self.remove_client(message[TO])
        elif message[TO] in self.names and self.names[message[TO]] not in self.listen_sockets:
            SERVER_LOGGER.error(
                f'Связь с клиентом {message[TO]} была потеряна. Соединение закрыто, доставка невозможна.')
            self.remove_client(self.names[message[TO]])
        else:
            SERVER_LOGGER.error(
                f'Пользователь {message[TO]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    @login_required
    def process_client_message(self, message, client):
        """Метод отбработчик поступающих сообщений."""
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:
            # Если сообщение о присутствии то вызываем функцию авторизации.
            self.autorize_user(message, client)

        # Если это сообщение, то отправляем его получателю.
        elif ACTION in message and message[ACTION] == MESSAGE \
                and TO in message \
                and TIME in message \
                and FROM in message \
                and MESSAGE in message \
                and self.names[message[FROM]] == client:
            if message[TO] in self.names:
                self.database.process_message(message[FROM], message[TO])
                self.process_message(message)
                try:
                    sending_message(client, {RESPONSE: 200})
                except OSError:
                    self.remove_client(client)
            else:
                try:
                    sending_message(client, {
                        RESPONSE: 400,
                        ERROR: 'Bad request'
                    })
                except OSError:
                    pass
            return

        # если клиент выходит
        elif ACTION in message and message[ACTION] == QUIT \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)

        # если это запрос списка контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS \
                and USER in message and \
                self.names[message[USER]] == client:
            try:
                sending_message(client, {
                    RESPONSE: 202,
                    LIST_INFO: self.database.get_contacts(message[USER])
                })
            except OSError:
                self.remove_client(client)

        # если это добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                sending_message(client, {RESPONSE: 200})
            except OSError:
                self.remove_client(client)

        # если это удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            try:
                sending_message(client, {RESPONSE: 200})
            except OSError:
                self.remove_client(client)

        # если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            try:
                sending_message(client, {
                    RESPONSE: 202,
                    LIST_INFO: [user[0] for user in self.database.users_list()]
                })
            except OSError:
                self.remove_client(client)

        # Если это запрос публичного ключа пользователя
        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST \
                and ACCOUNT_NAME in message:
            response = {RESPONSE: 511, DATA: self.database.get_pubkey(message[ACCOUNT_NAME])}
            # может быть, что ключа ещё нет (пользователь никогда не логинился,
            # тогда шлём 400)
            if response[DATA]:
                try:
                    sending_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                try:
                    sending_message(client, {
                        RESPONSE: 400,
                        ERROR: 'Нет публичного ключа для данного пользователя!'
                    })
                except OSError:
                    self.remove_client(client)

        # Иначе Bad request
        else:
            try:
                sending_message(client, {
                    RESPONSE: 400,
                    ERROR: 'Bad request'
                })
            except OSError:
                self.remove_client(client)

    def autorize_user(self, message, sock):
        """Метод реализующий авторизцию пользователей."""
        # Если имя пользователя уже занято то возвращаем 400
        SERVER_LOGGER.debug(f'Start auth process for {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            try:
                SERVER_LOGGER.debug('Username busy, sending 400')
                sending_message(sock, {
                    RESPONSE: 400,
                    ERROR: 'Bad request'
                })
            except OSError:
                SERVER_LOGGER.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()
        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            try:
                SERVER_LOGGER.debug('Unknown username, sending 400')
                sending_message(sock, {
                    RESPONSE: 400,
                    ERROR: 'Пользователь не зарегистрирован.'
                })
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            SERVER_LOGGER.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = {RESPONSE: 511, DATA: None}
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[DATA] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем
            # серверную версию ключа
            hash = hmac.new(self.database.get_hash(message[USER][ACCOUNT_NAME]), random_str, 'MD5')
            digest = hash.digest()
            SERVER_LOGGER.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                sending_message(sock, message_auth)
                ans = getting_message(sock)
            except OSError as err:
                SERVER_LOGGER.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if RESPONSE in ans and ans[RESPONSE] == 511 \
                    and hmac.compare_digest(digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    sending_message(sock, {RESPONSE: 200})
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                # добавляем пользователя в список активных и если у него изменился открытый ключ
                # сохраняем новый
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                try:
                    sending_message(sock, {
                        RESPONSE: 400,
                        ERROR: 'Пользователь не зарегистрирован.'
                    })
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """Метод реализующий отправки сервисного сообщения 205 клиентам."""
        for client in self.names:
            try:
                sending_message(self.names[client], {RESPONSE: 205})
            except OSError:
                self.remove_client(self.names[client])
