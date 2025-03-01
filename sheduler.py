from main import scheduler
import asyncio
import datetime

def hour_in_minsk():
    time = datetime.datetime.now() + datetime.timedelta(hours=3)
    return time.hour

if hour_in_minsk() in [7, 10, 14, 17, 21]:
    print(f'Scheduler. hour={hour_in_minsk()}')
    asyncio.run(scheduler())
