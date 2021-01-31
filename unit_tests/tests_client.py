"""Тесты программы клиента"""

import os
import sys
import unittest

from base.variables import *
from client import create_presence, process_answer

# для запуска из командной строки
sys.path.append(os.path.join(os.getcwd(), '..'))


class TestClassClient(unittest.TestCase):
    """Класс с тестами программы клиента"""

    def test_smoke_def_create_presence(self):
        """Тест на 'дымок' ф-ии создания сообщения"""
        test_notification = create_presence()
        test_notification[TIME] = 1.0
        self.assertEqual(test_notification, {
            ACTION: PRESENCE,
            TIME: 1.0,
            USER: {ACCOUNT_NAME: 'Guest'}
        })

    def test_response_200(self):
        """Тест на код 200"""
        self.assertEqual(process_answer({RESPONSE: 200}), '200 : OK')

    def test_response_400(self):
        """Тест на код 400"""
        self.assertEqual(process_answer({RESPONSE: 400, ERROR: 'Bad request'}), '400 : Bad request')

    def test_raises_exc(self):
        """Тест на вызов исключения при неправильном ответе, без поля RESPONSE"""
        self.assertRaises(ValueError, process_answer, {ERROR: 'Bad request'})


if __name__ == '__main__':
    unittest.main()
