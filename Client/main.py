import asyncio
import Codescord
import DiscordClient
import os


def run() -> None:
    source = Codescord.Source(
        language="py",
        code="print('Hello World!')"
    )

    loop = asyncio.get_event_loop()
    client = Codescord.client.Client(loop)
    result = loop.run_until_complete(
        client.run(source)
    )
    print(result)


def run_as_discord():
    token = os.environ.get("DISCORD_DEV")
    client = DiscordClient.client.Client()
    client.run(token)


if __name__ == '__main__':
    run()
