import asyncio
from Client.client import Client
from DiscordClient.client import Client as DiscordClient
import os


def run() -> None:
    loop = asyncio.get_event_loop()
    client = Client(loop)
    loop.run_until_complete(client.run("""print("hello world!")"""))


def run_as_discord():
    token = os.environ.get("DISCORD_DEV")
    client = DiscordClient()
    client.run(token)


if __name__ == '__main__':
    run_as_discord()
