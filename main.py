import fitz
import requests
import datetime
import os
import hashlib
import json
import asyncio

from urllib3 import disable_warnings
from colorama import init, Fore, Style
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InputMediaPhoto, Message, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.session.aiohttp import AiohttpSession


disable_warnings()  # Сайт БГУ не безопасен ¯\_(ツ)_/¯

if __name__ == '__main__' or '.' not in __name__:
    from sql import sql_user, sql_statistics, sql_get_last_message, sql_set_last_message, sql_get_language, sql_change_language
else:
    from .sql import sql_user, sql_statistics, sql_get_last_message, sql_set_last_message, sql_get_language, sql_change_language


message_text = {
    'start_message': ['Выберете расписание', 'Абярыце расклад']
}


init()
path = os.path.dirname(__file__)
load_dotenv(os.path.join(path, '.env'))
bot_token = os.getenv('BOT_TOKEN')
bot = Bot(bot_token)
dp = Dispatcher()


def parsing_links():
    root_link = 'https://philology.bsu.by'
    raspisanie_link = f'{root_link}/ru/studjentu/raspisanie'

    text = requests.get(raspisanie_link, verify=False).text
    soup = BeautifulSoup(text, "html.parser")

    links = {}

    for a_tag in soup.find_all('a', href=True):
        link = root_link + a_tag['href']
        text = a_tag.get_text(strip=True)

        if 'raspisanie/' in link:  # логично и просто
            links[text] = link

    return links


def translate_to_bel(text: str) -> str:
    try:
        return GoogleTranslator(source='ru', target='be').translate(text)
    except Exception as e:
        return text
    

def parsing_pdf(link):

    text = requests.get(link, verify=False).text
    soup = BeautifulSoup(text, 'html.parser')

    pdf_links = []

    for p_tag in soup.find_all('p'):  # проходимся по специальностям

        strong_tag = p_tag.find('strong')
        if strong_tag:

            specialty = strong_tag.get_text(strip=True).split('(')[0]

            temp_links = {}
            for a_tag in p_tag.find_all('a', href=True):  # по курсам
                pdf_link = a_tag['href']
                text = a_tag.get_text(strip=True)
                temp_links[text] = pdf_link

            if temp_links:
                pdf_links.append({'ru_name': specialty, 'bel_name': translate_to_bel(specialty), 'content': temp_links})

    return pdf_links
    

def parsing():
    result = {}

    links = parsing_links()

    for name, link in links.items():
        pdfs = parsing_pdf(link)

        if pdfs:
            hash_name = hashlib.md5(name.encode('utf-8')).hexdigest()

            result[hash_name] = {
                'ru_name': name,
                'bel_name': translate_to_bel(name),
                'content': pdfs
            }

    path = os.path.join(os.path.dirname(__file__), 'data.json')
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(result, json_file, ensure_ascii=False)
    
    print(f'Расписание было обновленно в {current_time()}. Длина: {len(result)}')

    return result


'''
{
    "d500510e6b9dc0689177a9a1a94b5d67": {
        "ru_name": "Расписание занятий студентов дневного отделения (І семестр) 2024-2025",
        "bel_name": "Расклад заняткаў студэнтаў дзённага аддзялення (І семестр) 2024-2025",
        "content": [
            {
                "ru_name": "Специальность \"Белорусская филология\" ",
                "bel_name": "Спецыяльнасць \"Беларуская філалогія\"",
                "content": {
                    "1 курс": "/files/dnevnoe/raspisanie/1_bel.pdf",
                    ...
                }
            },
            ...
        ],
        ...
    },
    ...
}
'''


def get_data(json_name: str = 'data.json') -> dict:
    path = os.path.join(os.path.dirname(__file__), json_name)

    if not(os.path.exists(path)) or os.path.getsize(path) == 0:
        parsing()

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return data
        


def start_inline_keyboard(language: int = 0):  # TODO: обработка. Проверка на .pdf
    language = 'bel_name' if language else 'ru_name'
    data = get_data()

    inline_keyboard = []

    for callback_data, content in data.items():
        text = content[language]
        inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)



def inline_keyboard_by_hash(hashed_text: str, language: int = 0):
    
    data = get_data().get(hashed_text, None)

    if data is None:
        return False
    else:
        content = data['content']
    
    language = 'bel_name' if language else 'ru_name'
    
    inline_keyboard = []



    for specialty in content:
        text_button = InlineKeyboardButton(text=str(specialty[language]), callback_data='decorative_button')
        inline_keyboard.append([text_button])

        courses = []
        for course_name, course_value in specialty['content'].items():
            if course_name: # на всяких случай
                courses.append(InlineKeyboardButton(text=course_name.strip(','), callback_data=course_value))

        inline_keyboard.append(courses)

    inline_keyboard.append([InlineKeyboardButton(text='Назад', callback_data='back')])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def current_time():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


@dp.message(CommandStart())  # Вызывает меню выбора
async def command_start_handler(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_get_language(message.from_user.id)
    await message.answer(text=message_text['start_message'][language], reply_markup=start_inline_keyboard(language))


@dp.callback_query(F.data == 'decorative_button')  # реакция, при нажатии на декоративные кнопки
async def inline_text(callback: CallbackQuery):
    sql_user(name=callback.from_user.full_name, username=str(callback.from_user.username), user_id=callback.from_user.id, chat_id=callback.chat_instance, increase_counter=False)
    language = sql_get_language(callback.from_user.id)
    text = ['Это исключительно декоративная кнопка', 'Гэта выключна дэкаратыўная кнопка'][language]
    await callback.answer(text=text)


@dp.callback_query(F.data == 'back')   # воссоздает то же меню, что и /start
async def inline_back_handler(callback: CallbackQuery):
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, callback.chat_instance, False)
    language = sql_get_language(callback.from_user.id)
    await callback.message.edit_text(text=message_text['start_message'][language], reply_markup=start_inline_keyboard(language))
    await callback.answer()


@dp.message(Command('language'))  # Обработчик команды /language
async def command_language(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_change_language(message.from_user.id)
    text = ['Язык был изменен', 'Мова была зменена'][language]
    await message.answer(text=text)




def downdload_pdf(link: str) -> str | bool:
    
    try:
        if not link.startswith('https:/'):
            root_link = 'https://philology.bsu.by/'
            link = root_link + link


        response = requests.get(link, verify=False)

        file_name = '_'.join(link.split('/')[-3:])  # https://philology.bsu.by/files/dnevnoe/raspisanie/4_rom-germ.pdf >>> dnevnoe_raspisanie_4_rom-germ.pdf

        with open(file_name, 'wb') as file:
            file.write(response.content)

        return file_name
    
    except Exception as e:
        print(e, link)
        return False


def pdf_to_png(pdf_path: str) -> list[str]:
    file_name = pdf_path[:-4]
    doc = fitz.open(pdf_path)
    photos = []
    count = len(doc)
    n = 2  # качество страниц
        
    for i in range(count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(n, n))
        temp_file_name = f"{file_name}_{i}.png"
        pix.save(temp_file_name)
        photos.append(temp_file_name)

    doc.close()

    return photos



@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery):
    data = callback.data
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, callback.chat_instance, True)
    language = sql_get_language(callback.from_user.id)
    
    if data.endswith('.pdf'):
        sql_set_last_message(callback.from_user.id, data)

        file_name = downdload_pdf(data)
        if file_name:
            images = pdf_to_png(file_name)
            photo_name = file_name[:-4]

            inline_update = InlineKeyboardButton(text=['Обновить', 'Аднавіць'][language], callback_data=data)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_back]])

            n = len(images) if len(images) <= 10 else 10
            files = []
            for i in range(n):
                files.append(InputMediaPhoto(media=FSInputFile(f"{photo_name}_{i}.png")))  # caption=caption if i == 0 else None


            await bot.send_media_group(callback.from_user.id, media=files)
            text = ['Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание',
                    'Націсніце на кнопку або адпраўце любое паведамленне, каб абнавіць расклад'][language]
            await bot.send_message(callback.from_user.id, text=text, reply_markup=inline_keyboard)

            os.remove(file_name)
            for i in range(len(images)):
                os.remove(f'{photo_name}_{i}.png')

        else:
            text = ['Ошибка 404. Страница не найдена', 'Памылка 404. Старонка не знойдзена'][language]
            await bot.send_message(callback.from_user.id, text)

        sql_statistics(name=callback.from_user.full_name, link=data, auto=0)


    else:
        inline_keyboard = inline_keyboard_by_hash(data, language)

        if inline_keyboard:
            language_str = 'bel_name' if language else 'ru_name'
            schedule_type = get_data()[data][language_str]
            text = schedule_type + ('. ' if not schedule_type.endswith('.') else '') + ['Выберете специальность и курс', 'Абярыце спецыяльнасць і курс'][language]
            try:
                await callback.message.edit_text(text=text, reply_markup=inline_keyboard)
            except:
                await callback.answer(['Ошибка. Если вы не можете получитить доступ к чему-то важному, то свяжитесь с администратором.', 'Памылка. Калі вы не можаце атрымаць доступ да чагосьці важнага, то звяжыцеся з адміністратарам.'][language])
        else:
            text = ['Ошибка при поиске расписания. Отправьте команду /start и попробуйте еще раз. Если не поможет, то обратитись к администратору', 'Памылка пры пошуку раскладу. Адпраўце каманду /start і паспрабуйце яшчэ раз. Калі не дапаможа, звернецеся да адміністратара'][language]
            await callback.answer(text=text)

        

    await callback.answer()


@dp.message()
async def main_handler(message: types.Message) -> None:
    user_id = message.from_user.id
    sql_user(message.from_user.full_name, str(message.from_user.username), user_id, message.chat.id)
    link = sql_get_last_message(user_id)
    language = sql_get_language(user_id)

    if link == 'None':
        await message.answer(['Ваше сохраненное расписание не обнаружено. Скорее всего, админ сбросил базу данных. Используйте команду /start и заново выберите расписание',
                              'Ваш захаваны расклад не выяўлены. Хутчэй за ўсё, адмін скінуў базу дадзеных. Выкарыстоўвайце каманду /start і зноўку абярыце расклад'][language])
    else:
        file_name = downdload_pdf(link)
        if file_name:
            images = pdf_to_png(file_name)
            photo_name = file_name[:-4]

            inline_update = InlineKeyboardButton(text=['Обновить', 'Аднавіць'][language], callback_data=link)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_back]])

            n = len(images) if len(images) <= 10 else 10
            files = []
            for i in range(n):
                files.append(InputMediaPhoto(media=FSInputFile(f"{photo_name}_{i}.png")))  # caption=caption if i == 0 else None


            await bot.send_media_group(message.from_user.id, media=files)
            text = ['Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание',
                    'Націсніце на кнопку або адпраўце любое паведамленне, каб абнавіць расклад'][language]
            await bot.send_message(message.from_user.id, text=text, reply_markup=inline_keyboard)

            os.remove(file_name)
            for i in range(len(images)):
                os.remove(f'{photo_name}_{i}.png')

        else:
            text = ['Ошибка 404. Страница не найдена', 'Памылка 404. Старонка не знойдзена'][language]
            await bot.send_message(message.from_user.id, text)

    sql_statistics(name=message.from_user.full_name, link=link, auto=0)


async def run_polling():
    await dp.start_polling(bot, skip_updates=True)


async def periodic_parsing(): # Запуск парсинга раз в 24 часа
    while True:
        parsing()
        await asyncio.sleep(24*60*60)


async def main():
    await asyncio.gather(
        run_polling(),
        periodic_parsing()
    )


if __name__ == '__main__':
    asyncio.run(main())