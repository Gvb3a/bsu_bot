import logging
from colorama import Fore, Style, init
from datetime import datetime, timedelta, timezone
from pathlib import Path

init()

log_file = Path("bsu.log")
logging.basicConfig(level=logging.INFO, filename=log_file, filemode="a", format="%(asctime)s %(levelname)s %(message)s")

def minsk_time() -> str:
    """Returns the current time in the format 'HH:MM:SS DD.MM.YYYY UTC+3 (Minsk time)'"""
    current_time = datetime.now(timezone.utc) + timedelta(hours=3)
    return current_time.strftime("%H:%M:%S %d.%m.%Y")


def log(message_green: str, message: str = '', error: bool = False) -> None:
    '''Logs the message with the current time and the message type (error or info)'''
    color = Fore.RED if error else Fore.GREEN
    print(minsk_time(), f'{color}{Style.BRIGHT}{message_green}{Style.RESET_ALL}', message)

    if error:
        logging.error(f'{message_green}: {message}')
    else:
        logging.info(f'{message_green}: {message}')

