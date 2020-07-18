import asyncio
from Client.client import Client


def run() -> None:
    loop = asyncio.get_event_loop()
    client = Client(loop)
    loop.run_until_complete(client.run())


if __name__ == '__main__':
    run()
