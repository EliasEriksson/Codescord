from Codescord.Common.source import Source
import asyncio
import Codescord
import Discord
import os
import argparse


async def runner():
    py1 = Source(
        language="py",
        code="from time import sleep\nsleep(3)\nprint('py1')"
    )

    py2 = Source(
        language="py",
        code="from time import sleep\nsleep(2)\nprint('py2')"
    )

    py3 = Source(
        language="py",
        code="from time import sleep\nsleep(1)\nprint('py3')"
    )

    scripts = [
        py1, py2, py3
    ]

    loop = asyncio.get_event_loop()
    client = Codescord.Client(loop)

    coroutines = [
        asyncio.create_task(
            client.process(script)
        )
        for script in scripts
    ]

    results = [
        await future for future in coroutines
    ]

    print(results)


def run_client() -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner())


def run_client_with_discord():
    token = os.environ.get("DISCORD_DEV")
    client = Discord.Client()
    client.run(token)


def run_server():
    loop = asyncio.get_event_loop()
    server = Codescord.Server(loop=loop)
    loop.run_until_complete(server.run())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str, default="server", help="'client', 'discord' or 'server'")
    result = parser.parse_args()
    modes = {
        "client": run_client,
        "discord": run_client_with_discord,
        "server": run_server
    }

    try:
        if result.mode in modes:
            modes[result.mode]()
        else:
            print(f"mode must be 'client', 'discord' or 'server' not '{result.mode}'")
    except KeyboardInterrupt:
        pass
