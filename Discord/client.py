from typing import *
import discord
import Codescord
import re
from uuid import uuid4
from .models import ResponseMessages
import asyncio
from .errors import Errors
from tortoise.exceptions import DoesNotExist


async def edit(stdout: str, message: discord.Message, description: str = None) -> None:
    description = description if description else ""
    await message.edit(content=f"{description}\n```{stdout}```")


async def send(stdout: str, channel: discord.TextChannel, description: str = None) -> discord.Message:
    description = description if description else ""
    return await channel.send(f"{description}\n```{stdout}```")


async def subprocess(stdin: str) -> Tuple[bool, str]:
    process = await asyncio.create_subprocess_exec(
        *stdin.split(" "), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if not stdout:
        print(f"failed with '{stdin}'")
        return False, stderr.decode("utf-8")
    print(f"succeeded with '{stdin}'")
    return True, stdout.decode("utf-8")


class Message:
    def __init__(self, message_id: int, author: discord.User, content: str, guild: discord.Guild, channel: discord.TextChannel) -> None:
        self.id = message_id
        self.author = author
        self.content = content
        self.guild = guild
        self.channel = channel


class Client(discord.Client):
    def __init__(self, loop=None, initial_port: int = 6090) -> None:
        loop = loop if not loop else asyncio.get_event_loop()
        super(Client, self).__init__(loop=loop)
        self.codescord_client = Codescord.Client(self.loop)
        self.initial_port = initial_port
        self.code_pattern = re.compile(r"```([\w+]+)\n([^=`]+)```", re.DOTALL)
        self.used_ports = set()
        self.used_ids = set()

    @staticmethod
    async def start_container(port: int, uuid: str) -> None:
        success, stdout = await subprocess(
            f"sudo docker run -d -p {port}:{6090} --name {uuid} codescord")
        if not success:
            raise Errors.ContainerStartupError(stdout)

    @staticmethod
    async def stop_container(uuid: str) -> None:
        success, stdout = await subprocess(
            f"sudo docker stop {uuid}")
        if not success:
            raise Errors.ContainerStopError(stdout)

        success, stdout = await subprocess(
            f"sudo docker rm {uuid}")

        if not success:
            raise Errors.ContainerRmError(stdout)

    def get_uuid(self) -> str:
        while (uuid := str(uuid4())) not in self.used_ids:
            self.used_ids.add(uuid)
            return uuid

    def get_next_port(self) -> int:
        port = self.initial_port
        while True:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
            port += 1

    async def process(self, message: Union[Message, discord.Message]) -> str:
        if message.author != self.user:
            if match := self.code_pattern.search(message.content):
                source = Codescord.Source(*match.groups())
                port = self.get_next_port()
                uuid = self.get_uuid()
                try:
                    await self.start_container(port, uuid)

                    stdout = await self.codescord_client.process(source, ("localhost", port))

                    asyncio.create_task(self.stop_container(uuid))

                    return stdout
                finally:
                    self.used_ports.remove(port)
                    self.used_ids.remove(uuid)

    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent) -> None:
        message = Message(
            message_id=event.data["id"],
            author=(await self.fetch_user(event.data["author"]["id"])),
            content=event.data["content"],
            guild=(await self.fetch_guild(event.data["guild_id"])),
            channel=(await self.fetch_channel(event.data["channel_id"])))
        try:
            db_response_message = await ResponseMessages.get_message(
                server_id=message.guild.id,
                channel_id=message.channel.id,
                user_message_id=message.id)

            response_message: discord.Message = await message.channel.fetch_message(
                db_response_message.message_id)

            if stdout := (await self.process(message)):
                await edit(stdout, response_message)
        except DoesNotExist:
            pass

    async def on_message(self, message: discord.Message) -> None:
        if stdout := (await self.process(message)):
            response = await send(stdout, message.channel)
            response_message = await ResponseMessages.create_message(
                server_id=message.guild.id,
                channel_id=message.channel.id,
                user_message_id=message.id,
                message_id=response.id)
            await response_message.save()

    @staticmethod
    async def on_ready():
        print("online.")
