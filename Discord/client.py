from typing import *
import discord
import Codescord
import re
from .models import ResponseMessages, Servers
from .message_parser import parse
import asyncio
import tortoise


class Message:
    """
    mimics a discord.Message object (adapter?)

    this object is passed down to Client.process() in Client.on_raw_message_edit
    it mimics the discord.Message objects since Client.process() takes a discord.Message object from
    Client.on_message() and the event (discord.RawMessageUpdateEvent) can not be casted to discord.Message
    (at least not recommended in the docs)
    """
    def __init__(self, message_id: int,
                 author: discord.User,
                 content: str,
                 guild: discord.Guild,
                 channel: discord.TextChannel) -> None:
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
    def __init__(self, start_port: int = 6090, end_port: int = None, loop=None,) -> None:
        """
        :param loop: asyncio event loop

        :attr loop: the asyncio event loop.
        :attr codescord_client: the client that is responsible for network traffic to the docker container.
        :attr initial_port: the initial port to open to a container.
        :attr code_pattern: if this re pattern matches its assumed that teh content contains executable code.
        :attr used_ports: ports to docker containers currently in use.
        :attr used_ids: names of docker containers currently in use.
        """
        loop = loop if not loop else asyncio.get_event_loop()
        super(Client, self).__init__(loop=loop)
        self.codescord_client = Codescord.Client(start_port, end_port, loop)
        self.manual_pattern = re.compile(r"/run\s*([^\n]*)\s*(?<!\\)`{3}([^\n]+)\n((?:(?!`{3}).)+)`{3}", re.DOTALL)
        self.auto_pattern = re.compile(r"(?<!\\)`{3}([^\n]+)\n((?:(?!`{3}).)+)`{3}", re.DOTALL)
        self.used_ports: Set[int] = set()
        self.used_ids: Set[str] = set()

    async def process_commands(self, message: Union[Message, discord.Message]) -> bool:
        """
        scans the discord message an attempt of "command line usage".

        if the message starts with "/codescord" it is assumed that the user attempted
        to interact with the command line use of this bot.
        the argument parser is setup in .message_parser.py.
        :param message: some discord users message.
        :return: true if command line use was detected else false.
        """
        if message.author != self.user and message.content.startswith("/codescord"):
            result, error = parse(message.content)
            if error:
                mes = "\n".join([f"{'`' * 3}{part}{'`' * 3}"for part in result])
                await message.channel.send(mes)
                return True
            elif vars(result):
                guild = await Servers.get_server(server_id=message.guild.id)
                await guild.update_from_dict({
                    result.option: result.value
                }).save()
                await message.channel.send(
                    f"{result.option.replace('_', '-')} is now "
                    f"`{'on' if result.value else 'off'}` for this server."
                )
                return True
        return False

    async def manual_process(self, message: Union[Message, discord.Message]):
        """
        the same as self.auto_process but with different pattern.

        :param message: discord message from some user to attempt to process.
        :return: execution result (stdout)
        """
        if message.author != self.user:
            if match := self.manual_pattern.findall(message.content):
                sources: List[Codescord.Source] = [
                    Codescord.Source(language, code, sys_args)
                    for sys_args, language, code in match
                ]
                source_process_tasks: List[asyncio.Task] = [
                    asyncio.create_task(self.codescord_client.schedule_process(source))
                    for source in sources
                ]
                results: List[str] = [
                    (f"{'`' * 3}\n"
                     f"{result if (result := await task) else 'Code gave no result but compiled and ran successfully.'}"
                     f"\n{'`' * 3}")
                    for task in source_process_tasks
                ]
                return results

    async def auto_process(self, message: Union[Message, discord.Message]) -> List[str]:
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
        (OBS! if these tasks closing the containers would somehow be stopped by i.e a keyboard interrupt.
        there is a fallback in main.py to stop and remove the containers from the image `codescord`.)

        :param message: discord message from some user to attempt to process.
        :return: execution result (stdout)
        """
        if message.author != self.user:
            if match := self.auto_pattern.findall(message.content):
                sources: List[Codescord.Source] = [
                    Codescord.Source(language, code)
                    for language, code in match
                ]
                source_process_task: List[asyncio.Task] = [
                    asyncio.create_task(self.codescord_client.schedule_process(source))
                    for source in sources
                ]
                results: List[str] = [
                    (f"{'`' * 3}\n"
                     f"{result if (result := await task) else 'Code gave no result but compiled and ran successfully.'}"
                     f"\n{'`' * 3}")
                    for task in source_process_task
                ]
                return results

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

            if results := (await self.manual_process(message)):
                edit = "\n".join(results)
                await response_message.edit(content=edit)
            elif (await Servers.get_server(server_id=message.guild.id)).auto_run:
                if results := (await self.auto_process(message)):
                    edit = "\n".join(results)
                    await response_message.edit(content=edit)

        except tortoise.exceptions.DoesNotExist:
            pass

    async def on_message(self, message: discord.Message) -> None:
        """
        scans sent message for runnable commands.

        searches for patterns in a discord message and sees if any commands match.
        first attempts to see if options are modified with /codescord.
        secondly searches for a manual run of highlighted code block (/run```lang\ncode```)
        thirdly it checks if a server have auto-run enabled, if it does it attempts to execute any code block
        if a code block was executed from the message an entry in the database is made so if that message in the
        future is edited the response to that message can also be updated.

        :param message: discord message sent by some user.
        :return: None
        """
        if message.guild:
            if await self.process_commands(message):
                pass
            if results := (await self.manual_process(message)):
                response: discord.Message = await message.channel.send(f"{chr(10).join(results)}")
                response_message = await ResponseMessages.create_message(
                    server_id=message.guild.id,
                    channel_id=message.channel.id,
                    user_message_id=message.id,
                    message_id=response.id)
                await response_message.save()
            elif (await Servers.get_server(server_id=message.guild.id)).auto_run:  # retry with auto run if it is on
                if results := (await self.auto_process(message)):
                    response: discord.Message = await message.channel.send(f'{chr(10).join(results)}')
                    response_message = await ResponseMessages.create_message(
                        server_id=message.guild.id,
                        channel_id=message.channel.id,
                        user_message_id=message.id,
                        message_id=response.id)
                    await response_message.save()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        adds the guild to the database and messages the person who invited it.

        :param guild: the guild the bot was invited to
        :return: None
        """
        await Servers.create_server(guild.id)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add):
            if entry.target == self.user:
                user: discord.User = entry.user
                await user.send(
                    "Thank you for using me on your server. Currently to run code with me on your "
                    "server you need to use the format:\n"
                    "/run\n"
                    "\\`\\`\\`language\n"
                    "code\n"
                    "\\`\\`\\`\n"
                    "If you would prefer to have all highlighted code blocks to run automatically "
                    "and not use the /run before them, "
                    "run command `/codescord auto-run on` in one of your servers text channels "
                    "the bot is allowed to read."
                )
                break

    @staticmethod
    async def on_guild_remove(guild: discord.Guild) -> None:
        """
        removes a guild from the database when the bot gets kicked / banned etc from a server

        :param guild: the guild the bot was removed from
        :return: None
        """
        try:
            server = await Servers.get_server(guild.id)
            await server.delete()
        except tortoise.exceptions.DoesNotExist:
            pass

    async def on_ready(self):
        """
        syncs the database on boot.

        :return: None
        """
        guilds_ids = set(set((guild.id for guild in self.guilds)))
        try:
            guilds_ids.update((guild.id for guild in await self.fetch_guilds(limit=200).flatten()))
        except discord.HTTPException:
            pass
        for guild_id in guilds_ids:
            await Servers.create_server(guild_id)

        servers = await Servers.all()
        for server in servers:
            try:
                await self.fetch_guild(server.server_id)
            except (discord.Forbidden, discord.HTTPException):
                await server.delete()
        print("online.")
