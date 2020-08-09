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
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.instructions = {
            utils.Protocol.authenticate: self.authenticate,
            utils.Protocol.file: self.handle_file,
        }
        self.languages = {
            "python": Languages.python,
            "py": Languages.python,

            "cpp": Languages.cpp,
            "c++": Languages.cpp,
        }

    def close(self) -> None:
        self.socket.close()

    async def response_as_int(self, connection: socket.socket, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
        b = await self.loop.sock_recv(connection, length)
        return int.from_bytes(b, endian, signed=signed)

    async def send_int_as_bytes(self, connection: socket.socket, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
        await self.loop.sock_sendall(connection, integer.to_bytes(length, endian, signed=signed))

    async def assert_response_status(self, connection: socket.socket, status: Union[int, bytes]) -> None:
        response = await self.response_as_int(connection)
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def send_size(self, connection: socket.socket, size: int, endian="big", signed=False) -> None:
        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(connection, bites)
        await self.assert_response_status(connection, utils.Protocol.success)

        await self.loop.sock_sendall(connection, size.to_bytes(bites, endian, signed=signed))
        await self.assert_response_status(connection, utils.Protocol.success)

    async def download(self, connection: socket.socket) -> bytes:
        bites = await self.response_as_int(connection)
        await self.send_int_as_bytes(connection, utils.Protocol.success)

        size = await self.response_as_int(connection, bites)
        await self.send_int_as_bytes(connection, utils.Protocol.success)

        blob = b""
        for _ in range(int(size / utils.Protocol.max_buffer)):
            print(f"iteration{_}")
            blob += await self.loop.sock_recv(connection, utils.Protocol.max_buffer)
        blob += await self.loop.sock_recv(connection, (size % utils.Protocol.max_buffer))

        return blob

    async def upload(self, connection: socket.socket, payload: bytes) -> None:
        await self.send_size(connection, len(payload))
        await self.assert_response_status(connection, utils.Protocol.success)

        await self.loop.sock_sendall(connection, payload)
        await self.assert_response_status(connection, utils.Protocol.success)

    async def handle_file(self, connection: socket.socket) -> None:
        language = (await self.download(connection)).decode("utf-8")
        if language in self.languages:
            await self.send_int_as_bytes(connection, utils.Protocol.success)

            code = (await self.download(connection))
            await self.send_int_as_bytes(connection, utils.Protocol.success)
            await self.assert_response_status(connection, utils.Protocol.awaiting)

            with tempfile.TemporaryDirectory() as tempdir:
                file = Path(tempdir).joinpath(f"script.{language}")
                with open(file, "wb") as script:
                    script.write(code)
                stdout = await asyncio.wait_for(self.languages[language](file), utils.Protocol.timeout)
            await self.upload(connection, stdout)
            await self.send_int_as_bytes(connection, utils.Protocol.awaiting)

    async def authenticate(self, connection: socket.socket) -> None:
        protocol = await self.download(connection)
        if protocol == utils.Protocol.get_protocol().encode("utf-8"):
            await self.send_int_as_bytes(connection, utils.Protocol.success)

    async def handle_connection(self, connection: socket.socket) -> None:
        while (response := await self.response_as_int(connection)) != utils.Protocol.close:
            if response in self.instructions:
                await self.send_int_as_bytes(connection, utils.Protocol.success)
                await self.instructions[response](connection)
        else:
            await self.send_int_as_bytes(connection, utils.Protocol.success)

        connection.close()

    async def run(self) -> None:
        try:
            while True:
                connection, _ = await self.loop.sock_accept(self.socket)
                asyncio.create_task(self.handle_connection(connection))
        except KeyboardInterrupt:
            pass
        finally:
            self.close()
