from typing import *
import socket
import asyncio
from math import ceil
import utils
from .errors import *


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
        self.retries = 3
        print("initialized.")

    def close(self) -> None:
        print("closing...")
        self.socket.close()
        self.socket = setup_socket()
        print("closed.")

    async def response_as_int(self, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
        print("SLEEPING")
        integer = int.from_bytes((await self.loop.sock_recv(self.socket, length)), endian, signed=signed)
        print(f"\tgot response as int ({integer}).")
        return integer

    async def send_int_as_bytes(self, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
        print(f"sending int ({integer}) as bytes...")
        await self.loop.sock_sendall(self.socket, integer.to_bytes(length, endian, signed=signed))
        print(f"sent int ({integer}) as bytes.")

    async def assert_response_status(self, status=utils.Protocol.Status.success) -> None:
        print(f"\tasserting response status ({status})...")
        response = await self.response_as_int()
        if response == status:
            print(f"\tresponse passed assertion ({status}).")
        elif response == utils.Protocol.Status.not_implemented:
            print(f"\tresponse was `{response}` (not implemented) expected `{status}`.")
            raise NotImplementedByServer()
        elif response == utils.Protocol.Status.internal_server_error:
            print(f"\tresponse was `{response}` (internal server error) expected `{status}`.")
            raise InternalServerError()
        elif response not in [getattr(utils.Protocol, attr) for attr in dir(utils.Protocol.Status)]:
            print(f"response `{response}` does not exist in Protocol.")
            raise NotImplementedByClient(f"Could not find status {response} in Protocol.")
        else:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def send_size(self, size: int, endian="big", signed=False) -> None:
        print("sending size...")
        # number of bytes required to store the size in an int
        bites = ceil(size.bit_length() / 8)
        await self.send_int_as_bytes(bites, endian=endian, signed=signed)
        await self.assert_response_status(utils.Protocol.Status.success)

        await self.send_int_as_bytes(size, bites)
        await self.assert_response_status(utils.Protocol.Status.success)
        print("sent size.")

    async def download(self) -> bytes:
        print("downloading...")
        # number of bytes required to store the size of the blob in an int
        bites = await self.response_as_int()
        await self.send_int_as_bytes(utils.Protocol.Status.success)

        # size of the blob in number of bytes
        size = await self.response_as_int(bites)
        await self.send_int_as_bytes(utils.Protocol.Status.success)

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
        await self.assert_response_status(utils.Protocol.Status.success)
        print("uploaded.")

    async def authenticate(self) -> None:
        print("authenticating...")
        await self.send_int_as_bytes(utils.Protocol.Status.authenticate)
        await self.assert_response_status(utils.Protocol.Status.success, )

        payload = utils.Protocol.get_protocol().encode("utf-8")
        await self.upload(payload)
        print("authenticated.")

    async def handle_source(self, source: Source) -> None:
        print("handling the source...")

        await self.send_int_as_bytes(utils.Protocol.Status.file)
        await self.assert_response_status(utils.Protocol.Status.success)

        payload = source.language.encode("utf-8")
        await self.upload(payload)

        payload = source.code.encode("utf-8")
        await self.upload(payload)
        print("source handled.")

    async def handle_stdout(self) -> str:
        print("handling stdout...")
        response = await self.response_as_int()
        if response == utils.Protocol.Status.text:
            await self.send_int_as_bytes(utils.Protocol.Status.success)
            blob = await self.download()
            await self.send_int_as_bytes(utils.Protocol.Status.success)
            print("stdout handled.")
            return blob.decode("utf-8")
        raise NotImplementedByClient(f"handle_stdout cant handle {response}")

    async def handle_connection(self, source: Source) -> str:
        print("handling the connection...")
        try:
            await self.authenticate()
            await self.handle_source(source)

            await self.send_int_as_bytes(utils.Protocol.Status.awaiting)
            stdout = await self.handle_stdout()
            await self.assert_response_status(utils.Protocol.Status.awaiting)

            print("client starting to send close")
            await self.send_int_as_bytes(utils.Protocol.Status.close)
            await self.assert_response_status(utils.Protocol.Status.success)

            print("connection handled.")
            return stdout
        except InternalServerError:
            return f"something went wrong internally on the server, please contact developer for update."
        except (NotImplementedByServer, NotImplementedByClient):
            return f"client protocol out of sync with server, please contact developer for update."

    async def process(self, source: Source, attempts=0, init=True) -> str:
        """
        processes a source object on the processing server

        starts the process of sending over the source object to the server to process
        and receiving the result back from stdout

        :param source: source object with language and source code
        :param attempts: how many attempts of reconnecting that have been done (max limit in self.retries)
        :param init: if initial call, makes sure it doesnt spam self.close() if all connection tries fails
        :return:
        """
        try:
            await self.loop.sock_connect(self.socket, ("localhost", 6969))
            stdout = await self.handle_connection(source)
            return stdout if stdout else "There was an error processing the source."
        except KeyboardInterrupt:
            pass
        except ConnectionError as e:
            if attempts < self.retries:
                print(e)
                print(f"connection was refused retrying with attempts number {attempts}.")
                await asyncio.sleep(1)
                return await self.process(source, attempts + 1, False)
            return f"Processing server down. Please try again later."
        finally:
            # this runs 3 times in a row if full connectionError is happening
            if init:
                self.close()
                print("disconnected.")
