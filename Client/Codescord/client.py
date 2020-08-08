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

    @utils.cast_to_annotations
    async def download(self, size: int) -> bytes:
        blob = b""
        for _ in range(ceil(size / utils.Protocol.buffer_size)):
            blob += await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
        await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.success)
        return blob

    async def handle_stdout(self) -> str:
        response = await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
        instruction, *args = response.decode("utf-8").split(":")
        if instruction == utils.Protocol.Instructions.text:
            await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.success)
            blob = await self.download(*args)
            await self.assert_response_status(utils.Protocol.StatusCodes.advance)

            return blob.decode("utf-8")
        else:
            raise AssertionError("only text instructions can be handled by the client.")

    async def assert_response_status(self, status: Union[int, bytes]) -> None:
        response = await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def authenticate(self):
        payload = utils.Protocol.get_protocol().encode("utf-8")
        await self.loop.sock_sendall(
            self.socket,
            f"{utils.Protocol.Instructions.protocol}:{len(payload)}".encode("utf-8")
        )
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # server ready to receive message
        await self.loop.sock_sendall(self.socket, payload)
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # server got the message
        await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.advance)
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # successfully authenticated

    async def handle_source(self, source: Source) -> None:
        payload = source.code.encode("utf-8")
        await self.loop.sock_sendall(
            self.socket,
            f"{utils.Protocol.Instructions.file}:{source.language}:{len(payload)}".encode("utf-8")
        )
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # server ready to receive source
        await self.loop.sock_sendall(self.socket, payload)
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.advance)
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.advance)

        # server got the source
        # server successfully processed the source

    async def handle_connection(self, source: Source) -> str:
        try:
            await self.loop.sock_connect(self.socket, ("localhost", 6969))
            await self.authenticate()
            await self.handle_source(source)
            response = await self.handle_stdout()
            return response

        except AssertionError as e:
            return str(e)
        finally:
            await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.close)
            await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)

    async def run(self, source: Source) -> str:
        try:
            stdout = await self.handle_connection(source)
        except KeyboardInterrupt:
            stdout = None
        except Exception as e:
            self.close()
            raise e
        self.close()
        return stdout if stdout else "There was an unknown error processing the source"

