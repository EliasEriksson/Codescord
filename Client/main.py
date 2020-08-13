import asyncio
import Codescord
import DiscordClient
import os


async def runner():
    py1 = Codescord.Source(
        language="py",
        code="from time import sleep\nsleep(3)\nprint('py1')"
    )

    py2 = Codescord.Source(
        language="py",
        code="from time import sleep\nsleep(2)\nprint('py2')"
    )

    py3 = Codescord.Source(
        language="py",
        code="from time import sleep\nsleep(1)\nprint('py3')"
    )

    scripts = [
        py1, py2, py3
    ]

    loop = asyncio.get_event_loop()
    client = Codescord.client.Client(loop)

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


def run() -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner())


def run_as_discord():
    token = os.environ.get("DISCORD_DEV")
    client = DiscordClient.client.Client()
    client.run(token)


if __name__ == '__main__':
    run()
