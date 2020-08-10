import discord
import Codescord
import re


class Client(discord.Client):
    def __init__(self):
        super(Client, self).__init__()
        self.codescord_client = Codescord.client.Client(self.loop)
        self.code_pattern = re.compile(r"```(\w+)\n([^=`]+)```", re.DOTALL)

    @staticmethod
    async def on_ready():
        print("bot online")

    async def on_message_edit(self) -> None:
        pass

    async def on_message(self, message: discord.Message) -> None:
        if message.author != self.user:
            if match := self.code_pattern.search(message.content):
                source = Codescord.Source(*match.groups())
                stdout = await self.codescord_client.process(source)
                await message.channel.send(
                    f"```{stdout}```"
                )
