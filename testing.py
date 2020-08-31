import asyncio
from functools import partial


m = []


async def work(future: asyncio.Future, i):
    print("started to work")
    await asyncio.sleep(0.5)
    print("done working")
    future.set_result(i)


async def main(loop):
    for i in range(4):
        future = loop.create_future()
        m.append((future, partial(work, future, i)))
    await m[2][0]
    # await asyncio.sleep(5)





if __name__ == '__main__':
    lp = asyncio.get_event_loop()
    lp.run_until_complete(main(lp))
