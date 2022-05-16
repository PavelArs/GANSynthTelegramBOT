import sys
sys.path.append('C:\\Users\\Pro10\\Documents\\GitHub\\GANSynthTelegramBOT\\GANSynth\\config')

import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
import ffmpeg
from pydub import AudioSegment

from config import settings
from GANSynth import *
from random import randint
# from aiogram.types import BufferedInputFile

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=settings.API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Stage(StatesGroup):
    start = State()
    duration = State()
    genre = State()
    generation = State()

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


def audio_config(duration, genre):
    if genre == "Drum'n'Bass":
        config = {
            'duration': duration,
            'lowest_key_note': 35,
            'highest_key_note': 50,
            'BPM': randint(170, 200)
        }
    elif genre == 'Trance':
        config = {
            'duration': duration,
            'lowest_key_note': 65,
            'highest_key_note': 80,
            'BPM': randint(120, 150)
        }
    elif genre == 'Techno':
        config = {
            'duration': duration,
            'lowest_key_note': 35,
            'highest_key_note': 50,
            'BPM': randint(135, 150)
        }
    elif genre == 'House':
        config = {
            'duration': duration,
            'lowest_key_note': 45,
            'highest_key_note': 70,
            'BPM': randint(118, 132)
        }
    elif genre == 'Electro':
        config = {
            'duration': duration,
            'lowest_key_note': 35,
            'highest_key_note': 50,
            'BPM': randint(125, 140)
        }
    else:
        config = {
            'duration': duration,
            'lowest_key_note': 35,
            'highest_key_note': 80,
            'BPM': randint(120, 200)
        }
    return config

# duration = 10
# genre = 'Random genre'

@dp.message_handler(commands='help', state='*')
@dp.message_handler(Text(equals="Help"), state=Stage.start)
async def help_message(message: types.Message):
    await message.reply(
        "This bot generates audio files from scratch. There are plenty of genres in which audio can be generated.\nTo generate an audio use /generate command.\nTo stop bot use /cancel command.\nTo start bot use /start command.")


@dp.message_handler(commands='start', state='*')
async def main_menu(message: types.Message):
    await Stage.start.set()
    await message.reply("Hi!\nI'm GANSynthBOT!\nDo you want to generate some audios?")
    await message.answer("Choose your options", reply_markup=start_menu)


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply('Bot shutted down. To start bot type /start command in chat.')


@dp.message_handler(commands='generate', state='*')
@dp.message_handler(Text(equals="Generate"), state=Stage.start)
@dp.message_handler(Text(equals="Yes"), state=Stage.generation)
async def audio_duration(message: types.Message):
    await Stage.duration.set()
    await message.answer("Please write a duration of your audio (in seconds).")


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


@dp.message_handler(state=Stage.genre)
async def generation_audio(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    data = await state.get_data()
    while data.get('genre') not in genres:
        await message.reply('Please choose one genre from the list below!')
        return

    config = audio_config(data.get('duration'), data.get('genre'))
    await message.answer("Please wait for your audio to be generated.\nIt may take a while.")
    au = generate_aud(lowest_key_note=config.get('lowest_key_note'), highest_key_note=config.get('highest_key_note'),
                      BPM=config.get('BPM'), composition_length=config.get('duration'), disc_rate=32000,
                      title=f'Generated {data.get("genre")}')
    await message.answer("Audio file is generated. One moment...")
    await message.answer(f"Your generated audio file in {data.get('genre')} genre.")
    await message.answer_document(open(f'C:\\Users\\Pro10\\genaud\\Generated {data.get("genre")}.wav', 'rb'))
    os.remove(f'C:\\Users\\Pro10\\genaud\\Generated {data.get("genre")}.wav')
    await message.answer("Generate one more?", reply_markup=end_menu)
    await Stage.generation.set()


#     await Stage.final()


@dp.message_handler(Text(equals="No"), state=Stage.generation)
async def thanks(message: types.Message):
    await message.answer(
        "Thank you for using the bot. Hope you enjoy your generated audio! :)\nSimply type /generate in chat if you want to generate one more audio.")
    await state.finish()