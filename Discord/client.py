import discord
import Codescord
import re

# model a message table with help of
# https://github.com/EliasEriksson/ClassicQuestGivers/blob/master/ClassicQuestGivers/ClassicQuestGivers/db.py
# and https://pypi.org/project/sqlalchemy-aio/
# id, guild, channel, message (ids)


class Client(discord.Client):
    def __init__(self):
        super(Client, self).__init__()
        self.codescord_client = Codescord.Client(self.loop)
        self.code_pattern = re.compile(r"```(\w+)\n([^=`]+)```", re.DOTALL)

    @staticmethod
    async def on_ready():
        print("bot online")

    async def on_message_edit(self, _, after: discord.Message) -> None:
        channel: discord.TextChannel = after.channel
        message = channel.fetch_message(0)

    async def on_message(self, message: discord.Message) -> None:
        if message.author != self.user:
            if match := self.code_pattern.search(message.content):
                source = Codescord.Source(*match.groups())
                stdout = await self.codescord_client.process(source)
                await message.channel.send(
                    f"```{stdout}```"
                )
