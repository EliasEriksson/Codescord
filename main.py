from tortoise import Tortoise
from tortoise import run_async
import asyncio
import Codescord
import Discord
import os
import argparse
from pathlib import Path
import subprocess


def process(stdin: str) -> str:
    """
    wrapper for subprocess.

    :param stdin: stdin
    :return: stdout
    """
    p = subprocess.run(stdin.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = p.stdout.decode("utf-8") if p.returncode == 0 else p.stderr.decode("utf-8")
    return stdout


def close_containers() -> None:
    """
    final resort to make sure all the docker containers are closed after some major exception.

    most of the time this is going to be keyboard interrupt.

    :return: None
    """
    stdout = process("sudo docker ps -a")

    for line in stdout.split("\n"):
        if "codescord" in line:
            name = line.split()[-1]
            process(f"sudo docker stop {name}")
            process(f"sudo docker rm {name}")


async def init_tortoise() -> None:
    """
    initializes tortoises connection to the database.

    :return: None
    """
    await Tortoise.init(
        db_url="sqlite://db.db",
        modules={"models": ["Discord.models"]})


async def _create_database() -> None:
    """
    asynchronous version of create_database.

    :return: None
    """
    path = Path("db.db")
    if path.exists():
        path.unlink()
    await init_tortoise()
    await Tortoise.generate_schemas()


def create_database() -> None:
    """
    sets up and creates the database for the Discord.Client.

    :return: None
    """
    run_async(_create_database())


def run_client() -> None:
    """
    starts the Discord.Client.

    :return: None
    """
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_tortoise())
        token = os.environ.get("DISCORD_DEV")
        client = Discord.Client(loop=loop)
        loop.run_until_complete(client.start(token))
    finally:
        loop.run_until_complete(Tortoise.close_connections())


def run_server() -> None:
    """
    starts the Codescord.Server.

    :return: None
    """
    loop = asyncio.get_event_loop()
    server = Codescord.Server(loop=loop)
    loop.run_until_complete(server.run())


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    parser = argparse.ArgumentParser()
    modes = {
        "client": run_client,
        "server": run_server,
        "create-database": create_database
    }
    mode_help = ", ".join(f"'{mode}'" for mode in modes.keys())
    parser.add_argument("mode", type=str, default="client", help=mode_help)
    result = parser.parse_args()

    try:
        if result.mode in modes:
            modes[result.mode]()
        else:
            print("mode must be ", end="")
            print(", ".join(f"'{mode}'" for mode in modes.keys()), end="")
            print(f", not '{result.mode}'")
            quit()
    except KeyboardInterrupt:
        pass
    finally:
        print("closing containers...")
        close_containers()
        print("closed containers.")
