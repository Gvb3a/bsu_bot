import os
import asyncio

from urllib3 import disable_warnings
from colorama import init, Fore, Style
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InputMediaPhoto, Message, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup


if __name__ == '__main__' or '.' not in __name__:
    from sql import sql_user, sql_statistics, sql_get_last_message, sql_set_last_message, sql_get_language, sql_change_language, all_plot
    from func import parsing, get_data, download_pdf, pdf_to_png, get_shedule_id, remove_id_by_shedule, remove_id_form_all_shedule, add_schedule_link_or_id, cheak_link_hash, current_time, sql_statistics_by_id
else:
    from .sql import sql_user, sql_statistics, sql_get_last_message, sql_set_last_message, sql_get_language, sql_change_language, all_plot
    from .func import parsing, get_data, download_pdf, pdf_to_png, get_shedule_id, remove_id_by_shedule, remove_id_form_all_shedule, add_schedule_link_or_id, cheak_link_hash, current_time, sql_statistics_by_id


message_text = {
    'start_message': ['Выберите расписание. После выбора можно настроить автоматическое обновление', 'Абярыце расклад. Пасля выбару можна настроіць аўтаматычнае абнаўленне']
}


init()
path = os.path.dirname(__file__)
load_dotenv(os.path.join(path, '.env'))
bot_token = os.getenv('BOT_TOKEN')
bot = Bot(bot_token)
dp = Dispatcher()



def start_inline_keyboard(language: int = 0):
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


@dp.message(CommandStart())  # Вызывает меню выбора
async def command_start_handler(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_get_language(message.from_user.id)
    await message.answer(text=message_text['start_message'][language], reply_markup=start_inline_keyboard(language))
    print(f'User {message.from_user.full_name} send start command')


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


@dp.message(Command('language'))  # Обработчик команды /language. Меняет язык
async def command_language(message: Message) -> None:
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, chat_id=message.chat.id)
    language = sql_change_language(message.from_user.id)
    text = ['Язык был изменен', 'Мова была зменена'][language]
    await message.answer(text=text)
    print(f'User {message.from_user.full_name} changed language')


@dp.message(Command('cancel_auto_update'))  # Отменить авто обновление
async def command_cancel_auto_update(message: Message) -> None:
    user_id = message.from_user.id
    remove_id_form_all_shedule(message.from_user.id)
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=user_id, chat_id=message.chat.id)
    language = sql_get_language(user_id)
    text = ['Все автоматические обновления отменены', 'Усе аўтаматычныя абнаўленні адменены'][language]
    await message.answer(text=text)
    print(f'User {message.from_user.full_name} canceled all auto update')


@dp.message(Command('stat')) 
async def command_statistic(message: Message) -> None:
    images = all_plot()
    files = [InputMediaPhoto(media=FSInputFile(file_name)) for file_name in images]
    await bot.send_media_group(message.from_user.id, media=files)
    print(f'User {message.from_user.full_name} send \statistic')
    for file_name in images:
        os.remove(file_name)


@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery):
    data = callback.data
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, callback.chat_instance, True)
    language = sql_get_language(callback.from_user.id)
    
    if data.endswith('.pdf'):
        sql_set_last_message(callback.from_user.id, data)

        file_name = download_pdf(data)
        if file_name:
            images = pdf_to_png(file_name)
            photo_name = file_name[:-4]

            inline_update = InlineKeyboardButton(text=['Обновить', 'Аднавіць'][language], callback_data=data)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_on_auto = InlineKeyboardButton(text=['Включить автообновление', 'Уключыць аўтаабнаўленне'][language], callback_data=f'{data}-auto_up')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_on_auto], [inline_back]])

            n = len(images) if len(images) <= 10 else 10
            files = []
            for i in range(n):
                files.append(InputMediaPhoto(media=FSInputFile(f"{photo_name}_{i}.png")))  # caption=caption if i == 0 else None


            await bot.send_media_group(callback.from_user.id, media=files)
            text = ['Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание',
                    'Націсніце на кнопку або адпраўце любое паведамленне, каб абнавіць расклад'][language]
            await bot.send_message(callback.from_user.id, text=text, reply_markup=inline_keyboard)

            try:
                os.remove(file_name)
            except:
                print(f'Error deleting {file_name}. Callback')
            for i in range(len(images)):
                os.remove(f'{photo_name}_{i}.png')

        else:
            text = ['Ошибка 404. Страница не найдена', 'Памылка 404. Старонка не знойдзена'][language]
            await bot.send_message(callback.from_user.id, text)

        sql_statistics(name=callback.from_user.full_name, link=data, auto=0)

    
    elif data.endswith('-auto_up'):

        link = data[:-8]

        add_schedule_link_or_id(link, callback.from_user.id)

        text = ['Автоматическое обновление включено. Бот будет проверять расписание и, если оно изменится, отправит его вам. Для отмены отправьте /cancel_auto_update', 'Аўтаматычнае абнаўленне ўключана. Бот будзе правяраць расклад і, калі ён зменіцца, адправіць яго вам. Для адмены адпраўце /cancel_auto_update'][language]
        await bot.send_message(callback.from_user.id, text)


    elif data.endswith('-auto_down'):
        remove_id_by_shedule(data[:-9], callback.from_user.id)

        text = ['Автоматическое обновление выключено', 'Аўтаматычнае абнаўленне выключана'][language]
        await bot.send_message(callback.from_user.id, text)

        
    else:
        inline_keyboard = inline_keyboard_by_hash(data, language)

        if inline_keyboard:
            language_str = 'bel_name' if language else 'ru_name'
            schedule_type = get_data()[data][language_str]
            text = schedule_type + ('. ' if not schedule_type.endswith('.') else '') + ['Выберете специальность и курс', 'Абярыце спецыяльнасць і курс'][language]
            try:
                await callback.message.edit_text(text=text, reply_markup=inline_keyboard)
            except:
                await callback.answer(['Ошибка. Попробуйте еще раз. Если это не поможет и вы не можете получитить доступ к чему-то важному, то свяжитесь с администратором.', 'Памылка. Паспрабуйце яшчэ раз. Калі гэта не дапаможа і вы не можаце атрымаць доступ да чагосьці важнага, то звяжыцеся з адміністратарам.'][language])
        else:
            text = ['Ошибка при поиске расписания. Отправьте команду /start и попробуйте еще раз. Если не поможет, то обратитись к администратору.', 'Памылка пры пошуку раскладу. Адпраўце каманду /start і паспрабуйце яшчэ раз. Калі не дапаможа, звернецеся да адміністратара.'][language]
            await callback.answer(text=text)

        
    print(f'User {callback.from_user.full_name} clicked {callback.data}')
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
        file_name = download_pdf(link)
        if file_name:
            images = pdf_to_png(file_name)
            photo_name = file_name[:-4]

            inline_update = InlineKeyboardButton(text=['Обновить', 'Аднавіць'][language], callback_data=link)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_on_auto = InlineKeyboardButton(text=['Включить автообновление', 'Уключыць аўтаабнаўленне'][language], callback_data=f'{link}-auto_up')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_on_auto], [inline_back]])

            n = len(images) if len(images) <= 10 else 10
            files = []
            for i in range(n):
                files.append(InputMediaPhoto(media=FSInputFile(f"{photo_name}_{i}.png")))  # caption=caption if i == 0 else None


            await bot.send_media_group(message.from_user.id, media=files)
            text = ['Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание',
                    'Націсніце на кнопку або адпраўце любое паведамленне, каб абнавіць расклад'][language]
            await bot.send_message(message.from_user.id, text=text, reply_markup=inline_keyboard)
            
            try:
                os.remove(file_name)
            except:
                print(f'Error deleting {file_name}. message')
            for i in range(len(images)):
                os.remove(f'{photo_name}_{i}.png')

        else:
            text = ['Ошибка 404. Страница не найдена', 'Памылка 404. Старонка не знойдзена'][language]
            await bot.send_message(message.from_user.id, text)
    
    print(f'User {message.from_user.full_name} send message ({link})')
    sql_statistics(name=message.from_user.full_name, link=link, auto=0)


async def run_polling():
    await dp.start_polling(bot, skip_updates=True)


async def scheduler():
    links = cheak_link_hash()
    print(f'Sheduler. time={current_time()} link={links}')
    for link in links:
        ids = get_shedule_id(link)
        file_name = download_pdf(link)
        print(f'link={link} ids={ids}' + ('' if file_name else ' file_name=False'))
        if file_name:
            images = pdf_to_png(file_name)
            photo_name = file_name[:-4]
            n = len(images) if len(images) <= 10 else 10
            files = []
            for i in range(n):
                files.append(InputMediaPhoto(media=FSInputFile(f"{photo_name}_{i}.png")))
            for id in ids:
                try:
                    await bot.send_media_group(id, media=files)
                    sql_statistics_by_id(id=id, link=link, auto=1)
                except Exception as e:
                    print(f'Error sending {link} to {id}. Error: {e}')
        
            os.remove(file_name)


if __name__ == '__main__':
    print('Start')
    dp.run_polling(bot, skip_updates=True)
