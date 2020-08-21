from ..Common.net import Net
from ..Common.errors import Errors
from ..Common.protocol import Protocol
from ..Common.languages import Languages
import socket
import asyncio
from pathlib import Path
import tempfile


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 6969))
    sock.setblocking(False)
    sock.listen()
    return sock


class Server(Net):
    def __init__(self, loop=None):
        super(Server, self).__init__(loop)
        self.socket = setup_socket()

        self.instructions = {
            Protocol.Status.authenticate: self.authenticate,
            Protocol.Status.file: self.handle_file,
        }
        self.languages = {
            "python": Languages.python,
            # "py": Languages.python,

            "cpp": Languages.cpp,
            "c++": Languages.cpp,
        }

    async def authenticate(self, connection: socket.socket) -> None:
        """
        authenticates the protocol that is used the client and server

        by authenticating the protocol the client sends the protocol to the server
        and the server will compare and verify it. if the protocols match the process can go on

        if server denies verification NotImplementedByServer is raised to indicate the protocols are not the same
        if something else goes wrong on server side InternalServerError is raised

        :param connection: the connection to the processing server

        :raises ConnectionError: if any sort of connection error occurs.

        :return: None
        """
        print("authenticating...")
        protocol = await self.download(connection)
        if protocol == Protocol.get_protocol().encode("utf-8"):
            await self.send_int_as_bytes(connection, Protocol.Status.success)
            print("authenticated.")
        else:
            await self.send_int_as_bytes(connection, Protocol.Status.not_implemented)
            raise Errors.NotImplementedInProtocol()

    async def handle_file(self, connection: socket.socket) -> None:
        """
        handles the downloading and execution of a source file

        first downloads the language from the client and sees if its a supported language.
        if it is the language source is downloaded.
        the source is then saved to a file in a tempdir and executed with
        procedures from Codescord.Common.Languages.
        the standard out is captured and sent back to the client.

        :param connection: the connection to the processing server.
        :return: None
        """
        print("handling file...")
        language = (await self.download(connection)).decode("utf-8")
        if language in self.languages:
            await self.send_int_as_bytes(connection, Protocol.Status.success)
            code = await self.download(connection)
            await self.send_int_as_bytes(connection, Protocol.Status.success)
            await self.assert_response_status(connection, Protocol.Status.awaiting)

            with tempfile.TemporaryDirectory() as tempdir:
                file = Path(tempdir).joinpath(f"script.{language}")
                with open(file, "wb") as script:
                    script.write(code)
                try:
                    stdout = await asyncio.wait_for(self.languages[language](file), Protocol.timeout)
                except asyncio.TimeoutError:
                    await self.send_int_as_bytes(connection, Protocol.Status.process_timeout)
                    raise Errors.ProcessTimedOut(f"process took longer than {Protocol.timeout}")

            await self.send_int_as_bytes(connection, Protocol.Status.text)
            await self.assert_response_status(connection, Protocol.Status.success)

            await self.upload(connection, stdout)
            await self.send_int_as_bytes(connection, Protocol.Status.awaiting)
            print("file handled.")
        else:
            await self.send_int_as_bytes(connection, Protocol.Status.not_implemented)
            raise Errors.LanguageNotImplementedByServer(language)

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
            while (response := await self.response_as_int(connection)) != Protocol.Status.close:
                if response in self.instructions:
                    await self.send_int_as_bytes(connection, Protocol.Status.success)
                    # noinspection PyArgumentList
                    await self.instructions[response](connection)
                else:
                    await self.send_int_as_bytes(connection, Protocol.Status.not_implemented)
            await self.send_int_as_bytes(connection, Protocol.Status.success)
            print("connection handled.")
        except Errors.ProcessTimedOut:
            print(f"process took longer than {Protocol.timeout}s.")
        except Errors.LanguageNotImplementedByServer as e:
            print(f"language {e} is not implemented on the server.")
        except Errors.NotImplementedByRecipient as e:
            print(f"{e} was not implemented on the client.")
        except Errors.NotImplementedInProtocol as e:
            print(f"{e} is not implemented in clients protocol.")
        except Exception as e:
            await self.send_int_as_bytes(connection, Protocol.Status.internal_server_error)
            raise e
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
        except ConnectionError:
            print("Client disconnected.")
        except KeyboardInterrupt:
            pass
        finally:
            self.socket.close()