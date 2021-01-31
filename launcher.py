"""Лаунчер"""

import subprocess


def main():
    PROCESS_QUEUE = []

    while True:
        ACTION = input('Выберите действие: q - выход, '
                       's - запустить сервер, '
                       'c - запустить клиенты, '
                       'x - закрыть все окна: ')

        if ACTION == 'q':
            break
        elif ACTION == 's':
            # Запуск серверной части
            PROCESS_QUEUE.append(subprocess.Popen('python server.py',
                                                  creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif ACTION == 'c':
            print('Первый запуск может быть достаточно долгим из-за генерации ключей!')
            number_clients = int(input('Число тестовых клиентов: '))
            # Запуск клиентской части
            for i in range(number_clients):
                PROCESS_QUEUE.append(subprocess.Popen(f'python client.py -n user{i + 1} -p 123456',
                                                      creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif ACTION == 'x':
            while PROCESS_QUEUE:
                PROCESS_QUEUE.pop().kill()


if __name__ == '__main__':
    main()
