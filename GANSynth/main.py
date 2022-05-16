import sys
import nest_asyncio
# sys.path.append('C:\\Users\\Pro10\\Documents\\GitHub\\GANsynth-pytorch')
from TelegramBOT import *

nest_asyncio.apply()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)