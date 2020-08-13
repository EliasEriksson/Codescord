from typing import *
import socket
import asyncio
import tempfile
from pathlib import Path
from math import ceil
import utils
from .languages import Languages


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 6969))
    sock.setblocking(False)
    sock.listen()
    return sock


class Server:
    def __init__(self, loop=None) -> None:
        print("initializing...")
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.instructions = {
            utils.Protocol.Status.authenticate: self.authenticate,
            utils.Protocol.Status.file: self.handle_file,
        }
        self.languages = {
            "python": Languages.python,
            "py": Languages.python,

            "cpp": Languages.cpp,
            "c++": Languages.cpp,
        }
        print("initialized.")

    def close(self) -> None:
        print("closing...")
        self.socket.close()
        print("closed.")

    async def response_as_int(self, connection: socket.socket, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
        print(f"awaiting response as int...")
        integer = int.from_bytes((await self.loop.sock_recv(connection, length)), endian, signed=signed)
        print(f"got response as int ({integer}).")
        return integer

    async def send_int_as_bytes(self, connection: socket.socket, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
        print(f"sending int ({integer}) as bytes...")
        await self.loop.sock_sendall(connection, integer.to_bytes(length, endian, signed=signed))
        print(f"sent int ({integer}) as bytes.")

    async def assert_response_status(self, connection: socket.socket, status: int) -> None:
        print(f"asserting response status ({status})...")
        response = await self.response_as_int(connection)
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")
        print(f"response passed assertion ({status}).")

    async def send_size(self, connection: socket.socket, size: int, endian="big", signed=False) -> None:
        print("sending size...")
        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(connection, bites)
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        await self.send_int_as_bytes(connection, size, bites, endian, signed)
        await self.assert_response_status(connection, utils.Protocol.Status.success)
        print("size sent.")

    async def download(self, connection: socket.socket) -> bytes:
        print("downloading...")
        bites = await self.response_as_int(connection)
        await self.send_int_as_bytes(connection, utils.Protocol.Status.success)

        size = await self.response_as_int(connection, bites)
        await self.send_int_as_bytes(connection, utils.Protocol.Status.success)

        blob = b""
        for _ in range(int(size / utils.Protocol.max_buffer)):
            blob += await self.loop.sock_recv(connection, utils.Protocol.max_buffer)
        blob += await self.loop.sock_recv(connection, (size % utils.Protocol.max_buffer))

        print("downloaded.")
        return blob

    async def upload(self, connection: socket.socket, payload: bytes) -> None:
        print("uploading...")
        await self.send_size(connection, len(payload))

        await self.loop.sock_sendall(connection, payload)
        await self.assert_response_status(connection, utils.Protocol.Status.success)
        print("uploaded.")

    async def handle_file(self, connection: socket.socket) -> None:
        print("handling file...")
        language = (await self.download(connection)).decode("utf-8")
        if language in self.languages:
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            code = await self.download(connection)
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            await self.assert_response_status(connection, utils.Protocol.Status.awaiting)

            with tempfile.TemporaryDirectory() as tempdir:
                file = Path(tempdir).joinpath(f"script.{language}")
                with open(file, "wb") as script:
                    script.write(code)
                stdout = await asyncio.wait_for(self.languages[language](file), utils.Protocol.timeout)

            await self.send_int_as_bytes(connection, utils.Protocol.Status.text)
            await self.assert_response_status(connection, utils.Protocol.Status.success)

            await self.upload(connection, stdout)
            await self.send_int_as_bytes(connection, utils.Protocol.Status.awaiting)
            print("file handled.")

    async def authenticate(self, connection: socket.socket) -> None:
        print("authenticating...")
        protocol = await self.download(connection)
        if protocol == utils.Protocol.get_protocol().encode("utf-8"):
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            print("authenticated.")

    async def handle_connection(self, connection: socket.socket) -> None:
        print("handling the connection...")
        try:
            while (response := await self.response_as_int(connection)) != utils.Protocol.Status.close:
                if response in self.instructions:
                    await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
                    # noinspection PyArgumentList
                    await self.instructions[response](connection)
                else:
                    await self.send_int_as_bytes(connection, utils.Protocol.Status.not_implemented)
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            print("connection handled.")
        except BrokenPipeError:
            print("Client disconnected.")
        finally:
            connection.close()

    async def run(self) -> None:
        print("awaiting connections...")
        try:
            while True:
                connection, _ = await self.loop.sock_accept(self.socket)
                asyncio.create_task(self.handle_connection(connection))
        except KeyboardInterrupt:
            pass
        finally:
            self.close()
