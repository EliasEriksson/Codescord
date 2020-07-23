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
        """
        Server class that manages the execution of files inside the docker container.
        Receives files from client over socket connection.
        Server can utilise instructions listed in utils.Protocol.Instructions.
        Functions to execute specific language source is found in languages.Languages

        :attr socket: the servers socket clients connect to
        :attr loop: event loop to receive/send data
        :attr instructions: instructions mapped from utils.Protocol.Instructions to Server methods
        :attr languages: name of languages currently supported. Must match names in highlight.js
        (https://github.com/highlightjs/highlight.js)
        :param loop:
        """
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.instructions = {
            utils.Protocol.Instructions.protocol: self.handle_file,
            utils.Protocol.Instructions.file: self.handle_protocol,
        }
        self.languages = {
            "python": Languages.python,
            "py": Languages.python,

            "cpp": Languages.cpp,
            "c++": Languages.cpp,
        }

    def close(self) -> None:
        """
        does everything required to properly close the connection of the server instance
        :return: None
        """
        self.socket.close()

    async def download(self, connection: socket.socket, size: int) -> bytes:
        """
        downloads a byte blob from connection in chunks of utils.Protocol.buffer_size

        :param connection: connection to the client sending the blob
        :param size: size of the blob in bytes
        :return: blob
        """
        blob = b""

        for _ in range(ceil(size / utils.Protocol.buffer_size)):
            blob += await self.loop.sock_recv(connection, utils.Protocol.buffer_size)
        await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.success)
        return blob

    async def receive_file(self, connection: socket.socket, file: Union[Path, str], size: int) -> None:
        """
        open file in byte write mod and starts downloading a file from the client

        :param connection: connection to the client
        :param file: file path to the downloaded file
        :param size: file size in bytes
        :return: None
        """
        content = await self.download(connection, size)
        with open(file, "wb") as script:
            script.write(content)

    @utils.cast_to_annotations
    async def handle_file(self, connection: socket.socket, language: str, size: int) -> None:
        """
        downloads a file from the client, executes it and sends the result back to the client

        the file is deleted after execution

        :param connection: connection to the client
        :param language: the source language (supported languages in languages.Languages)
        :param size: size of the downloaded file
        :return: None
        """
        if language in self.languages:
            await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.success)
            with tempfile.TemporaryDirectory() as tempdir:
                file = Path(tempdir).joinpath(f"script.{language}")
                await self.receive_file(connection, file, size)
                result = await asyncio.wait_for(self.languages[language](file), 30)
            await self.loop.sock_sendall(connection, utils.Protocol.Instructions.text.encode("utf-8"))
            response = await self.loop.sock_recv(connection, utils.Protocol.buffer_size)
            if not response == utils.Protocol.StatusCodes.success:
                await self.loop.sock_sendall(connection, result)
                response = await self.loop.sock_recv(connection, utils.Protocol.buffer_size)
                if response == utils.Protocol.StatusCodes.success:
                    # everything went well here =)
                    pass
        else:
            await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.not_implemented)

    @utils.cast_to_annotations
    async def handle_protocol(self, connection: socket.socket, size: int) -> None:
        """
        verifies that the client and server speaks the same protocol

        sends either utils.Protocol.StatusCodes.success
        or           utils.Protocol.StatusCodes.internal_server_Error
        depending on if server and client have same protocol

        :param connection: connection to the client
        :param size: size of the protocol message in bytes
        :return:
        """
        await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.success)
        client_protocol = (await self.download(connection, size)).decode("utf-8")
        if client_protocol == utils.Protocol.get_protocol():
            await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.success)
        else:
            await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.internal_server_error)

    async def handle_connection(self, connection: socket.socket) -> None:
        """
        connection loop. connection tries to last for as long the loop is going.

        server expects an instruction from the client that is then launched by matching the received instruction to
        method in self.instructions.

        loop stops when clients sends status 600 when it is expecting an instruction
        :param connection: connection to the client
        :return: None
        """
        while (response := (await self.loop.sock_recv(connection, utils.Protocol.buffer_size))) != utils.Protocol.StatusCodes.close:
            instruction, *args = response.decode("utf-8").split(":")
            if instruction in self.instructions:
                try:
                    self.instructions[instruction](connection, *args)
                except BrokenPipeError:
                    break
                except asyncio.TimeoutError:
                    await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.internal_server_error)
                    break
                except Exception as e:
                    # log the error with something else than print
                    print(e)
                    await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.internal_server_error)
                    break
            else:
                await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.not_implemented)
                break
        else:
            await self.loop.sock_sendall(connection, utils.Protocol.StatusCodes.success)

    async def accept_connection(self) -> None:
        """
        accepts a connection that is then handled by self.handle_connection
        :return: None
        """
        connection, *_ = await self.loop.sock_accept(self.socket)
        await self.handle_connection(connection)
        connection.close()

    async def run(self) -> None:
        try:
            while True:
                await self.accept_connection()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.close()
            raise e
        self.close()
