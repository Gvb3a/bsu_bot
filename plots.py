# TODO: переделать полностью
import sqlite3
import matplotlib.pyplot as plt
from typing import List


def requests_by_hours() -> str:
    '''Создает график запросов по часам и сохраняет его в файл'''
    with sqlite3.connect('bsu_database.db') as connection:
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

    return "requests_by_hours.png"


def create_specialty(title: str) -> dict:
    '''Создает словарь для специальности'''
    return {
        'title': title,
        '1': [0, 0],  # [без авто, с авто]
        '2': [0, 0],
        '3': [0, 0],
        '4': [0, 0]
    }


def by_specialty_and_course() -> str:
    '''Создает график запросов по специальностям и курсам и сохраняет его в файл'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT pdf_link, auto FROM statistics")

        plt.figure(figsize=(12, 7))

        specialties = ['Романо-германская филология', 'Славянская филология', 'Восточная филология',
                       'Русская филология', 'Классическая филология', 'Белорусская филология']

        specialty = {key: create_specialty(title) for key, title in zip(
            ['rom-germ', 'slav', 'vost', 'rus', 'klassiki', 'bel'], specialties)}

        rows = cursor.fetchall()[-10**5:]
        links = [row[0] for row in rows]
        autos = [row[1] for row in rows]

        for spec, is_auto in zip(links, autos):
            if spec.endswith('.pdf'):
                spec_name = spec.split('_')[-1][:-4]
                curse_name = spec.split('/')[-1][0]
                try:
                    if is_auto:
                        specialty[spec_name][curse_name][1] += 1
                    else:
                        specialty[spec_name][curse_name][0] += 1
                except KeyError:
                    pass

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

    return "by_specialty_and_course.png"


def last_30_days() -> str:
    '''Создает график запросов за последние 30 дней и сохраняет его в файл'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT time FROM statistics")

        time = [time[0].split()[1] for time in cursor.fetchall()[-10**5:]]

        sorted_dates = sorted(list(set(time))[-30:])
        dict_of_time = {date.split('.')[0]: time.count(date) for date in sorted_dates}

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_title("Запросы за последние 30 дней")
        bars = ax.bar(dict_of_time.keys(), dict_of_time.values())

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

        plt.savefig('last_30_days.png')

    return 'last_30_days.png'


def all_plot() -> List[str]:
    '''Создает все графики и возвращает список их файлов'''
    return [last_30_days(), by_specialty_and_course(), requests_by_hours()]
