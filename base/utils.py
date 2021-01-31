"""Общие утилиты проекта"""
import json

from base.variables import *


def getting_message(sock_obj):
    """
    Утилита приёма и декодирования сообщения.
    Принимает байты преобразует в словарь, если принято что-то другое возвращает ошибку значения
    :param sock_obj:
    :return:
    """
    encoded_response = sock_obj.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        response_in_json = encoded_response.decode(ENCODING)
        response = json.loads(response_in_json)
        if isinstance(response, dict):
            return response
        return ValueError
    return ValueError


def sending_message(sock_obj, message):
    """
    Утилита кодирования и отправки сообщения.
    Принимает словарь преобразует в байты
    :param sock_obj:
    :param message:
    :return:
    """
    message_in_json = json.dumps(message)
    encoded_message = message_in_json.encode(ENCODING)
    sock_obj.send(encoded_message)
