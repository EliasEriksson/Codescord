from typing import *
import discord
import Codescord
import re
from uuid import uuid4
from .models import ResponseMessages
import asyncio
from .errors import Errors
import tortoise


async def edit(stdout: str, message: discord.Message, description: str = None) -> None:
    """
    wrapper for discord.Message.edit()

    :param stdout: execution result from executing code
    :param message: message to edit
    :param description: message above the execution result
    :return:
    """
    description = description if description else ""
    await message.edit(content=f"{description}\n```{stdout}```")


async def send(stdout: str, channel: discord.TextChannel, description: str = None) -> discord.Message:
    """
    wrapper for discord.TextChannel.send()

    :param stdout: execution result from executing code
    :param channel: channel to send message in
    :param description: message above the execution result
    :return:
    """
    description = description if description else ""
    return await channel.send(f"{description}\n```{stdout}```")


async def subprocess(stdin: str) -> Tuple[bool, str]:
    """
    easier wrapper around asyncio.create_subprocess_exec

    :param stdin: command to execute in subprocess
    :return: result from subprocess
    """
    process = await asyncio.create_subprocess_exec(
        *stdin.split(" "), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if not stdout:
        print(f"failed with '{stdin}'")
        return False, stderr.decode("utf-8")
    print(f"succeeded with '{stdin}'")
    return True, stdout.decode("utf-8")


class Message:
    """
    mimics a discord.Message object (adapter?)

    this object is passed down to Client.process() in Client.on_raw_message_edit
    it mimics the discord.Message objects since Client.process() takes a discord.Message object from
    Client.on_message() and the event (discord.RawMessageUpdateEvent) can not be casted to discord.Message
    (at least not recommended in the docs)
    """
    def __init__(self, message_id: int, author: discord.User, content: str, guild: discord.Guild, channel: discord.TextChannel) -> None:
        """

        :attr id: the edited message id
        :attr author: the author of the message
        :attr content: the content of the message
        :attr guild: the discord guild (server) where the message was sent
        :attr channel: the discord TextChannel where the message was sent
        """

        self.id = message_id
        self.author = author
        self.content = content
        self.guild = guild
        self.channel = channel


class Client(discord.Client):
    """
    this client is the master manager for the Codescord program.
    whenever a message containing a highlighted code block is sent/edited this client will start up a
    container with a Codescord.Server.
    this client will then use its internal Codescord.Client to connect the the Codescord.Server in the container
    and send the source over for execution to then send the result (stdout) from the executed source in a new message.
    the container with the Codescord.Server will then be closed.

    if the message was edited this client will look thru its database if it replied to that exact message.
    if it did reply to that message it will attempt to execute potential source.
    if it never replied to the edited message it will NEVER scan the message for source not execute it even if it did.
    """
    def __init__(self, loop=None, initial_port: int = 6090) -> None:
        """
        :param loop: asyncio event loop
        :param initial_port: first port to open to a docker container. (will increment by 1 for each active container.)

        :attr loop: the asyncio event loop.
        :attr codescord_client: the client that is responsible for network traffic to the docker container.
        :attr initial_port: the initial port to open to a container.
        :attr code_pattern: if this re pattern matches its assumed that teh content contains executable code.
        :attr used_ports: ports to docker containers currently in use.
        :attr used_ids: names of docker containers currently in use.
        """
        loop = loop if not loop else asyncio.get_event_loop()
        super(Client, self).__init__(loop=loop)
        self.codescord_client = Codescord.Client(self.loop)
        self.initial_port = initial_port
        self.code_pattern = re.compile(r"```([\w+]+)\n([^=`]+)```", re.DOTALL)
        self.used_ports = set()
        self.used_ids = set()

    @staticmethod
    async def start_container(port: int, uuid: str) -> None:
        """
        starts a docker container with provided id and port.

        :param port: local port to expose to the container.
        :param uuid: container id
        :return: None
        """
        success, stdout = await subprocess(
            f"docker run -d -p {port}:{6090} --name {uuid} codescord")
        if not success:
            raise Errors.ContainerStartupError(stdout)

    @staticmethod
    async def stop_container(uuid: str) -> None:
        """
        stops a docker container with some id.

        :param uuid: container id
        :return: None
        """
        success, stdout = await subprocess(
            f"docker stop {uuid}")
        if not success:
            raise Errors.ContainerStopError(stdout)

        success, stdout = await subprocess(
            f"docker rm {uuid}")

        if not success:
            raise Errors.ContainerRmError(stdout)

    def get_uuid(self) -> str:
        """
        generates a container id from uuid4 and adds it to self.used_ids

        this while loop will pretty much never run more than once

        :return: id for the docker container
        """
        while (uuid := str(uuid4())) not in self.used_ids:
            pass
        self.used_ids.add(uuid)
        return uuid

    def get_next_port(self) -> int:
        """
        gets the next free port in line starting from self.initial_port.

        :return: container port.
        """
        port = self.initial_port
        while True:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
            port += 1

    async def process(self, message: Union[Message, discord.Message]) -> str:
        """
        scans the discord message for highlighted a highlighted code block to attempt execution.

        if a highlighted code block is found a Codescord.Source object is made
        (containing the language highlight and the source.
        a unused port and id is generated for the docker container and container will be started.
        self.codescord_client will attempt to connect to the Codescord.Server inside the container
        and send over the source.
        (OBS! the first connection attempt self.codescord_client will most of the time happen before the container is
        started but it should always succeed on the first retry)
        after the source have been successfully or unsuccessfully processed a parallel task is started to handle
        the closing and removal of the container.
        (OBS! if these tasks closing the containers would somehow be stopped by i.e a keyboard interupt.
        there is a fallback in main.py to stop and remove the containers from the image `codescord`.)

        :param message: discord message from some user to attempt to process.
        :return: execution result (stdout)
        """
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
        """
        procedure to update a sent response to some previously executed highlighted code block.

        attempts to find an entry in the database corresponding to the updated message.
        if found the message will be scanned for a highlighted code block and attempt execution.
        if it was successfully executed this clients response message to the edited message will be edited to the
        new execution result.

        :param event: data attribute on this event is used to construct the Discord.Message (OBS not discord.Message!)
        :return: None
        """
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
        except tortoise.exceptions.DoesNotExist:
            pass

    async def on_message(self, message: discord.Message) -> None:
        """
        procedure when a new message is sent.

        scans a new discord message for a highlighted code block, if found execute it.
        if the message was processed an entry in the database is made so if that message in the future
        is updated the response to that message can also be updated.

        :param message: discord message sent by some user.
        :return: None
        """
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
