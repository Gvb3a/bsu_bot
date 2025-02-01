from main import scheduler
from func import current_hour
import asyncio

if current_hour() in [7, 10, 14, 17, 21]:
    print(f'Scheduler. hour={current_hour()}')
    asyncio.run(scheduler())
