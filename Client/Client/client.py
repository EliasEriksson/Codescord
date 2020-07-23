from typing import Tuple
import socket
import asyncio
from math import ceil
import utils


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Protocol:
    command_protocol = "protocol"
    command_file = "file"
    command_text = "text"
    commands = (command_protocol, command_file, command_text)

    buffer_size = 128

    success = b"200"
    failed = b"400"
    internal_server_error = b"500"
    not_implemented = b"501"

    @classmethod
    def get_protocol(cls):
        # non callable attributes and their values
        protocol = [f"{attr}={value}" for attr in dir(cls)
                    if not (callable((value := getattr(cls, attr))) or attr.startswith("__"))]

        return ":".join(protocol)


class C:
    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()

    def close(self) -> None:
        self.socket.close()
        self.socket = setup_socket()

    async def authenticate(self) -> bool:
        await self.loop.sock_connect(self.socket, ("localhost", 6969))
        response = await self.loop.sock_recv(self.socket, Protocol.buffer_size)
        if response == Protocol.success:
            payload = Protocol.get_protocol().encode("utf-8")
            await self.loop.sock_sendall(self.socket, f"{Protocol.command_protocol}:{len(payload)}".encode("utf-8"))
            await self.loop.sock_sendall(self.socket, payload)
            response = await self.loop.sock_recv(self.socket, Protocol.buffer_size)
            if response == Protocol.success:
                return True
            elif response == Protocol.failed:
                return False
            else:
                # non understandable response, not speaking the same protocol
                raise ConnectionAbortedError
        else:
            # no response from server
            raise ConnectionAbortedError

    async def send_file(self, code: str) -> bool:
        payload = code.encode("utf-8")
        await self.loop.sock_sendall(self.socket, f"{Protocol.command_file}:{len(payload)}".encode("utf-8"))
        response = await self.loop.sock_recv(self.socket, Protocol.buffer_size)
        if response == Protocol.success:
            await self.loop.sock_sendall(self.socket, payload)
            response = await self.loop.sock_recv(self.socket, Protocol.buffer_size)
            if response == Protocol.success:
                return True
            elif response == Protocol.failed:
                return False
            else:
                # unknown transmission error
                raise ConnectionAbortedError
        else:
            # unknown transmission error
            raise ConnectionAbortedError

    async def receive_result(self) -> str:
        response = await self.loop.sock_recv(self.socket, Protocol.buffer_size)
        command, *args = response.decode("utf-8").split(":")
        if command == Protocol.command_text:
            size = int(*args)
            result = b""
            for _ in range(ceil(size / Protocol.buffer_size)):
                result += await self.loop.sock_recv(self.socket, Protocol.buffer_size)
            await self.loop.sock_sendall(self.socket, Protocol.success)
            return result.decode("utf-8")
        else:
            # not implemented
            raise ConnectionAbortedError

    async def process(self, code: str) -> str:
        if not await self.authenticate():
            raise ConnectionAbortedError
        if not await self.send_file(code):
            raise ConnectionAbortedError
        result = await self.receive_result()

        return result

    async def run(self, code: str) -> str:
        try:
            return await self.process(code)
        except (KeyboardInterrupt, ConnectionRefusedError):
            pass
        except Exception as e:
            self.close()
            raise e
        self.close()


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


if __name__ == '__main__':
    print(Protocol)
