import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
import mysql.connector
# from mysql.connector import errorcode
from datetime import datetime

from config import settings
from GANSynth import *



# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=settings.API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


cnx = mysql.connector.connect(user=settings.user, password=settings.password,
                              host=settings.host,
                              database=settings.database,
                              auth_plugin=settings.auth_plugin)


class Stage(StatesGroup):
    start = State()
    duration = State()
    genre = State()
    generation = State()

# cursor = cnx.cursor(buffered=True)
# cursor.execute(f"select name from {settings.schema}.chats")
# genres = cursor.fetchall()
genres = ["Trance", "Techno", "Electro", "Drum'n'Bass", "House", "Random"]

start_menu = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
buttons = ["Generate", "Help"]
start_menu.add(*buttons)

genres_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
buttons = genres
genres_menu.add(*buttons)

end_menu = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
buttons = ["Yes", "No"]
end_menu.add(*buttons)


@dp.message_handler(commands='help', state='*')
@dp.message_handler(Text(equals="Help"), state=Stage.start)
async def help_message(message: types.Message):
    await message.reply(
        "This bot generates audio files from scratch. There are plenty of genres in which audio can be generated.\nTo generate an audio use /generate command.\nTo stop bot use /cancel command.\nTo start bot use /start command.")
    cursor = cnx.cursor()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()

@dp.message_handler(commands='start', state='*')
async def main_menu(message: types.Message):
    await Stage.start.set()
    cursor = cnx.cursor(buffered=True)
    query = (f"SELECT * FROM {settings.schema}.chats WHERE user_id = {message.from_user.id}")
    cursor.execute(query)
    if not cursor.rowcount:
        file = open('sql_scripts/new_user_insert.sql', 'r')
        sql = file.read()
        file.close()
        cursor.execute(sql, (0, datetime.now(), datetime.now(), 0,  message.from_user.id))
        cnx.commit()
        await message.reply("Hi!\nI'm GANSynthBOT!\nDo you want to generate some audios?")
    else:
        await message.reply("Welcome back!\nDo you want to generate some audios?")
    await message.answer("Choose your options", reply_markup=start_menu)
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()


@dp.message_handler(state='*', commands=['cancel', 'stop'])
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply('Bot shutted down. To start bot type /start command in chat.')
    cursor = cnx.cursor()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s, bot_stpd = 1 where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()


@dp.message_handler(commands='generate', state='*')
@dp.message_handler(Text(equals="Generate"), state=Stage.start)
@dp.message_handler(Text(equals="Yes"), state=Stage.generation)
async def audio_duration(message: types.Message):
    await Stage.duration.set()
    await message.answer("Please write a duration of your audio (in seconds).")
    cursor = cnx.cursor()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()


@dp.message_handler(state=Stage.duration)
async def genre_choice(message: types.Message, state: FSMContext):
    try:
        await state.update_data(duration=int(message.text))
    except Exception as ex:
        await message.reply("Please write an integer!")
        return
    data = await state.get_data()
    while data.get('duration') > 60:
        await message.reply("This audio will be generating for years. Please write an integer not bigger than 60!")
        return
    while data.get('duration') <= 0:
        await message.reply("Seems like your audio's duration too little to generate. Please write a positive integer!")
        return

    await message.answer("Choose one from listed genres to generate audio.", reply_markup=genres_menu)
    await Stage.genre.set()
    cursor = cnx.cursor()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()


@dp.message_handler(state=Stage.genre)
async def generation_audio(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    cursor = cnx.cursor(buffered=True, dictionary=True)
    query = (f"SELECT name FROM {settings.schema}.genres "
             "WHERE _deleted = 0")
    cursor.execute(query)
    correct_genre = False
    data = await state.get_data()
    for row in cursor:
        if row.get('name') == data.get('genre'):
            correct_genre = True
            break
    if not correct_genre:
        await message.reply('Please choose one genre from the list below!')
        cursor.close()
        return
    query = (f"SELECT * FROM {settings.schema}.genres "
             "WHERE name = %(name)s")
    cursor.execute(query, {'name': data.get('genre')})
    g = cursor.fetchall()
    await message.answer("Please wait for your audio to be generated.\nIt may take a while.")
    for i in g:
        generate_aud(lowest_key_note=i.get('lk_pitch'), highest_key_note=i.get('hk_pitch'),
                     BPM=i.get('bpm'), composition_length=data.get('duration'), disc_rate=32000,
                     title=f'Generated {data.get("genre")}')
    # cursor.close()
    await message.answer("Audio file is generated. One moment...")
    await message.answer(f"Your generated audio file in {data.get('genre')} genre.")
    await message.answer_document(open(f'C:\\Users\\Pro10\\genaud\\Generated {data.get("genre")}.wav', 'rb'))
    os.remove(f'C:\\Users\\Pro10\\genaud\\Generated {data.get("genre")}.wav')
    # await message.answer("Please rate 1 to 5 generated audio", reply_markup=['1', '2', '3', '4', '5', 'Skip'])
    cursor.execute(f"SELECT MAX(gen_num) from {settings.schema}.gen_au "
                   f"WHERE chat_id=(SELECT id FROM {settings.schema}.chats WHERE user_id={message.from_user.id})")
    n = cursor.fetchall()
    if n[0].get("MAX(gen_num)") is None:
        n = 1
    else:
        n = n[0].get("MAX(gen_num)") + 1
    # query = (f"INSERT INTO {settings.schema}.gen_au (id, dur, chat_id, genre_id, gen_num, aud_link, usr_mark, created_at) "
    #          f"VALUES (0, %s, %s, %s, %s, NULL, NULL, %s);")
    file = open('sql_scripts/gen_au_insert.sql', 'r')
    sql = file.read()
    file.close()
    cursor.execute(sql, (0, data.get('duration'), message.from_user.id, g[0].get('id'), n, datetime.now()))
    await message.answer("Generate one more?", reply_markup=end_menu)
    await Stage.generation.set()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()

#     await Stage.final()


@dp.message_handler(Text(equals="No"), state=Stage.generation)
async def thanks(message: types.Message):
    await message.answer(
        "Thank you for using the bot. Hope you enjoy your generated audio! :)\nSimply type /generate in chat if you want to generate one more audio.")
    await state.finish()
    cursor = cnx.cursor()
    cursor.execute((f"update {settings.schema}.chats set lst_msg = %s where user_id = {message.from_user.id};"), (datetime.now(),))
    cursor.close()
    cnx.commit()