import asyncio
import Codescord
import DiscordClient
import os


def run() -> None:
    py_source = Codescord.Source(
        language="py",
        code="print('Hello World!')"
    )
    cpp_source = Codescord.Source(
        language="cpp",
        code="""#include <iostream>
        int main(){
            std::cout << "Hello world!" << std::endl;
            return 0;
        }"""
    )

    loop = asyncio.get_event_loop()
    client = Codescord.client.Client(loop)

    result = loop.run_until_complete(
        client.run(py_source)
    )
    print(result)

    # result = loop.run_until_complete(
    #     client.run(py_source)
    # )

    result = loop.run_until_complete(
        client.run(cpp_source)
    )
    print(result)


def run_as_discord():
    token = os.environ.get("DISCORD_DEV")
    client = DiscordClient.client.Client()
    client.run(token)


if __name__ == '__main__':
    run()
