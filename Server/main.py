import asyncio
from Server.server import Server


def run():
    loop = asyncio.get_event_loop()
    server = Server(loop=loop)
    loop.run_until_complete(server.run())


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        pass
