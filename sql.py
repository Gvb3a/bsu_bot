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
        tracked_message TEXT,
        language INT,
        first_message_time TEXT,
        last_message_time TEXT,
        number_of_messages INT        
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


def sql_user(name: str, username: str, user_id: int, chat_id: int, increase_counter: bool = True):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    
    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    standart_value = {
        'name': name,
        'username': username,
        'id': user_id,
        'chat_id': chat_id,
        'last_message': 'None',
        'tracked_message': 'None',
        'language': 0,
        'first_message_time': str(current_time()),
        'last_message_time': str(current_time()),
        'number_of_messages': 1
    }
    
    if row is None:  # создаем пользователя если его не было
        cursor.execute(f"INSERT INTO user(name, username, id, chat_id, last_message, tracked_message, language, first_message_time, last_message_time, number_of_messages) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       tuple(standart_value.values()))
    else:
        # проверяем, соответствует ли имеющиеся данные с настоящими (например пользователь поменял имя)
        if name != row[0]:
            cursor.execute(f"UPDATE user SET name = ? WHERE id = ?", (name, user_id))

        if username != row[1]:
            cursor.execute(f"UPDATE user SET username = ? WHERE id = ?", (username, user_id))

        if chat_id != row[3]:
            cursor.execute(f"UPDATE user SET chat_id = ? WHERE id = ?", (chat_id, user_id))

        if increase_counter:  # TODO: перенести в sql_statistic
            cursor.execute(f"UPDATE user SET last_message_time = ? WHERE id = ?", (current_time(), user_id))
            cursor.execute(f"UPDATE user SET number_of_messages = number_of_messages + 1 WHERE id = {user_id}")


    connection.commit()
    connection.close()


def sql_statistics(name: str, link: str, auto: int = 0) -> None:
    'Вставляет данные об отправителе, ссылке и о том, отправляется ли оно автоматически или нет'
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"INSERT INTO statistics(name, pdf_link, auto, time) VALUES (?, ?, ?, ?)", (name, link, auto, current_time()))

    connection.commit()
    connection.close()


def sql_get_last_message(user_id: int) -> str | bool:
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    
    if row is None:
        last_message = False
    else:
        last_message = row[4]

    connection.close()

    return last_message


def sql_set_last_message(user_id: int, last_message: str):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    
    cursor.execute(f"UPDATE user SET last_message = ? WHERE id = ?", (last_message, user_id))

    connection.commit()
    connection.close()
 


def sql_get_language(user_id: int) -> int:
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()

    if row is None:
        l = 0
    else:
        l = row[6]

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

if __name__ == '__main__':
    sql_user(name='Boris', username = 'gvb3a', user_id=123, chat_id=321)