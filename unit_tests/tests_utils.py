"""Тесты общих функций"""

import json
import os
import sys
import unittest

from base.utils import sending_message, getting_message
from base.variables import *

# для запуска из командной строки
sys.path.append(os.path.join(os.getcwd(), '..'))


class TestSocket:
    """
    Тестовый класс для тестирования отправки и получения,
    при создании требует словарь, который будет использоваться
    в тестовых функциях
    """

    def __init__(self, test_dictionary):
        self.test_dictionary = test_dictionary
        self.encoded_message = None
        self.received_message = None

    def recv(self, max_length):
        """
        Получение данных из сокета и кодирование их
        :param max_length:
        :return:
        """
        message_in_json = json.dumps(self.test_dictionary)
        return message_in_json.encode(ENCODING)

    def send(self, message_to_send):
        """
        Тестовая функция отправки, корретно  кодирует сообщение,
        также сохраняет, то что должно быть отправлено в сокет.
        message_to_send - то, что отправляем в сокет
        :param message_to_send:
        :return:
        """
        message_in_json = json.dumps(self.test_dictionary)
        # кодирует сообщение
        self.encoded_message = message_in_json.encode(ENCODING)
        # сохраняем что должно было отправлено в сокет
        self.received_message = message_to_send


class TestClassUtils(unittest.TestCase):
    """Класс для тестирования утилит"""
    test_dictionary_send = {
        ACTION: PRESENCE,
        TIME: 1.0,
        USER: {
            ACCOUNT_NAME: 'test_user'
        }
    }

    test_dict_recv_2xx = {RESPONSE: 200}

    test_dict_recv_4xx = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_sending_message(self):
        """
        Тестируем корректность работы фукции отправки,
        создадим тестовый сокет и проверим корректность отправки словаря
        """
        # экземпляр тестового словаря, хранит собственно тестовый словарь
        test_sock_obj = TestSocket(self.test_dictionary_send)
        # вызов тестируемой функции, результаты будут сохранены в тестовом сокете
        sending_message(test_sock_obj, self.test_dictionary_send)
        # проверка корретности кодирования словаря.
        # сравниваем результат довренного кодирования и результат от тестируемой функции
        self.assertEqual(test_sock_obj.encoded_message, test_sock_obj.received_message)

    def test_getting_message(self):
        """Тест функции приёма сообщения"""
        test_sock_2xx = TestSocket(self.test_dict_recv_2xx)
        test_sock_4xx = TestSocket(self.test_dict_recv_4xx)
        # тест корректной расшифровки корректного словаря
        self.assertEqual(getting_message(test_sock_2xx), self.test_dict_recv_2xx)
        # тест корректной расшифровки ошибочного словаря
        self.assertEqual(getting_message(test_sock_4xx), self.test_dict_recv_4xx)


if __name__ == '__main__':
    unittest.main()
