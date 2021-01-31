Base package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт decorators.py
--------------------

.. automodule:: base.decorators
    :members:

Скрипт descriptors.py
---------------------

.. autoclass:: base.descriptors.PortValidator
    :members:

Скрипт metaclasses.py
-----------------------

.. autoclass:: base.metaclasses.ServerVerifier
   :members:
   
.. autoclass:: base.metaclasses.ClientVerifier
   :members:
   
Скрипт utils.py
---------------

base.utils. **getting_message** (sock_obj)


    Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
    декодирует полученное сообщение и проверяет что получен словарь.

base.utils. **sending_message** (sock_obj, message)


    Функция отправки словарей через сокет. Кодирует словарь в формат JSON и отправляет через сокет.

Скрипт variables.py
-------------------

Содержит разные глобальные переменные проекта.