from typing import *
import socket
import asyncio
from math import ceil
import utils


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Source:
    def __init__(self, language: str, code: str) -> None:
        self.language = language
        self.code = code


class Client:
    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()

    def close(self) -> None:
        self.socket.close()
        self.socket = setup_socket()

    async def response_as_int(self, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
        return int.from_bytes((await self.loop.sock_recv(self.socket, length)), endian, signed=signed)

    async def send_int_as_bytes(self, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
        await self.loop.sock_sendall(self.socket, integer.to_bytes(length, endian, signed=signed))

    async def assert_response_status(self, status: Union[int, bytes]) -> None:
        response = await self.response_as_int()
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def send_size(self, size: int, endian="big", signed=False) -> None:
        # number of bytes required to store the size in an int
        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(bites)
        await self.assert_response_status(utils.Protocol.success)

        await self.send_int_as_bytes(size, bites)
        await self.assert_response_status(utils.Protocol.success)

    async def download(self) -> bytes:
        # number of bytes required to store the size of the blob in an int
        bites = await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
        await self.send_int_as_bytes(utils.Protocol.success)

        # size of the blob in number of bytes
        size = await self.response_as_int(bites)
        await self.send_int_as_bytes(utils.Protocol.success)

        # initialising blob and downloading from socket, blob will be `size` bytes
        blob = b""
        for _ in range(int(size / utils.Protocol.max_buffer)):
            blob += await self.loop.sock_recv(self.socket, utils.Protocol.max_buffer)
        blob += await self.loop.sock_recv(self.socket, (size % utils.Protocol.max_buffer))
        # await self.send_int_as_bytes(utils.Protocol.success)

        return blob

    async def upload(self, payload: bytes) -> None:
        await self.send_size(len(payload))
        # await self.assert_response_status(utils.Protocol.success)

        print("sending payload")
        await self.loop.sock_sendall(self.socket, payload)
        await self.assert_response_status(utils.Protocol.success)

    async def authenticate(self) -> None:
        await self.send_int_as_bytes(utils.Protocol.authenticate)
        await self.assert_response_status(utils.Protocol.success)

        payload = utils.Protocol.get_protocol().encode("utf-8")
        await self.upload(payload)

    async def handle_source(self, source: Source) -> None:
        await self.send_int_as_bytes(utils.Protocol.file)
        await self.assert_response_status(utils.Protocol.success)

        payload = source.language.encode("utf-8")
        await self.upload(payload)

        payload = source.code.encode("utf-8")
        await self.upload(payload)

    async def handle_stdout(self) -> Optional[str]:
        response = await self.response_as_int()
        if response == utils.Protocol.text:
            await self.send_int_as_bytes(utils.Protocol.success)
            blob = await self.download()
            return blob.decode("utf-8")

    async def handle_connection(self, source: Source) -> str:
        await self.loop.sock_connect(self.socket, ("localhost", 6969))
        await self.authenticate()
        await self.handle_source(source)

        await self.send_int_as_bytes(utils.Protocol.awaiting)
        stdout = await self.handle_stdout()
        await self.loop.sock_recv(self.socket, utils.Protocol.awaiting)

        await self.send_int_as_bytes(utils.Protocol.close)
        await self.loop.sock_recv(self.socket, utils.Protocol.success)

        return stdout

    async def run(self, source: Source) -> str:
        try:
            stdout = await self.handle_connection(source)
        except KeyboardInterrupt:
            stdout = None
        finally:
            self.close()
        return stdout if stdout else "There was an error processing the source."
