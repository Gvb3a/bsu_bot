# TODO: переделать полностью
import sqlite3
import matplotlib.pyplot as plt
from typing import List


def requests_by_hours(n: int = 10**5):
    '''Создает график запросов по часам'''
    with sqlite3.connect('bsu_database.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT time, auto FROM statistics")

        # Получаем последние n записей
        data = cursor.fetchall()[-n:]
        
        # Разделяем данные на авто и ручные запросы по часам
        hours_auto = [int(time[0].split(':')[0]) for time in data if time[1] == 1]
        hours_manual = [int(time[0].split(':')[0]) for time in data if time[1] == 0]

        # Считаем количество для каждого часа
        dict_of_time_auto = {i: hours_auto.count(i) for i in range(24)}
        dict_of_time_manual = {i: hours_manual.count(i) for i in range(24)}

        labels = list(range(24))
        values_auto = list(dict_of_time_auto.values())
        values_manual = list(dict_of_time_manual.values())

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.set_title("Запросы по часам")
        ax.set_xlabel("Часы")
        ax.set_ylabel("Запросы")

        # Создаем stacked bar chart с правильными цветами
        # Ручные запросы - синие (C0 - стандартный синий цвет matplotlib)
        bars_manual = ax.bar(labels, values_manual, label='Ручные запросы', color='tab:blue')
        # Автоматические запросы - оранжевые (C1 - стандартный оранжевый цвет matplotlib) 
        bars_auto = ax.bar(labels, values_auto, bottom=values_manual, label='Автоматические запросы', color='tab:orange')

        # Добавляем подписи значений для автоматических запросов (сверху)
        for i, (bar_auto, bar_manual) in enumerate(zip(bars_auto, bars_manual)):
            auto_value = bar_auto.get_height()
            if auto_value > 0:  # Только если есть автоматические запросы
                bar_x = bar_auto.get_x() + bar_auto.get_width() / 2
                bar_y = bar_manual.get_height() + auto_value  # Позиция сверху

                ax.annotate(
                    f"{int(auto_value)}",
                    xy=(bar_x, bar_y),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color='C1',  # Оранжевый цвет для автоматических
                    fontweight='bold'
                )

        # Добавляем подписи значений для ручных запросов (внутри столбца)
        for bar_manual in bars_manual:
            manual_value = bar_manual.get_height()
            if manual_value > 0:  # Только если есть ручные запросы
                bar_x = bar_manual.get_x() + bar_manual.get_width() / 2
                bar_y = manual_value / 2  # Позиция посередине столбца

                ax.annotate(
                    f"{int(manual_value)}",
                    xy=(bar_x, bar_y),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color='white',
                    fontweight='bold'
                )

        # Добавляем легенду
        ax.legend()

        # Настраиваем ось X
        ax.set_xticks(range(0, 24, 1))
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.show()

        # Выводим статистику в консоль
        total_auto = sum(values_auto)
        total_manual = sum(values_manual)
        print(f"Всего автоматических запросов: {total_auto}")
        print(f"Всего ручных запросов: {total_manual}")
        print(f"Общее количество запросов: {total_auto + total_manual}")

requests_by_hours()


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
