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
    
        
def create_specialty(title, subplots):
    return {
        'title': title,
        'subplots': subplots,
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 0
    }


def by_specialty_and_course():
    connection = sqlite3.connect('bsu_database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT pdf_link FROM statistics")

    plt.figure(figsize=(12, 7))

    specialties_data = [
    ('Романо-германская филология', [3, 2, 1]),
    ('Славянская филология', [3, 2, 2]),
    ('Восточная филология', [3, 2, 3]),
    ('Русская филология', [3, 2, 4]),
    ('Классическая филология', [3, 2, 5]),
    ('Белорусская филология', [3, 2, 6]),
    ]

    specialty = {key: create_specialty(title, subplots) for key, (title, subplots) in zip(
        ['rom-germ', 'slav', 'vost', 'rus', 'klassiki', 'bel'], specialties_data)}

    """
    'rom-germ': {
        'title': 'Романо-германская филология',
        'subplots': [3, 2, 1],
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 0
    }
    """
    
    links = [i[0] for i in cursor.fetchall()[-10**5:]]


    # .split('_')[-1][:-4]: 3_rom-germ.pdf -> [3, 'rom-germ.pdf'] -> 'rom-germ.pdf', 'rom-germ'
    # .split('/')[-1][0]: .../3_rom-germ.pdf -> ['...', '3_rom-germ.pdf'] -> 3_rom-germ.pdf -> 3
    for spec, curse in zip(links, links):
        if spec.endswith('.pdf'):
            specialty[spec.split('_')[-1][:-4]][curse.split('/')[-1][0]] += 1

    subplot_index = 1
    for spec_data in specialty.values():
        plt.subplot(2, 3, subplot_index)
        plt.title(spec_data['title'])
        plt.bar(x=['1 курс', '2 курс', '3 курс', '4 курс'], height=[spec_data['1'], spec_data['2'], spec_data['3'], spec_data['4']], label=spec_data['title'])
        subplot_index += 1

    plt.tight_layout()

    plt.savefig("by_specialty_and_course.png")
    connection.close()

    return "by_specialty_and_course.png"


sql_launch()
