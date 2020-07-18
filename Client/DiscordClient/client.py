import discord
from Client.client import Client as PyscordClient
import re


class Client(discord.Client):
    def __init__(self):
        super(Client, self).__init__()
        self.pyscord_client = PyscordClient(self.loop)
        self.code_pattern = re.compile(r"```(\w+)\n([^=`]+)```", re.DOTALL)
        self.languages = {
            "python": self.handle_python
        }

    async def on_ready(self):
        print("bot online")

    async def handle_python(self, code: str) -> str:
        return await self.pyscord_client.connect(code)

    async def on_message(self, message: discord.Message) -> None:
        if match := self.code_pattern.search(message.content):
            language, code = match.groups()
            if language in self.languages:
                result = await self.languages[language](code)
                await message.channel.send(
                    f"Result from {message.id}:\n```{result}```"
                )
