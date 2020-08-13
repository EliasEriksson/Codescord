import socket
import asyncio
import tempfile
from pathlib import Path
from math import ceil
import utils
from .languages import Languages
from .errors import *


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 6969))
    sock.setblocking(False)
    sock.listen()
    return sock


class Server:
    def __init__(self, loop=None) -> None:
        """
        :attr socket: the socket dealing with incoming connections.
        :attr loop: the event loop.
        :attr instructions: supported instructions that can be launched from the main processing loop in handle_connection.
        :attr languages: languages that can be processed.

        :param loop: the event loop
        """
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
        if response == status:
            print(f"response passed assertion ({status}).")
        elif response == utils.Protocol.Status.not_implemented:
            print(f"response was `{response}` (not implemented) expected `{status}`.")
            raise NotImplementedByClient()
        elif response == utils.Protocol.Status.internal_server_error:
            print(f"response was `{response}` (internal server error) expected `{status}`.")
            raise InternalServerError()
        elif response not in [getattr(utils.Protocol, attr) for attr in dir(utils.Protocol.Status)]:
            print(f"response `{response}` does not exist in Protocol.")
            raise NotImplementedByServer(f"Could not find status {response} in Protocol.")
        else:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

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

        size = len(payload)

        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(connection, bites)
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        await self.send_int_as_bytes(connection, size, bites)
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        await self.loop.sock_sendall(connection, payload)
        await self.assert_response_status(connection, utils.Protocol.Status.success)
        print("uploaded.")

    # methods above are generic/shared with client and should be put in a parent class

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
        else:
            await self.send_int_as_bytes(connection, utils.Protocol.Status.not_implemented)
            raise NotImplementedByServer()

    async def authenticate(self, connection: socket.socket) -> None:
        print("authenticating...")
        protocol = await self.download(connection)
        if protocol == utils.Protocol.get_protocol().encode("utf-8"):
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            print("authenticated.")
        else:
            await self.send_int_as_bytes(connection, utils.Protocol.Status.not_implemented)
            raise NotImplementedByServer()

    async def handle_connection(self, connection: socket.socket) -> None:
        """
        the main procedure of processing a connection.

        waits for an instruction, if the instruction is listed in instructions sends success back
        ands launches the instruction.
        if the instruction is not listed sends not implemented by server status back to the client.

        :param connection: the connection to the client.
        :return: None
        """
        print("handling the connection...")
        try:
            while (response := await self.response_as_int(connection)) != utils.Protocol.Status.close:
                if response in self.instructions:
                    await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
                    try:
                        # noinspection PyArgumentList
                        await self.instructions[response](connection)
                    except Exception as e:
                        await self.send_int_as_bytes(connection, utils.Protocol.Status.internal_server_error)
                        raise e
                else:
                    await self.send_int_as_bytes(connection, utils.Protocol.Status.not_implemented)
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            print("connection handled.")
        except ConnectionError:
            print("Client disconnected.")
        finally:
            connection.close()

    async def run(self) -> None:
        """
        starts the server

        awaits connections and creates a new task to handle the connection

        :return: None
        """
        print("awaiting connections...")
        try:
            while True:
                connection, _ = await self.loop.sock_accept(self.socket)
                asyncio.create_task(self.handle_connection(connection))
        except KeyboardInterrupt:
            pass
        finally:
            self.socket.close()
