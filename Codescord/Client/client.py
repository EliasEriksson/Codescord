from typing import Optional, List, Tuple, Callable, Awaitable, Set
from ..Common.net import Net
from ..Common.errors import Errors
from ..Common.protocol import Protocol
from ..Common.source import Source
import socket
import asyncio
from uuid import uuid4
from functools import partial


async def subprocess(stdin: str) -> Tuple[bool, str]:
    """
    easier wrapper around asyncio.create_subprocess_exec

    :param stdin: command to execute in subprocess
    :return: result from subprocess
    """
    process = await asyncio.create_subprocess_exec(
        *stdin.split(" "), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if not stdout:
        print(f"failed with '{stdin}'")
        return False, stderr.decode("utf-8")
    print(f"succeeded with '{stdin}'")
    return True, stdout.decode("utf-8")


def setup_socket() -> socket.socket:
    """
    sets up a socket used by the client.

    blocking must be false since used in async context.
    :return: the clients socket used to connect to the processing server.
    """
    sock = socket.socket()
    sock.setblocking(False)
    return sock


class QueuedPool:
    """
    a processing pool with first in first out queue to entry.

    this functions acts as a bottle neck depending on the amount of ports available for
    this program specified with -p option when running main.py.

    this pool will continuously look for processes that have been added to the internal queue
    if there is a port available for a container to start the process it will be put in a pending state.
    once the process is finished the port will be released and the process will be removed from its pending
    state freeing up another spot for another process to be queued.
    """
    def __init__(self, start_port: int, end_port: int = None, loop: asyncio.AbstractEventLoop = None) -> None:
        """
        initializes the QueuedPool and starts trying to process the queue.

        the difference between start_port and end_port + 1 will be the size of the processing pool
        as that is the amount of ports freely availeble.

        :param start_port: start of the port range.
        :param end_port: end of the port range.
        :param loop: asyncio event loop.

        :attr loop: asyncio event loop.
        :attr start_port: start of the port range.
        :attr end_port: end of the port range.
        :attr size: amount of ports availeble as well as the process pool size.
        :attr used_ports: ports currently in use by docker containers.
        :attr used_ids: ids (names) of the currently running docker containers.
        :attr queue: the queue waiting to get into the pending queue
        :attr pending: currently run processes.
        """
        self.loop = loop
        self.start_port = start_port
        self.end_port = end_port if end_port else start_port
        self.size = self.end_port - self.start_port + 1
        assert self.start_port <= self.end_port

        self.used_ports: Set[int] = set()
        self.used_ids: Set[str] = set()
        self.queue: List[Tuple[asyncio.Future, Callable[[Tuple[str, int]], Awaitable[str]]]] = []
        self.pending: Set[asyncio.Task] = set()

        self.loop.create_task(self._process_queue())

    @staticmethod
    async def pass_gil() -> None:
        """
        forces the task to sleep and pass the GIL to next task.

        :return: None
        """
        await asyncio.sleep(0.01)

    @staticmethod
    async def start_container(uuid: str, port: int) -> None:
        """
        starts a docker container with provided id and port.

        :param port: local port to expose to the container.
        :param uuid: container id.
        :return: None
        """
        success, stdout = await subprocess(
            f"sudo docker run -d -p {port}:{6090} --name {uuid} codescord")
        if not success:
            raise Errors.ContainerStartupError(stdout)

    @staticmethod
    async def stop_container(uuid: str) -> None:
        """
        stops a docker container with some id.

        :param uuid: container id.
        :return: None
        """
        success, stdout = await subprocess(
            f"sudo docker stop {uuid}")
        if not success:
            raise Errors.ContainerStopError(stdout)

        success, stdout = await subprocess(
            f"sudo docker rm {uuid}")

        if not success:
            raise Errors.ContainerRmError(stdout)

    async def schedule_process(self, process: Callable[[Tuple[str, int]], Awaitable[str]]) -> str:
        """
        main way to schedule a process. the process (coroutine) should ultimately return a string.

        :param process: callable coroutine with partial args.
        :return: result from the process.
        """
        future = self.loop.create_future()
        self.queue.append((future, process))
        await future
        return future.result()

    async def get_port(self) -> int:
        """
        generates a free port for use.

        looks for a free port, if none availeble it waits for one to be free.

        :return: port
        """
        if self.end_port:
            while True:
                for port in range(self.start_port, self.end_port + 1):
                    if port not in self.used_ports:
                        self.used_ports.add(port)
                        return port
                await self.pass_gil()
        else:
            port = self.start_port
            while True:
                if port not in self.used_ports:
                    self.used_ports.add(port)
                    return port
                port += 1
                if port > 0xFFFF:  # 65535 in hex, maximum amount of ports available
                    port = self.start_port
                await self.pass_gil()

    def get_id(self) -> str:
        """
        generates a new free id for a container.

        :return: uuid
        """
        while True:
            uuid = str(uuid4())
            if uuid not in self.used_ids:
                self.used_ids.add(uuid)
                return uuid

    async def _process_queue(self) -> None:
        """
        a forever running loop to put queued items up for execution once there is space in the queue.

        this loop is called in the init method

        if there is a spot in the processing queue self.pending and there are processes queued
        in self.queue an id and port is generated for a new process followed by execution of the process.
        when the process is done some cleanup is done to free resources.

        if there are no processes to add to the queue the gil will be passed onto some other task by sleeping here.

        :return: None
        """
        while True:
            if len(self.pending) < self.size:
                if self.queue:
                    uuid = self.get_id()
                    port = await self.get_port()
                    process = asyncio.create_task(self.process(uuid, port))
                    asyncio.create_task(self.cleanup(uuid, port, process))
                    self.pending.add(process)
            await self.pass_gil()

    async def process(self, uuid: str, port: int) -> None:
        """
        pops off the next process from the waiting queue to start processing.

        starts the docker container with given uuid and port and starts the process
        of connecting to the server inside. waits for a little bit to let the container start.
        once its done processing the result is set on the future objects so the process can continue in
        cleanup.

        :param uuid: uuid for the docker container.
        :param port: port for the docker container.

        :return: None
        """
        future, process = self.queue.pop(0)
        await self.start_container(uuid, port)
        await asyncio.sleep(0.45)  # wait a little for the container to start
        result = await process(("localhost", port))

        future.set_result(result)

    async def cleanup(self, uuid: str, port: int, process: asyncio.Task) -> None:
        """
        cleans up resource usage from the task whenever its done running.

        waits for the process to finish as well as
        the docker container to close before freeing the uuid, port for further use as well as
        freeing a spot in the process pool of pending processes

        :param uuid: container uuid
        :param port: port that is/was used by the container
        :param process: the process connecting into the docker container
        :return: None
        """
        await process
        freeing_port = asyncio.create_task(self.stop_container(uuid))
        await freeing_port
        self.used_ids.remove(uuid)
        self.used_ports.remove(port)
        self.pending.remove(process)


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
    def __init__(self, start_port: int, end_port: Optional[int], loop: asyncio.AbstractEventLoop = None) -> None:
        """

        :param start_port: start of the port range
        :param end_port: end of the port range
        :param loop: asyncio event loop
        """
        super(Client, self).__init__(loop)
        self.pool = QueuedPool(start_port, end_port, loop)
        self.retries = 5

    async def authenticate(self, connection: socket.socket) -> None:
        """
        authenticates the protocol that is used by the client and server.

        by authenticating the protocol the client sends the protocol to the server.
        and the server will compare and verify it. if the protocols match the process can go on.

        :param connection: the connection to the processing server.

        :return: None
        """
        print("authenticating...")
        await self.send_int_as_bytes(connection, Protocol.Status.authenticate)
        await self.assert_response_status(connection)

        payload = Protocol.get_protocol().encode("utf-8")
        await self.upload(connection, payload)
        print("authenticated.")

    async def upload_source(self, connection: socket.socket, source: Source) -> None:
        """
        handles the sending of the source file.

        attempts to send the source file to the processing server.

        :param connection: the connection to the processing server.
        :param source: source object with language and source code.
        :return: None
        """
        print("handling the source...")
        await self.send_int_as_bytes(connection, Protocol.Status.file)
        await self.assert_response_status(connection, Protocol.Status.success)

        print(source)
        print("uploading the language payload...")
        payload = source.language.encode("utf-8")
        await self.upload(connection, payload)
        print("uploaded the language payload.")

        print("uploading the code payload...")
        payload = source.code.encode("utf-8")
        await self.upload(connection, payload)
        print("uploaded the code payload.")

        print()
        payload = source.sys_args.encode("utf-8")
        await self.upload(connection, payload)
        print("source handled.")

    async def download_stdout(self, connection: socket.socket) -> str:
        """
        handles the receiving of the stdout from the server when processing the source file.

        awaits the server to respond with a message if message is a text message the
        source files produced stdout will be downloaded from the processing server.

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
            await self.upload_source(connection, source)

            await self.send_int_as_bytes(connection, Protocol.Status.awaiting)
            stdout = await self.download_stdout(connection)
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

    async def schedule_process(self, source: Source) -> str:
        """
        the preferred way of sending a processing request to a server in a docker container.

        :param source: source code to send.
        :return: the result from processing.
        """
        process = partial(self.process, source)
        return await self.pool.schedule_process(process)

    async def process(self, source: Source, address: Tuple[str, int], attempts=0) -> str:
        """
        processes a source object on the processing server.

        can, but should not be called outside of schedule_process as it sets everything automatically

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
            return stdout
        except KeyboardInterrupt:
            print(self.loop.is_closed())
        except (ConnectionRefusedError, ConnectionResetError):
            if attempts == 0:
                print("server have probably not started yet, retrying...")
                await asyncio.sleep(0.1)
                return await self.process(source, address, attempts + 1)
            else:
                return await self.process(source, address, attempts + 1)
        except (ConnectionAbortedError, BrokenPipeError) as e:
            connection.close()
            if attempts < self.retries:
                print(e)
                print(f"connection was refused retrying with attempts number {attempts}.")
                await asyncio.sleep(0.5)
                return await self.process(source, address, attempts + 1)
            return f"Processing server down. Please try again later."
