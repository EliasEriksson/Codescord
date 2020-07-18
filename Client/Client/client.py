from typing import *
import socket
import asyncio
from math import ceil


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Client:
    FAILURE = b"0"
    SUCCESS = b"1"
    BUFFER_SIZE = 128

    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.actions = {
            "stdout": self.handle_stdout
        }

    async def close(self) -> None:
        self.socket.close()
        self.socket = setup_socket()

    async def send_action(self, action: str) -> bool:
        await self.loop.sock_sendall(self.socket, action.encode("utf-8"))
        status = await self.loop.sock_recv(self.socket, self.BUFFER_SIZE)
        if status == self.SUCCESS:
            return True
        return False

    async def send(self, code: str) -> None:
        payload = code.encode("utf-8")
        if await self.send_action(f"file:{len(payload)}"):
            await self.loop.sock_sendall(self.socket, payload)

    async def receive_stdout(self, size: int) -> str:
        result = b""
        for _ in range(ceil(size / self.BUFFER_SIZE)):
            result += await self.loop.sock_recv(self.socket, self.BUFFER_SIZE)
        return result.decode("utf-8")

    async def handle_stdout(self, action_args: Tuple[str]) -> str:
        size = int(*action_args)
        return await self.receive_stdout(size)

    async def receive_action(self) -> str:
        action = (await self.loop.sock_recv(self.socket, self.BUFFER_SIZE)).decode("utf-8")
        return action

    async def handle_receive(self) -> str:
        action, *args = (await self.receive_action()).split(":")
        if action in self.actions:
            await self.loop.sock_sendall(self.socket, self.SUCCESS)
            return await self.actions[action](args)
        else:
            await self.loop.sock_sendall(self.socket, self.FAILURE)

    async def connect(self, code: str) -> str:
        await self.loop.sock_connect(self.socket, ("localhost", 6969))
        await self.send(code)
        result = await self.handle_receive()
        await self.close()
        return result

    async def run(self, code: str) -> None:
        try:
            await self.connect(code)
        except KeyboardInterrupt:
            await self.close()
        except ConnectionRefusedError:
            await self.close()

