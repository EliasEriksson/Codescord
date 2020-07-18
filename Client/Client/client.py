from typing import *
import socket
import asyncio
from io import BytesIO


test_code = """
var = "asd"
print(var)
"""


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Client:
    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()

    def close(self) -> None:
        self.socket.close()

    async def receive(self) -> str:
        print("starting to receive data from server...")
        result = b""
        while data := await self.loop.sock_recv(self.socket, 128):
            result += data
        print("received result from server.")
        return result.decode("utf-8")

    async def send_action(self, action: str) -> bool:
        await self.loop.sock_sendall(self.socket, action.encode("utf-8"))
        status = (await self.loop.sock_recv(self.socket, 128)).decode("utf-8")
        if status == "OK":
            return True
        return False

    async def send(self, code: str) -> None:
        print("starting to send code to server...")
        payload = code.encode("utf-8")
        if await self.send_action(f"file:{len(payload)}"):
            await self.loop.sock_sendall(self.socket, payload)
        print("code sent to server.")

    async def connect(self) -> None:
        print("awaiting server for connection")
        await self.loop.sock_connect(self.socket, ("localhost", 6969))
        print("connected with the server.")
        await self.send(test_code)
        result = await self.receive()
        print(result)

    async def run(self) -> None:
        try:
            await self.connect()
        except KeyboardInterrupt:
            self.close()
            pass

