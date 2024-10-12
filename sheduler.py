from main import scheduler
from func import current_hour
import asyncio

if current_hour() % 7 == 0 and current_hour() != 0:
    print(f'Scheduler. hour={current_hour()}')
    asyncio.run(scheduler())

