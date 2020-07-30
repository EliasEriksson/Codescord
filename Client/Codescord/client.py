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
            return blob.decode("utf-8")
        else:
            raise AssertionError("only text instructions can be handled by the client.")

    async def assert_response_status(self, status: Union[int, bytes]) -> None:
        print(f"awaiting response from server expecting {status}")
        response = await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
        if response != status:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")
        print(f"response code was {status} as expected")

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
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # successfully authenticated

    async def handle_source(self, source: Source) -> None:
        payload = source.code.encode("utf-8")
        print("sending instruction to the server...")
        await self.loop.sock_sendall(
            self.socket,
            f"{utils.Protocol.Instructions.file}:{source.language}:{len(payload)}".encode("utf-8")
        )
        print("instruction was sent to the server.")
        print("awaiting success about receiving the instruction")
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        print("instruction was sent successfully")
        # server ready to receive source
        print("sending the source to the server...")
        await self.loop.sock_sendall(self.socket, payload)
        print("source was sent to the server")
        print("awaiting success about receiving the source...")
        await self.assert_response_status(utils.Protocol.StatusCodes.success)
        print("source as sent successfully in to the server.")
        # server got the source
        # await self.assert_response_status(utils.Protocol.StatusCodes.success)
        # server successfully processed the source

    async def handle_connection(self, source: Source) -> str:
        try:
            print("attempting to connect to server...")
            await self.loop.sock_connect(self.socket, ("localhost", 6969))
            print("connected with the server.")
            print("attempting to authenticate with the server...")
            await self.authenticate()
            print("authenticated with the server.")
            print("attempting to send source to the server...")
            await self.handle_source(source)
            print("source was sent to the server.")
            print("awaiting result back from server...")
            response = await self.handle_stdout()
            print("response with result received.")
            return response
        except AssertionError as e:
            # unexpected status code was received
            print("sending close status to the server...")
            await self.loop.sock_sendall(self.socket, utils.Protocol.StatusCodes.close)
            print("close status sent to the server.")
            print("awaiting server to respond with success...")
            response = await self.loop.sock_recv(self.socket, utils.Protocol.buffer_size)
            if response == utils.Protocol.StatusCodes.success:
                print("successfully closed the connection.")
            else:
                print("something went wrong when closing the connection.")
            return "There was an unknown error processing the source"

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

