import sqlite3
import matplotlib.pyplot as plt
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
        'last_message': 'None',
        'tracked_message': 'None',
        'language': 0,
        'first_message_time': str(current_time()),
        'last_message_time': str(current_time()),
        'number_of_messages': 1
    }
    
    if row is None:  # создаем пользователя если его не было
        cursor.execute(f"INSERT INTO user(name, username, id, last_message, tracked_message, language, first_message_time, last_message_time, number_of_messages) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       tuple(standart_value.values()))
    else:
        # проверяем, соответствует ли имеющиеся данные с настоящими (например пользователь поменял имя)
        if name != row[0]:
            cursor.execute(f"UPDATE user SET name = ? WHERE id = ?", (name, user_id))

        if username != row[1]:
            cursor.execute(f"UPDATE user SET username = ? WHERE id = ?", (username, user_id))

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


def sql_statistics_by_id(id: int, link: str, auto: int = 1) -> None:
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT name FROM user WHERE id = {id}")
    name = cursor.fetchone()[0]

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
        last_message = row[3]

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
        l = row[5]

    connection.commit()
    connection.close()
    return l


def sql_change_language(user_id):
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()

    language = sql_get_language(user_id)
    new_language = 0 if language else 1
    cursor.execute(f"UPDATE user SET language = ? WHERE id = ?", (new_language, user_id))

    connection.commit()
    connection.close()
    return new_language



def requests_by_hours() -> str:
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT time FROM statistics")

    hours = [int(time[0].split(':')[0]) for time in cursor.fetchall()][-10**5:]

    dict_of_time = {i: hours.count(i) for i in range(24)}

    labels = list(dict_of_time.keys())
    values = list(dict_of_time.values())

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.set_title("Запросы по часам")
    ax.set_xlabel("Часы")
    ax.set_ylabel("Запросы")

    bars = ax.bar(labels, values)

    for bar in bars:
        bar_value = bar.get_height()
        bar_x = bar.get_x() + bar.get_width() / 2
        bar_y = bar_value

        value_label = f"{int(bar_value)}"

        ax.annotate(
            value_label,
            xy=(bar_x, bar_y),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
        )

    plt.savefig("requests_by_hours.png")
    connection.close()

    return "requests_by_hours.png"
    
        
def create_specialty(title):
    return {
        'title': title,
        '1': [0, 0],  # [без авто, с авто]
        '2': [0, 0],
        '3': [0, 0],
        '4': [0, 0]
    }


def by_specialty_and_course():
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT pdf_link, auto FROM statistics")

    plt.figure(figsize=(12, 7))

    specialties = ['Романо-германская филология', 'Славянская филология', 'Восточная филология', 
                   'Русская филология', 'Классическая филология', 'Белорусская филология']

    specialty = {key: create_specialty(title) for key, title in zip(
        ['rom-germ', 'slav', 'vost', 'rus', 'klassiki', 'bel'], specialties)}

    # Получаем данные и ограничиваем выборку
    rows = cursor.fetchall()[-10**5:]
    links = [row[0] for row in rows]
    autos = [row[1] for row in rows]

    # Обрабатываем данные
    for spec, is_auto in zip(links, autos):
        if spec.endswith('.pdf'):
            spec_name = spec.split('_')[-1][:-4]
            curse_name = spec.split('/')[-1][0]

            if is_auto:
                specialty[spec_name][curse_name][1] += 1
            else:
                specialty[spec_name][curse_name][0] += 1

    # Создаем графики
    subplot_index = 1
    for spec_data in specialty.values():
        plt.subplot(2, 3, subplot_index)
        sm = sum(sum(value) for key, value in spec_data.items() if key != 'title')
        plt.title(f"{spec_data['title']} ({sm})")

        y_auto = [spec_data['1'][1], spec_data['2'][1], spec_data['3'][1], spec_data['4'][1]]
        y_no_auto = [spec_data['1'][0], spec_data['2'][0], spec_data['3'][0], spec_data['4'][0]]

        x = ['1 курс', '2 курс', '3 курс', '4 курс']

        plt.bar(x, y_auto, label='Авто', color='#ff7f0e')
        plt.bar(x, y_no_auto, bottom=y_auto, label='Не авто', color='#1f77b4')
        
        plt.legend()
        subplot_index += 1

    plt.tight_layout()

    plt.savefig("by_specialty_and_course.png")
    connection.close()

    return "by_specialty_and_course.png"


sql_launch()