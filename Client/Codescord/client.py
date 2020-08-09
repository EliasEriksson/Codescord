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
        print("initializing...")
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        print("initialized.")

    def close(self) -> None:
        print("closing...")
        self.socket.close()
        self.socket = setup_socket()
        print("closed.")

    async def response_as_int(self, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
        print("awaiting response as int...")
        integer = int.from_bytes((await self.loop.sock_recv(self.socket, length)), endian, signed=signed)
        print(f"got response as int ({integer}).")
        return integer

    async def send_int_as_bytes(self, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
        print(f"sending int ({integer}) as bytes...")
        await self.loop.sock_sendall(self.socket, integer.to_bytes(length, endian, signed=signed))
        print(f"sent int ({integer}) as bytes.")

    async def assert_response_status(self, status: Union[int, bytes]) -> None:
        print(f"asserting response status ({status})...")
        response = await self.response_as_int()
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")
        print(f"response passed assertion ({status}).")

    async def send_size(self, size: int, endian="big", signed=False) -> None:
        print("sending size...")
        # number of bytes required to store the size in an int
        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(bites)
        await self.assert_response_status(utils.Protocol.success)

        await self.send_int_as_bytes(size, bites)
        await self.assert_response_status(utils.Protocol.success)
        print("sent size.")

    async def download(self) -> bytes:
        print("downloading...")
        # number of bytes required to store the size of the blob in an int
        bites = await self.response_as_int()
        await self.send_int_as_bytes(utils.Protocol.success)

        # size of the blob in number of bytes
        size = await self.response_as_int(bites)
        await self.send_int_as_bytes(utils.Protocol.success)

        # initialising blob and downloading from socket, blob will be `size` bytes
        blob = b""
        for _ in range(int(size / utils.Protocol.max_buffer)):
            blob += await self.loop.sock_recv(self.socket, utils.Protocol.max_buffer)
        blob += await self.loop.sock_recv(self.socket, (size % utils.Protocol.max_buffer))
        print("downloaded.")
        return blob

    async def upload(self, payload: bytes) -> None:
        print("uploading...")
        await self.send_size(len(payload))

        await self.loop.sock_sendall(self.socket, payload)
        await self.assert_response_status(utils.Protocol.success)
        print("uploaded.")

    async def authenticate(self) -> None:
        print("authenticating...")
        await self.send_int_as_bytes(utils.Protocol.authenticate)
        await self.assert_response_status(utils.Protocol.success)

        payload = utils.Protocol.get_protocol().encode("utf-8")
        await self.upload(payload)
        print("authenticated.")

    async def handle_source(self, source: Source) -> None:
        print("handling the source...")
        await self.send_int_as_bytes(utils.Protocol.file)
        await self.assert_response_status(utils.Protocol.success)

        payload = source.language.encode("utf-8")
        await self.upload(payload)

        payload = source.code.encode("utf-8")
        await self.upload(payload)
        print("source handled.")

    async def handle_stdout(self) -> Optional[str]:
        print("handling stdout...")
        response = await self.response_as_int()
        if response == utils.Protocol.text:
            await self.send_int_as_bytes(utils.Protocol.success)
            blob = await self.download()
            await self.send_int_as_bytes(utils.Protocol.success)
            print("stdout handled.")
            return blob.decode("utf-8")

    async def handle_connection(self, source: Source) -> str:
        print("handling the connection...")
        await self.loop.sock_connect(self.socket, ("localhost", 6969))
        await self.authenticate()
        await self.handle_source(source)

        await self.send_int_as_bytes(utils.Protocol.awaiting)
        stdout = await self.handle_stdout()
        await self.loop.sock_recv(self.socket, utils.Protocol.awaiting)

        await self.send_int_as_bytes(utils.Protocol.close)
        await self.response_as_int(utils.Protocol.success)

        print("connection handled.")
        return stdout

    async def run(self, source: Source) -> str:
        print("connecting...")
        try:
            stdout = await self.handle_connection(source)
        except KeyboardInterrupt:
            stdout = None
        finally:
            self.close()
        print("disconnected.")
        return stdout if stdout else "There was an error processing the source."
