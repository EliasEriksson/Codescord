from Codescord.Common.source import Source
from tortoise import Tortoise
from tortoise import run_async
import asyncio
import Codescord
import Discord
import os
import argparse
from pathlib import Path


async def init_tortoise() -> None:
    await Tortoise.init(
        db_url="sqlite://db.db",
        modules={"models": ["Discord.models"]})


async def _create_database() -> None:
    path = Path("db.db")
    if path.exists():
        path.unlink()
    await init_tortoise()
    await Tortoise.generate_schemas()


def create_database() -> None:
    run_async(_create_database())
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(_create_database())


async def _run_client():
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
    loop.run_until_complete(_run_client())


def run_client_with_discord():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_tortoise())
        token = os.environ.get("DISCORD_DEV")
        client = Discord.Client(loop=loop)
        loop.run_until_complete(client.start(token))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(Tortoise.close_connections())


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
        "server": run_server,
        "create-database": create_database
    }

    try:
        if result.mode in modes:
            modes[result.mode]()
        else:
            print(f"mode must be 'client', 'discord' or 'server' not '{result.mode}'")
            quit()
    except KeyboardInterrupt:
        pass
