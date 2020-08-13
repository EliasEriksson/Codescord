import socket
import asyncio
from math import ceil
import utils
from .errors import *


def setup_socket() -> socket.socket:
    """
    sets up a socket used by the client

    blocking must be false since used in async context
    :return: the clients socket used to connect to the processing server
    """
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Source:
    def __init__(self, language: str, code: str) -> None:
        self.language = language
        self.code = code


class Client:
    def __init__(self, loop=None) -> None:
        """
        initialises the client object with event loop and max retries for connection errors.

        :attr loop: the event loop
        :attr retries: amount of times to retry the connection if it dies.

        :param loop: the event loop
        """

        print("initializing...")
        self.loop = loop if loop else asyncio.get_event_loop()
        self.retries = 3
        print("initialized.")

    async def response_as_int(self, connection: socket.socket, length=utils.Protocol.buffer_size, endian="big", signed=False) -> int:
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

    async def send_int_as_bytes(self, connection: socket.socket, integer: int, length=utils.Protocol.buffer_size, endian="big", signed=False) -> None:
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

    async def assert_response_status(self, connection: socket.socket, status=utils.Protocol.Status.success) -> None:
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
        elif response == utils.Protocol.Status.not_implemented:
            print(f"response was `{response}` (not implemented) expected `{status}`.")
            raise NotImplementedByServer()
        elif response == utils.Protocol.Status.internal_server_error:
            print(f"response was `{response}` (internal server error) expected `{status}`.")
            raise InternalServerError()
        elif response not in [getattr(utils.Protocol, attr) for attr in dir(utils.Protocol.Status)]:
            print(f"response `{response}` does not exist in Protocol.")
            raise NotImplementedByClient(f"Could not find status {response} in Protocol.")
        else:
            raise AssertionError(f"expected status: {status}, got: {response} instead.")

    async def download(self, connection: socket.socket) -> bytes:
        """
        downloads some byte blob from the server.

        used to download whats captured in stdout from the processed source.

        :raises ConnectionError: if anything goes wrong with the connection (DCs etc)

        :param connection: connection to the processing server.
        :return: None
        """

        print("downloading...")
        # number of bytes required to store the size of the blob in an int
        bites = await self.response_as_int(connection)
        await self.send_int_as_bytes(connection, utils.Protocol.Status.success)

        # size of the blob in number of bytes
        size = await self.response_as_int(connection, bites)
        await self.send_int_as_bytes(connection, utils.Protocol.Status.success)

        # initialising blob and downloading from socket, blob will be `size` bytes
        blob = b""
        for _ in range(int(size / utils.Protocol.max_buffer)):
            blob += await self.loop.sock_recv(connection, utils.Protocol.max_buffer)
        blob += await self.loop.sock_recv(connection, (size % utils.Protocol.max_buffer))
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
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        await self.send_int_as_bytes(connection, size, bites)
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        await self.loop.sock_sendall(connection, payload)
        await self.assert_response_status(connection, utils.Protocol.Status.success)
        print("uploaded.")

    async def authenticate(self, connection: socket.socket,) -> None:
        """
        authenticates the protocol that is used by the client and server

        by authenticating the protocol the client sends the protocol to the server
        and the server will compare and verify it. if the protocols match the process can go on

        if server denies verification NotImplementedByServer is raised to indicate the protocols are not the same
        if something else goes wrong on server side InternalServerError is raised

        :param connection: the connection to the processing server

        :raises NotImplementedByServer: if the instruction is not implemented by the server.
        :raises InternalServerError: if the server can communicate but something goes wrong on the other side.
        :raises ConnectionError: if any sort of connection error occurs.

        :return: None
        """
        print("authenticating...")
        await self.send_int_as_bytes(connection, utils.Protocol.Status.authenticate)
        await self.assert_response_status(connection)

        payload = utils.Protocol.get_protocol().encode("utf-8")
        await self.upload(connection, payload)
        print("authenticated.")

    async def handle_source(self, connection: socket.socket, source: Source) -> None:
        """
        handles the sending of the source file

        attempts to send the source file to the processing server

        if anything goes wrong InternalServerError is raised

        :raises InternalServerError: if the server can communicate but something goes wrong on the other side.
        :raises ConnectionError: if any sort of connection error occurs.

        :param connection: the connection to the processing server.
        :param source: source object with language and source code
        :return: None
        """
        print("handling the source...")
        await self.send_int_as_bytes(connection, utils.Protocol.Status.file)
        await self.assert_response_status(connection, utils.Protocol.Status.success)

        payload = source.language.encode("utf-8")
        await self.upload(connection, payload)

        payload = source.code.encode("utf-8")
        await self.upload(connection, payload)
        print("source handled.")

    async def handle_stdout(self, connection: socket.socket) -> str:
        """
        handles the receiving of the stdout from the server when processing the source file.

        awaits the server to respond with a message if message is a text message the
        source files produced stdout will be downloaded from the processing server.

        if message is not a text message NotImplementedByClient is raised.

        :raises: NotImplementedByClient
        :return:
        """
        print("handling stdout...")
        response = await self.response_as_int(connection)
        if response == utils.Protocol.Status.text:
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            blob = await self.download(connection)
            await self.send_int_as_bytes(connection, utils.Protocol.Status.success)
            print("stdout handled.")
            return blob.decode("utf-8")
        else:
            await self.send_int_as_bytes(connection, utils.Protocol.Status.not_implemented)
            raise NotImplementedByClient(f"handle_stdout cant handle {response}")

    async def handle_connection(self, connection: socket.socket, source: Source) -> str:
        """
        the main procedure of the processing of the source.

        makes sure the client and server authenticates before proceeding.
        sends the source to the processing server.
        waits for the processing server to send results back, times out after 30 seconds.
        downloads the results and returns them.

        :param connection: the connection to the processing server.
        :param source: source object with language and source code.

        :raises ConnectionError: if any sort of connection error occurs.

        :return: None
        """
        print("handling the connection...")
        try:
            await self.authenticate(connection)
            await self.handle_source(connection, source)

            await self.send_int_as_bytes(connection, utils.Protocol.Status.awaiting)
            stdout = await self.handle_stdout(connection)
            await self.assert_response_status(connection, utils.Protocol.Status.awaiting)

            print("client starting to send close")
            await self.send_int_as_bytes(connection, utils.Protocol.Status.close)
            await self.assert_response_status(connection, utils.Protocol.Status.success)

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

        connection = setup_socket()
        try:
            await self.loop.sock_connect(connection, ("localhost", 6969))
            stdout = await self.handle_connection(connection, source)
            return stdout if stdout else "There was an error processing the source."
        except KeyboardInterrupt:
            pass
        except ConnectionError as e:
            if attempts < self.retries:
                print(e)
                print(f"connection was refused retrying with attempts number {attempts}.")
                await asyncio.sleep(3)
                return await self.process(source, attempts + 1, False)
            return f"Processing server down. Please try again later."
        finally:
            # this runs 3 times in a row if full connectionError is happening
            if init:
                connection.close()
