from typing import Tuple
from ..Common.net import Net
from ..Common.errors import Errors
from ..Common.protocol import Protocol
from ..Common.source import Source
import socket
import asyncio


def setup_socket() -> socket.socket:
    """
    sets up a socket used by the client.

    blocking must be false since used in async context.
    :return: the clients socket used to connect to the processing server.
    """
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class Client(Net):
    """
    this client will be what Discord.Client uses to send source code to the Codescord.Server.
    the Discord.Client will have one instance of this client.
    this client will attempts to make a conenction to a Codescord.Server inside of a docker container
    when Codescord.Client.process is called.

    this client will then attempt to:
    authenticate with the server,
    send the source code to the server,
    receive the stdout from the server
    and then close the connection.
    """
    def __init__(self, loop=None) -> None:
        super(Client, self).__init__(loop)
        self.retries = 5

    async def authenticate(self, connection: socket.socket) -> None:
        """
        authenticates the protocol that is used by the client and server.

        by authenticating the protocol the client sends the protocol to the server.
        and the server will compare and verify it. if the protocols match the process can go on.

        if server denies verification NotImplementedByServer is raised to indicate the protocols are not the same.
        if something else goes wrong on server side InternalServerError is raised.

        :param connection: the connection to the processing server.

        :return: None
        """
        print("authenticating...")
        await self.send_int_as_bytes(connection, Protocol.Status.authenticate)
        await self.assert_response_status(connection)

        payload = Protocol.get_protocol().encode("utf-8")
        await self.upload(connection, payload)
        print("authenticated.")

    async def handle_source(self, connection: socket.socket, source: Source) -> None:
        """
        handles the sending of the source file.

        attempts to send the source file to the processing server.

        :raises InternalServerError: if the server can communicate but something goes wrong on the other side.
        :raises ConnectionError: if any sort of connection error occurs.

        :param connection: the connection to the processing server.
        :param source: source object with language and source code.
        :return: None
        """
        print("handling the source...")
        await self.send_int_as_bytes(connection, Protocol.Status.file)
        await self.assert_response_status(connection, Protocol.Status.success)

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

        :return: stdout from the processing server.
        """
        print("handling stdout...")
        await self.assert_response_status(connection, Protocol.Status.text)
        await self.send_int_as_bytes(connection, Protocol.Status.success)

        blob = await self.download(connection)
        await self.send_int_as_bytes(connection, Protocol.Status.success)

        print("stdout handled.")
        return blob.decode("utf-8")

    async def handle_connection(self, connection: socket.socket, source: Source) -> str:
        """
        the main procedure of the processing of the source.

        makes sure the client and server authenticates before proceeding.
        sends the source to the processing server.
        waits for the processing server to send results back, times out after 30 seconds.
        downloads the results and returns them.

        :param connection: the connection to the processing server.
        :param source: source object with language and source code.

        :return: None
        """
        print("handling the connection...")
        try:
            await self.authenticate(connection)
            await self.handle_source(connection, source)

            await self.send_int_as_bytes(connection, Protocol.Status.awaiting)
            stdout = await self.handle_stdout(connection)
            await self.assert_response_status(connection, Protocol.Status.awaiting)

            print("client starting to send close")
            await self.send_int_as_bytes(connection, Protocol.Status.close)
            await self.assert_response_status(connection, Protocol.Status.success)

            print("connection handled.")
            return stdout
        except Errors.ProcessTimedOut:
            print(f"process took longer than {Protocol.timeout}s.")
        except Errors.LanguageNotImplementedByServer as e:
            print(f"language {e} is not implemented on the server.")
        except Errors.NotImplementedByRecipient as e:
            print(f"{e} was not implemented on the server.")
        except Errors.NotImplementedInProtocol as e:
            print(f"{e} is not implemented in the servers protocol.")
        finally:
            connection.close()

    async def process(self, source: Source, address: Tuple[str, int], attempts=0) -> str:
        """
        processes a source object on the processing server.

        starts the process of sending over the source object to the server to process
        and receiving the result back from stdout.

        :param source: source object with language and source code.
        :param attempts: how many attempts of reconnecting that have been done (max limit in self.retries).
        :param address: ip address with port to connect to.

        :return: the result from processing.
        """

        connection = setup_socket()
        try:
            print(f"connecting to {address}...")
            await self.loop.sock_connect(connection, address)
            print(f"connected to {address}.")
            stdout = await self.handle_connection(connection, source)
            return stdout if stdout else "There was an error processing the source."
        except KeyboardInterrupt:
            print(self.loop.is_closed())
        except (ConnectionRefusedError, ConnectionResetError):
            if attempts == 0:
                print("server have probably not started yet, retrying...")
                await asyncio.sleep(0.45)
                return await self.process(source, address, attempts + 1)
            else:
                return await self.process(source, address, attempts + 1)
        except (ConnectionAbortedError, BrokenPipeError) as e:
            connection.close()
            if attempts < self.retries:
                print(e)
                print(f"connection was refused retrying with attempts number {attempts}.")
                await asyncio.sleep(3)
                return await self.process(source, address, attempts + 1)
            return f"Processing server down. Please try again later."

