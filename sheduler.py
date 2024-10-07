from main import scheduler
from func import current_hour
import asyncio

if 7 <= current_hour() < 22:
    print(f'Scheduler. hour={current_hour()}')
    asyncio.run(scheduler())

