"""Тесты программы сервера"""

import sys
import unittest
import os
from base.variables import *
from server import process_client_message

# для запуска из командной строки
sys.path.append(os.path.join(os.getcwd(), '..'))


class TestServer(unittest.TestCase):
    """
    В сервере тестируется только функция process_client_message
    """
    valid_response = {RESPONSE: 200}
    invalid_response = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_smoke_check(self):
        """Тест на 'дымок'"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.valid_response)

    def test_no_action(self):
        """Ошибка - нет типа сообщения"""
        self.assertEqual(process_client_message(
            {TIME: '1.0', USER: {ACCOUNT_NAME: 'Guest'}}), self.invalid_response)

    def test_no_time(self):
        """Ошибка - нет времени сообщения"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.invalid_response)

    def test_no_user(self):
        """Ошибка - не указан пользователь"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '1.0'}), self.invalid_response)

    def test_invalid_action(self):
        """Ошибка - неизвестный тип сообщения"""
        self.assertEqual(process_client_message(
            {ACTION: 'request', TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}), self.invalid_response)

    def test_unknown_user(self):
        """Ошибка - не Guest"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'User'}}), self.invalid_response)


if __name__ == '__main__':
    unittest.main()
