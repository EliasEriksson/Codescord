from typing import *
import discord
import Codescord
import re
from uuid import uuid4
from .models import ResponseMessages
# from asyncio import subprocess
import asyncio


async def edit(stdout: str, message: discord.Message, description: str = None) -> None:
    description = description if description else ""
    await message.edit(content=f"{description}\n```{stdout}```")


async def send(stdout: str, channel: discord.TextChannel, description: str = None) -> discord.Message:
    description = description if description else ""
    return await channel.send(f"{description}\n```{stdout}```")


async def subprocess(stdin: str) -> Tuple[bool, str]:
    process = await asyncio.create_subprocess_exec(
        *stdin.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if not process.returncode == 0:
        return False, stderr.decode("utf-8")
    return True, stdout.decode("utf-8")


class Client(discord.Client):
    def __init__(self, loop=None) -> None:
        loop = loop if not loop else asyncio.get_event_loop()
        super(Client, self).__init__(loop=loop)
        self.codescord_client = Codescord.Client(self.loop)
        self.code_pattern = re.compile(r"```(\w+)\n([^=`]+)```", re.DOTALL)
        self.used_ports = set()
        self.used_ids = set()

    def get_uuid(self) -> str:
        while (uuid := uuid4()) not in self.used_ids:
            return str(uuid)

    def get_next_port(self) -> int:
        port = 6090
        while True:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
            port += 1

    async def process(self, message: discord.Message) -> str:
        if message.author != self.user:
            if match := self.code_pattern.search(message.content):
                source = Codescord.Source(*match.groups())
                port = self.get_next_port()
                uuid = self.get_uuid()
                success, stdout = await subprocess(
                    f"sudo docker run -d -p {port}:{port} --name {uuid}")
                if not success:
                    raise Exception()

                stdout = await self.codescord_client.process(source, ("localhost", port))

                success, _ = await subprocess(
                    f"sudo docker stop {uuid}")
                if not success:
                    raise Exception()

                success, _ = await subprocess(
                    f"sudo docker rm {uuid}")

                if not success:
                    raise Exception()

                return stdout

    # async def process(self, message: discord.Message) -> str:
    #     if message.author != self.user:
    #         if match := self.code_pattern.search(message.content):
    #             source = Codescord.Source(*match.groups())
    #             stdout = await self.codescord_client.process(source, ("localhost", 6969))
    #             return stdout

    async def on_message_edit(self, _, user_edited_message: discord.Message) -> None:
        if stdout := (await self.process(user_edited_message)):
            db_response_message = await ResponseMessages.get_message(
                server_id=user_edited_message.guild.id,
                channel_id=user_edited_message.channel.id,
                user_message_id=user_edited_message.id)

            response_message: discord.Message = await user_edited_message.channel.fetch_message(
                db_response_message.message_id)
            await edit(stdout, response_message)

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
