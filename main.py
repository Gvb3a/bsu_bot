import fitz
import requests
import datetime
import os

from urllib3 import disable_warnings
from colorama import init, Fore, Style
from dotenv import load_dotenv

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
    'start_message': ['Выберете расписание', 'Абярыце расклад'],
    'help_message': ''
}
init()
path = os.path.dirname(__file__)
load_dotenv(os.path.join(path, '.env'))
bot_token = os.getenv('BOT_TOKEN')
bot = Bot(bot_token)
dp = Dispatcher()


def start_keyboard(l):  # функция для start inline-keyboard (в зависимости от языка)
    # l - язык пользователя. 0 - русский, 1 - белорусский
    inline_start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=['Расписание занятий студентов дневного отделения (І семестр) 2024-2025',
                                    'Расклад заняткаў студэнтаў дзённага аддзялення (І семестр) 2024-2025'][l], callback_data='inline_raspisanie')],
        [InlineKeyboardButton(text=['Расписание занятий (дистанционное обучение) студентов дневного отделения (i семестр) 2024-2025',
                                    'Расклад заняткаў (дыстанцыйнае навучанне) студэнтаў дзённага аддзялення (i семестр) 2024-2025'][l], callback_data='inline_USRDO')]
    ])
    return inline_start_keyboard


def inline_button(path, speciality):  # генерация однотипных inline кнопок
    inline_list = []
    for i in range(4):
        inline_list.append(InlineKeyboardButton(text=f'{i+1} курс', callback_data=f'{path}/{i+1}_{speciality}'))
    return inline_list


def inline_text_button(text, l):
    return [InlineKeyboardButton(text=text[l], callback_data='text')]

def create_main_inline_keyboard(l, path):
    # расписания хранятся по следующему пути:
    # https://philology.bsu.by/files/dnevnoe/{тип расписания}/{курс}_{специальность}.pdf
    # на классической филологии только один набор
    inline_classical_philology_4 = [InlineKeyboardButton(text='4 курс', callback_data=f'{path}/4_klassiki')]

    inline_back = [InlineKeyboardButton(text='Назад', callback_data='back')]
    inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
    inline_text_button(['Белорусская филология', 'Беларуская філалогія'], l),
    inline_button(path, 'bel'),
    inline_text_button(['Русская филология', 'Руская філалогія'], l),
    inline_button(path, 'rus'),
    inline_text_button(['Славянская филология', 'Славянская філалогія'], l),
    inline_button(path, 'slav'),
    inline_text_button(['Классическая  филология', 'Класічная  філалогія'], l),
    inline_classical_philology_4,
    inline_text_button(['Романо-германская филология', 'Рамана-германская філалогія'], l),
    inline_button(path, 'rom-germ'),
    inline_text_button(['Восточная филология', 'Усходняя філалогія'], l),
    inline_button(path, 'vost'),
    inline_back
    ])
    return inline_keyboard


main_dict = {  # будет использоваться для 'расшифрования' TODO
    'raspisanie': ['Расписание занятий студентов дневного отделения ',
                   'Расклад заняткаў студэнтаў дзённага аддзялення '],
    'USRDO': ['Расписание занятий (дистанционное обучение) студентов дневного отделения ',
              'Расклад заняткаў (дыстанцыйнае навучанне) студэнтаў дзённага аддзялення '],
    'zachet': ['Расписание зачетов студентов дневного отделения ',
               'Расклад залікаў студэнтаў дзённага аддзялення '],
    'sesia': ['Расписание консультаций и экзаменов студентов дневного отделения ',
              'Расклад кансультацый і экзаменаў студэнтаў дзённага аддзялення ']

}
sup_dict = {
    'bel': ['белорусская филология', 'беларуская філалогія'],
    'rus': ['русская филология', 'руская філалогія'],
    'slav': ['славянская филология', 'славянская філалогія'],
    'klassiki': ['классическая  филология', 'класічная  філалогія'],
    'rom-germ': ['романо-германская филология', 'рамана-германская філалогія'],
    'vost': ['восточная филология', 'усходняя філалогія']
}
start_list = ['Выберите тип расписания. После окончательного выбора бот запомнит Ваше расписание и будет присылать его '
              'при отправке любого сообщения.', 'Абярыце тып раскладу. Пасля канчатковага выбару бот запомніць Ваш '
              'расклад і будзе дасылаць яго пры адпраўцы любога паведамлення']


def current_time():
    delta = datetime.timedelta(hours=3, minutes=0)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


@dp.message(CommandStart())  # Вызывает меню выбора
async def command_start_handler(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_get_language(message.from_user.id)
    await message.answer(text=message_text['start_message'][language], reply_markup=start_keyboard(language))


@dp.callback_query(F.data == 'text')  # реакция, при нажатии на декоративные кнопки
async def inline_text(callback: CallbackQuery):
    sql_user(name=callback.from_user.full_name, username=str(callback.from_user.username), user_id=callback.from_user.id, chat_id=callback.chat_instance, increase_counter=False)
    language = sql_get_language(callback.from_user.id)
    text = ['Это исключительно декоративная кнопка', 'Гэта выключна дэкаратыўная кнопка'][language]
    await callback.answer(text=text)


@dp.callback_query(F.data == 'back')   # воссоздает то же меню, что и /start
async def inline_back_handler(callback: CallbackQuery):
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, callback.chat_instance, False)
    language = sql_get_language(callback.from_user.id)
    await callback.message.edit_text(text=message_text['start_message'][language], reply_markup=start_keyboard(language))
    await callback.answer()


@dp.message(Command('language'))  # Обработчик команды /language
async def command_language(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_change_language(message.from_user.id)
    text = ['Язык был изменен', 'Мова была зменена'][language]
    await message.answer(text=text)




def downdload_pdf(link: str) -> str | bool:

    if not link.startswith('https:/'):
        root_link = 'https://philology.bsu.by/'
        link = root_link + link

    try:
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
    
    if data.startswith('inline'):
        data = data[7:]

        await callback.message.edit_text(text=main_dict[data][language]+['Выберете специальность', 'Абярыце спецыяльнасць'][language],
                                            reply_markup=create_main_inline_keyboard(language, data))

    else:

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




if __name__ == '__main__':
    print(f'The bot launches at {current_time()}')
    dp.run_polling(bot, skip_updates=True)