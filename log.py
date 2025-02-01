import logging
from colorama import Fore, Style, init
from datetime import datetime, timezone


logging.basicConfig(level=20, filename="bsu.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s")

def utc_time():
    return datetime.now(timezone.utc).strftime('%Y.%m.%d %H:%M:%S')

init()

def log(message_green: str, message: str = '', error=False):

    t = utc_time()

    color = Fore.RED if error else Fore.GREEN
    print(t, f'{color}{Style.BRIGHT}{message_green}{Style.RESET_ALL}', message)

    if error:
        logging.error(f'{message_green}: {message}')
    else:
        logging.info(f'{message_green}: {message}')

