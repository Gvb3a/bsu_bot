import os
import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InputMediaPhoto, Message, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup


from sql import sql_insert_to_statistics, sql_user, sql_get_last_message, sql_set_last_message, sql_insert_to_statistics_by_id
from parsing_and_schedule import get_bsu_links, remove_user_id_from_all_schedules, remove_user_id_from_schedule, download_pdf, pdf_to_png, add_or_update_schedule_link, check_schedule_link_hash, gets_link_ids_from_schedule_link
from log import log

path = os.path.dirname(__file__)
load_dotenv(os.path.join(path, '.env'))
bot_token = str(os.getenv('BOT_TOKEN'))
bot = Bot(bot_token)
dp = Dispatcher()


def minsk_time():
    delta = datetime.timedelta(hours=3)
    current_time = datetime.datetime.now(datetime.timezone.utc) + delta
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def start_inline_keyboard():
    '''Create start inline keyboard'''
    data = get_bsu_links()
    inline_keyboard = []

    for callback_data, content in data.items():
        name = content['name']
        inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def inline_keyboard_by_hash(hashed_text: str):
    data = get_bsu_links().get(hashed_text, None)

    if data is None:
        return False
    else:
        content = data['content']
    
    inline_keyboard = []

    for specialty in content:
        decorative_button = InlineKeyboardButton(text=str(specialty['course_name']), callback_data='decorative_button')
        inline_keyboard.append([decorative_button])

        courses = []
        for course_number, course_value in specialty['content'].items():
            if course_number:
                courses.append(InlineKeyboardButton(text=course_number.strip(','), callback_data=course_value))

        inline_keyboard.append(courses)

    inline_keyboard.append([InlineKeyboardButton(text='Назад', callback_data='back')])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(text="Выберите расписание. После выбора можно настроить автоматическое обновление", reply_markup=start_inline_keyboard())
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=message.from_user.id, increase_counter=False)
    log(message_green='start command', message=f'User: {message.from_user.full_name}, ID: {message.from_user.id}')


@dp.callback_query(F.data == 'decorative_button')
async def inline_text(callback: CallbackQuery):
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, False)
    text = 'Это исключительно декоративная кнопка'
    await callback.answer(text=text)


@dp.callback_query(F.data == 'back')
async def inline_back_handler(callback: CallbackQuery):
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, False)
    await callback.message.edit_text(text="Выберите расписание. После выбора можно настроить автоматическое обновление", reply_markup=start_inline_keyboard())
    await callback.answer()


@dp.message(Command('cancel_auto_update'))
async def command_cancel_auto_update(message: Message) -> None:
    user_id = message.from_user.id
    remove_user_id_from_all_schedules(user_id)
    sql_user(name=message.from_user.full_name, username=str(message.from_user.username), user_id=user_id, increase_counter=False)
    text = 'Все автоматические обновления отменены'
    await message.answer(text=text)
    log('cancel_auto_update', f'User {message.from_user.full_name} canceled all auto update')


@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery):
    data = str(callback.data)
    sql_user(callback.from_user.full_name, str(callback.from_user.username), callback.from_user.id, True)
    
    if data.endswith('.pdf'):
        sql_set_last_message(callback.from_user.id, data)
        file_name = download_pdf(data)
        if file_name:
            file_name = str(file_name)  # for fix red underline
            images = pdf_to_png(file_name)

            inline_update = InlineKeyboardButton(text='Обновить', callback_data=data)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_on_auto = InlineKeyboardButton(text='Включить автообновление', callback_data=f'{data}-auto_up')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_on_auto], [inline_back]])

            files = []
            for i in images[:9]:
                files.append(InputMediaPhoto(media=FSInputFile(i)))

            await bot.send_media_group(callback.from_user.id, media=files)
            text = 'Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание. Включите автообновление, чтобы расписание присылалось при изменении.'
            await bot.send_message(callback.from_user.id, text=text, reply_markup=inline_keyboard)

            try:
                os.remove(file_name)
                for image_file in images:
                    os.remove(image_file)
            except Exception as e:
                log(f'callback_data: Error deleting {file_name}', f'{e}', error=True)

        else:
            await bot.send_message(callback.from_user.id, 'Ошибка 404. Страница не найдена.')

        sql_insert_to_statistics(name=callback.from_user.full_name, link=data, auto=0)
        log('callback_data defult', f'link: {data}, user: {callback.from_user.full_name}')

    
    elif data.endswith('-auto_up'):
        link = data[:-8]
        add_or_update_schedule_link(link, callback.from_user.id)
        text = 'Автоматическое обновление включено. Бот будет проверять расписание и, если оно изменится, отправит его вам. Для отмены отправьте /cancel_auto_update'
        await bot.send_message(callback.from_user.id, text)
        log('callback_data auto_up', f'link: {link}, user: {callback.from_user.full_name}')


    elif data.endswith('-auto_down'):
        remove_user_id_from_schedule(data[:-10], callback.from_user.id)
        text = 'Автоматическое обновление выключено'
        await bot.send_message(callback.from_user.id, text)
        log('callback_data auto_down', f'link: {data[:-10]}, user: {callback.from_user.full_name}')

    else:
        inline_keyboard = inline_keyboard_by_hash(data)

        if inline_keyboard:
            schedule_type = get_bsu_links()[data]['name']
            text = f"{schedule_type.strip('.')}. Выберете специальность и курс"
            try:
                await callback.message.edit_text(text=text, reply_markup=inline_keyboard)
            except Exception as e:
                log('callback_data edit_text error', f'Error: {e}', error=True)
                await callback.answer('Ошибка. Попробуйте еще раз. Если это не поможет и вы не можете получить доступ к чему-то важному, то свяжитесь с администратором.')
        else:
            text = 'Ошибка при поиске расписания. Отправьте команду /start и попробуйте еще раз. Если не поможет, то обратитесь к администратору.'
            await callback.answer(text=text)
            log('callback_data error', f'data: {data}, user: {callback.from_user.full_name}', error=True)

    await callback.answer()



@dp.message()
async def main_handler(message: types.Message) -> None:
    user_id = message.from_user.id
    sql_user(message.from_user.full_name, str(message.from_user.username), user_id, True)
    link = sql_get_last_message(user_id)

    if link == 'None':
        await message.answer('Ваше сохраненное расписание не обнаружено. Скорее всего, админ сбросил базу данных. Используйте команду /start и выберите расписание.')
    else:
        file_name = download_pdf(link)
        if file_name:
            file_name = str(file_name)
            images = pdf_to_png(file_name)

            inline_update = InlineKeyboardButton(text='Обновить', callback_data=link)
            inline_back = InlineKeyboardButton(text='Меню', callback_data='back')
            inline_on_auto = InlineKeyboardButton(text='Включить автообновление', callback_data=f'{link}-auto_up')
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_on_auto], [inline_back]])

            files = []
            for i in images[:9]:
                files.append(InputMediaPhoto(media=FSInputFile(i)))

            await bot.send_media_group(message.from_user.id, media=files)
            text = 'Нажмите на кнопку или отправьте любое сообщение, что бы обновить расписание. Включите автообновление, чтобы расписание присылалось при изменении.'
            await bot.send_message(message.from_user.id, text=text, reply_markup=inline_keyboard)
            
            try:
                os.remove(file_name)
                for file_name in images:
                    os.remove(file_name)
            except:
                print(f'Error with deleting {file_name}')

        else:
            text = 'Ошибка 404. Страница не найдена'
            await bot.send_message(message.from_user.id, text)
    
    log('message', f'link: {link}, user: {message.from_user.full_name}')
    sql_insert_to_statistics(name=message.from_user.full_name, link=link, auto=0)


async def scheduler():
    log('Sheduler started')
    links = check_schedule_link_hash()
    log('Sheduler sends start', f'links={links}')
    for link in links:
        ids = gets_link_ids_from_schedule_link(link)
        file_name = download_pdf(link)
        log('Sheduler send', f'link={link} ids={ids}' + ('' if file_name else ' file_name=False'))
        if file_name:
            file_name = str(file_name)
            images = pdf_to_png(file_name)
            files = []
            for i in images[:9]:
                files.append(InputMediaPhoto(media=FSInputFile(i)))
            for id in ids:
                try:
                    await bot.send_media_group(id, media=files)
                    sql_insert_to_statistics_by_id(user_id=id, link=link, auto=1)
                except Exception as e:
                    log('Sheduler sending error', f'link: {link}, id: {id}, Error: {e}')
            try:
                os.remove(file_name)
                for i in images:
                    os.remove(i)
            except Exception as e:
                log(f'Sheduler error deleting {file_name}', f'{e}', error=True)
        else:
            log('Sheduler error', f'link: {link}, file_name: {file_name}', error=True)
    log('Sheduler ended')


if __name__ == '__main__':
    log('START')
    dp.run_polling(bot, skip_updates=True)
