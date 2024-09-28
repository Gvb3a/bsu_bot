import sqlite3
import datetime


def current_time():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def sql_launch():
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
        name TEXT,
        username TEXT,
        id INTEGER PRIMARY KEY,
        chat_id INT,
        last_message TEXT,
        saved_message TEXT,
        language INT
        )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
        name TEXT,
        pdf_link TEXT,
        auto INT,
        time TEXT
        )
        ''')
    
    
    connection.commit()
    connection.close()


def sql_user(name: str, username: str, user_id: int, chat_id: int):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    
    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    
    if row is None:  # создаем пользователя если его не было
        cursor.execute(f"INSERT INTO user(name, username, id, chat_id, last_message, tracked_message, language) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (name, username, user_id, chat_id, 'None', 'None', 0))
    else:
        # проверяем, соответствует ли имеющиеся данные с настоящими (например пользователь поменял имя)
        if name != row[0]:
            cursor.execute(f"UPDATE user SET name = ? WHERE id = ?", (name, user_id))

        if username != row[1]:
            cursor.execute(f"UPDATE user SET username = ? WHERE id = ?", (username, user_id))

        if chat_id != row[3]:
            cursor.execute(f"UPDATE user SET chat_id = ? WHERE id = ?", (chat_id, user_id))


    connection.commit()
    connection.close()


def sql_stat(name: str, link: str, auto: int = 0) -> None:
    'Вставляет данные об отправителе, ссылке и о том, отправляется ли оно автоматически или нет'
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"INSERT INTO statistics(name, pdf_link, auto, time) VALUES (?, ?, ?)", (name, link, auto, current_time()))

    connection.commit()
    connection.close()


def sql_get_last_message(user_id):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute(f"INSERT INTO user(id, saved_message, last_message, language) VALUES (?, ?, ?, ?)", (user_id, 'None', 'None', 0))
        last_message = 'None'

    else:
        last_message = row[4]

    connection.commit()
    connection.close()

    return last_message


def sql_set_last_message(user_id, last_message):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute(f"INSERT INTO user(id, saved_message, last_message, language) VALUES (?, ?, ?, ?)", (user_id, 'None', last_message, 0))

    else:
        cursor.execute(f"INSERT INTO user(last_message) VALUES (?)", (last_message))

    connection.commit()
    connection.close()
 


def sql_get_language(user_id):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()

    if row is None:
        cursor.execute(f"INSERT INTO user(id, saved_message, last_message, language) VALUES (?, ?, ?, ?)", (user_id, 'None', 'None', 0))
        l = 0
    else:
        l = row[3]

    connection.commit()
    connection.close()
    return l


def sql_change_language(user_id):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    language = sql_get_language(user_id)
    new_language = 0 if language else 1
    cursor.execute(f"UPDATE user SET ? = ? WHERE id = ?", ('language', new_language, user_id))

    connection.commit()
    connection.close()
    return new_language


sql_launch()