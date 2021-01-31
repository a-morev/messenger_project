import datetime

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker


# класс для хранения данных для серверной стороны
class ServerRepository:
    """
    Класс - оболочка для работы с базой данных сервера.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход.
    """

    class Users:
        def __init__(self, name, passwd_hash):
            self.id = None
            self.name = name
            self.last_login = datetime.datetime.now()
            self.passwd_hash = passwd_hash
            self.pubkey = None

    # класс для отображения таблицы БД всех активных клиентов
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_date):
            self.id = None
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_date = login_date

    # класс для отображения таблицы БД истории посещения клиента
    class HistoryUser:
        def __init__(self, name, date, ip_address, port):
            self.id = None
            self.name = name
            self.date = date
            self.ip_address = ip_address
            self.port = port

    # класс для отображение таблицы БД контактов пользователей
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # класс для отображения таблицы БД истории действий
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        # движок БД -'sqlite:///server_database.db3'
        self.engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200, connect_args={
            'check_same_thread': False
        })
        # подготовка "запроса" на создание таблицы users внутри каталога MetaData
        self.metadata = MetaData()

        # таблица пользователей
        users_table = Table('users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            Column('passwd_hash', String),
                            Column('pubkey', Text)
                            )
        # таблица активных пользователей
        active_users_table = Table('active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user_id', ForeignKey('users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_date', DateTime)
                                   )
        # таблица активных пользователей
        history_user_table = Table('history_user', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('users.id')),
                                   Column('date', DateTime),
                                   Column('ip_address', String),
                                   Column('port', Integer)
                                   )
        # таблица контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('users.id')),
                         Column('contact', ForeignKey('users.id'))
                         )

        # Создаём таблицу истории пользователей
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )
        self.metadata.create_all(self.engine)

        # связывание таблицы и класса-отображения
        mapper(self.Users, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.HistoryUser, history_user_table)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

        # создание сессии
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # когда устанавливается соединение, очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # основные действия в БД
    def user_login(self, name, ip_address, port, key):
        """
        Запись в базу входа клиента.
        """
        # проверка пользователей на наличие там пользователя с таким именем
        query_result = self.session.query(self.Users).filter_by(name=name)
        # если имя пользователя есть, обновляется время последнего логина
        if query_result.count():
            user = query_result.first()
            user.last_login = datetime.datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        # иначе исключение
        else:
            raise ValueError('Пользователь не зарегистрирован.')

        # Теперь можно создать запись в таблицу активных пользователей
        # создание экземпляра класса self.ActiveUsers, через который передаем данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # Внесение записи в историю входов
        # Создаем экземпляр класса self.LoginHistory, через который передаем данные в таблицу
        history = self.HistoryUser(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # сохранение изменений
        self.session.commit()

    def add_user(self, name, passwd_hash):
        """
        Метод регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.
        """
        user_row = self.Users(name, passwd_hash)
        self.session.add(user_row)
        self.session.commit()
        history_row = self.UsersHistory(user_row.id)
        self.session.add(history_row)
        self.session.commit()

    def remove_user(self, name):
        """
        Метод удаляющий пользователя из базы.
        """
        user = self.session.query(self.Users).filter_by(name=name).first()
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()
        self.session.query(self.HistoryUser).filter_by(name=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(user=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(
            contact=user.id).delete()
        self.session.query(self.UsersHistory).filter_by(user=user.id).delete()
        self.session.query(self.Users).filter_by(name=name).delete()
        self.session.commit()

    def get_hash(self, name):
        """
        Метод получения хэша пароля пользователя.
        """
        user = self.session.query(self.Users).filter_by(name=name).first()
        return user.passwd_hash

    def get_pubkey(self, name):
        """
        Метод получения публичного ключа пользователя.
        """
        user = self.session.query(self.Users).filter_by(name=name).first()
        return user.pubkey

    def check_user(self, name):
        """
        Метод проверяющий существование пользователя.
        """
        if self.session.query(self.Users).filter_by(name=name).count():
            return True
        else:
            return False

    def user_logout(self, name):
        """
        фиксация отключения пользователя
        """
        # получаем запись из таблицы Users пользователя, что покидает нас
        user = self.session.query(self.Users).filter_by(name=name).first()

        # Удаляем запись из таблицы ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()

        self.session.commit()

    # Фиксация передачи сообщения с соответсвующими отметками в БД
    def process_message(self, sender, recipient):
        # ID отправителя и получателя
        sender = self.session.query(self.Users).filter_by(name=sender).first().id
        recipient = self.session.query(self.Users).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    # Добавление контакта для пользователя
    def add_contact(self, user, contact):
        # ID пользователей
        user = self.session.query(self.Users).filter_by(name=user).first()
        contact = self.session.query(self.Users).filter_by(name=contact).first()

        # проверка, что не дубль, и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id,
                                                                           contact=contact.id).count():
            return

        # создание объекта и внесение его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    # Функция удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        # ID пользователей
        user = self.session.query(self.Users).filter_by(name=user).first()
        contact = self.session.query(self.Users).filter_by(name=contact).first()

        # проверка, что контакт может существовать
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    def users_list(self):
        """
        Список всех известных пользователей и время последнего входа.
        """
        query_lst = self.session.query(self.Users.name, self.Users.last_login)
        # Возвращаем список кортежей
        return query_lst.all()

    def active_users_list(self):
        """
        Список активных пользователей.
        """
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            self.Users.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_date
        ).join(self.Users)

        return query.all()

    def user_history(self, name=None):
        """
        История входов по пользователю или всем пользователям.
        """
        # запрос истории входа
        query = self.session.query(self.Users.name,
                                   self.HistoryUser.date,
                                   self.HistoryUser.ip_address,
                                   self.HistoryUser.port
                                   ).join(self.Users)
        # Если было указано имя пользователя, то фильтруем по нему
        if name:
            query = query.filter(self.Users.name == name)
        return query.all()

        # функция возвращает список контактов пользователя.

    def get_contacts(self, name):
        # Запрашивааем указанного пользователя
        user = self.session.query(self.Users).filter_by(name=name).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.Users.name). \
            filter_by(user=user.id). \
            join(self.Users, self.UsersContacts.contact == self.Users.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.Users.name,
            self.Users.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.Users)
        # Возвращаем список кортежей
        return query.all()


# отладка
if __name__ == '__main__':
    test_db = ServerRepository('../server_database.db3')
    # подключение пользователя
    test_db.user_login('user_1', '1.1.1.5', 8000)
    test_db.user_login('user_2', '1.1.1.5', 7000)
    print(test_db.users_list())
    # выводим список кортежей - активных пользователей
    # print(test_db.active_users_list())
    # # отключение пользователя
    # test_db.user_logout('user_1')
    # # выводим список активных пользователей
    # print(test_db.active_users_list())
    # # история входов пользователю user_1
    # test_db.user_history('user_1')
    # выводим список известных пользователей
    test_db.process_message('test1', 'test2')
    print(test_db.message_history())
