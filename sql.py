'''Модуль для работы с базой данных
- sql_launch() - создает таблицы users и statistics
- sql_user(name: str, username: str, user_id: int, increase_counter: bool = True) - добавляет пользователя в базу данных, если его там нет, и обновляет информацию о нем, если он там есть (users)
- sql_insert_to_statistics(name: str, link: str, auto: int = 0) - добавляет данные о запросе в базу данных (statistics)
- sql_insert_to_statistics_by_id(user_id: int, link: str, auto: int = 1) - добавляет данные о запросе в базу данных, но вместо имени использует id, так как имя не всегда доступно (statistics)
- sql_get_last_message(user_id: int) -> str | bool - возвращает последнее сообщение пользователя (users)
- sql_set_last_message(user_id: int, last_message: str) - устанавливает последнее сообщение пользователя (users)'''

import sqlite3
import datetime
from typing import Union


def current_time() -> str:
    '''Возвращает текущее время в формате "HH:MM:SS DD.MM.YYYY UTC+3 (минское время)"'''
    delta = datetime.timedelta(hours=3)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def sql_launch() -> None:
    '''Создает таблицы users и statistics, если их нет'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                name TEXT,
                username TEXT,
                id INTEGER PRIMARY KEY,
                last_message TEXT,
                tracked_message TEXT,
                first_message_time TEXT,
                last_message_time TEXT,
                number_of_messages INT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                name TEXT,
                id INT,
                pdf_link TEXT,
                auto INT,
                time TEXT
            )
        ''')
        connection.commit()

    # connection = sqlite3.connect('bsu_database.db')
    # cursor = connection.cursor()
    # cursor.execute()
    # connection.commit()
    # connection.close()
 


def sql_user(name: str, username: str, user_id: int, increase_counter: bool = True) -> None:
    '''Добавляет пользователя в базу данных, если его там нет, и обновляет информацию о нем, если он там есть'''
    current_time_str = current_time()
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row is None:
            cursor.execute('''
                INSERT INTO users (name, username, id, last_message, tracked_message, first_message_time, last_message_time, number_of_messages)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, username, user_id, 'None', 'None', current_time_str, current_time_str, 1))
        else:
            if name != row[0]:
                cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
            if username != row[1]:
                cursor.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
            if increase_counter:
                cursor.execute("UPDATE users SET last_message_time = ?, number_of_messages = number_of_messages + 1 WHERE id = ?", (current_time_str, user_id))
        connection.commit()


def sql_insert_to_statistics(name: str, link: str, auto: int = 0) -> None:
    '''Вставляет данные об отправителе, ссылке и о том, отправляется ли оно автоматически или нет'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO statistics (name, pdf_link, auto, time)
            VALUES (?, ?, ?, ?)
        ''', (name, link, auto, current_time()))
        connection.commit()


def sql_insert_to_statistics_by_id(user_id: int, link: str, auto: int = 1) -> None:
    '''Вставляет данные об отправителе, ссылке и о том, отправляется ли оно автоматически или нет, но вместо имени использует id, так как имя не всегда доступно'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        name = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO statistics (name, pdf_link, auto, time)
            VALUES (?, ?, ?, ?)
        ''', (name, link, auto, current_time()))
        connection.commit()


def sql_get_last_message(user_id: int) -> str:
    '''Возвращает последнее (сохраненное) сообщение пользователя'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT last_message FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 'None'


def sql_set_last_message(user_id: int, last_message: str) -> None:
    '''Устанавливает последнее сообщение пользователя'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET last_message = ? WHERE id = ?", (last_message, user_id))
        connection.commit()


sql_launch()