import socket
import asyncio
from math import ceil
from .protocol import Protocol
from .errors import Errors


class Net:
    def __init__(self, loop=None) -> None:
        """
        initialises the client object with event loop and max retries for connection errors.

        :attr loop: the event loop
        :attr retries: amount of times to retry the connection if it dies.

        :param loop: the event loop
        """

        self.loop = loop if loop else asyncio.get_event_loop()

    async def response_as_int(self, connection: socket.socket, length=Protocol.buffer_size, endian="big", signed=False) -> int:
        """
        receive an integer from the server.

        mostly a convenience method to automatically convert received bytes to int.
        OBS! integer can not be larger than 1 byte.
        if necessary this can be changed by using the first section of the upload code

        :param length: buffer size.
        :param endian: big or little endian int.
        :param signed: singed or unsigned int
        :param connection: connection to the processing server

        :raises ConnectionError: if anything goes wrong with the connection (DCs etc).

        :return: None
        """
        print("awaiting response as int...")
        integer = int.from_bytes((await self.loop.sock_recv(connection, length)), endian, signed=signed)
        print(f"got response as int ({integer}).")
        return integer

    async def send_int_as_bytes(self, connection: socket.socket, integer: int, length=Protocol.buffer_size, endian="big", signed=False) -> None:
        """
        sends an integer to the recipient
        OBS! only 1 byte int supported

        :param connection: connection to the recipient.
        :param integer: integer to be sent.
        :param length: number of bytes (currently must be 1).
        :param endian: endianness.
        :param signed: signed or unsigned integer.
        :return: None
        """
        print(f"sending int ({integer}) as bytes...")
        await self.loop.sock_sendall(connection, integer.to_bytes(length, endian, signed=signed))
        print(f"sent int ({integer}) as bytes.")

    async def assert_response_status(self, connection: socket.socket, status=Protocol.Status.success) -> None:
        """
        makes sure the server response is the the same the client expects

        makes sure the server response as expected.
        raises the correct error if this is not the case.

        :param connection: connection to the server.
        :param status: the expected status code.

        :raises ConnectionError: if anything goes wrong with the connection (DCs etc).
        :raises NotImplementedByServer: if the instruction is not implemented by the server.
        :raises NotImplementedByClient: if the instruction is not implemented by the client.
        :raises InternalServerError:if the server can communicate but something goes wrong on the server side.

        :return: None
        """
        print(f"asserting response status ({status})...")
        response = await self.response_as_int(connection)
        if response == status:
            print(f"response passed assertion ({status}).")
        elif response == Protocol.Status.not_implemented:
            print(f"response was `{response}` (not implemented) expected `{status}`.")
            raise Errors.NotImplementedByServer()
        elif response == Protocol.Status.internal_server_error:
            print(f"response was `{response}` (internal server error) expected `{status}`.")
            raise Errors.InternalServerError()
        elif response not in [getattr(Protocol, attr) for attr in dir(Protocol.Status)]:
            print(f"response `{response}` does not exist in Protocol.")
            raise Errors.NotImplementedByClient(f"Could not find status {response} in Protocol.")
        else:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def download(self, connection: socket.socket) -> bytes:
        """
        downloads some byte blob from the server.


        used to download whats captured in stdout from the processed source
        as well as the protocol.

        :raises ConnectionError: if anything goes wrong with the connection (DCs etc)

        :param connection: connection to the processing server.
        :return: None
        """

        print("downloading...")
        # number of bytes required to store the size of the blob in an int
        bites = await self.response_as_int(connection)
        await self.send_int_as_bytes(connection, Protocol.Status.success)

        # size of the blob in number of bytes
        size = await self.response_as_int(connection, bites)
        await self.send_int_as_bytes(connection, Protocol.Status.success)

        # initialising blob and downloading from socket, blob will be `size` bytes
        blob = b""
        for _ in range(int(size / Protocol.max_buffer)):
            blob += await self.loop.sock_recv(connection, Protocol.max_buffer)
        blob += await self.loop.sock_recv(connection, (size % Protocol.max_buffer))
        print("downloaded.")
        return blob

    async def upload(self, connection: socket.socket, payload: bytes) -> None:
        """
        uploads some byte blob to the processing server

        used to upload files to the processing server.
        sends a 1 byte message about how many bytes that the integer representing the size of the upload is,
        then sends the integer representing the size of the upload.
        the byte blob is the uploaded for the processing server to download.

        :param connection: connection to the processing server.
        :param payload: the byte blob of data to be sent to the recipient.

        :raises ConnectionError: if anything goes wrong with the connection (DCs etc).
        :raises InternalServerError:if the server can communicate but something goes wrong on the server side.

        :return: None
        """
        print("uploading...")
        # size of the upload
        size = len(payload)

        # number of bytes required to receive the entire integer representing the size of the upload
        bites = ceil(size.bit_length() / 8)

        await self.send_int_as_bytes(connection, bites)
        await self.assert_response_status(connection, Protocol.Status.success)

        await self.send_int_as_bytes(connection, size, bites)
        await self.assert_response_status(connection, Protocol.Status.success)

        await self.loop.sock_sendall(connection, payload)
        await self.assert_response_status(connection, Protocol.Status.success)
        print("uploaded.")

    async def authenticate(self, connection: socket.socket) -> None:
        raise NotImplementedError()

    async def handle_connection(self, *_, **__) -> None:
        raise NotImplementedError()
