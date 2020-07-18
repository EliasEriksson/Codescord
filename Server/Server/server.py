from typing import *
import socket
import asyncio
import tempfile
from pathlib import Path
from math import ceil
from .errors import ProcessTimedOut


script_name = "script.py"


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 6969))
    sock.setblocking(False)
    sock.listen()
    return sock


class Server:
    FAILURE = b"0"
    SUCCESS = b"1"
    BUFFER_SIZE = 128

    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.actions = {
            "file": self.handle_file,
        }

    def close(self) -> None:
        self.socket.close()

    @staticmethod
    async def run_script(script_path: Union[str, Path]) -> bytes:
        process = await asyncio.create_subprocess_exec(
            "python3", script_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout
        return stderr

    async def send_action(self, connection: socket.socket, action: str) -> bool:
        await self.loop.sock_sendall(connection, action.encode("utf-8"))
        status = await self.loop.sock_recv(connection, self.BUFFER_SIZE)
        if status == self.SUCCESS:
            return True
        return False

    async def send(self, connection: socket.socket, data: bytes) -> None:
        if await self.send_action(connection, f"stdout:{len(data)}"):
            await self.loop.sock_sendall(connection, data)

    async def receive_file(self, connection: socket.socket, script_path: Union[str, Path], size: int):
        with open(script_path, "wb") as script:
            for _ in range(ceil(size / self.BUFFER_SIZE)):
                script.write((await self.loop.sock_recv(connection, self.BUFFER_SIZE)))

    async def handle_file(self, connection: socket.socket, action_args: Tuple[str]):
        size = int(*action_args)
        with tempfile.TemporaryDirectory() as tempdir:
            script_path = Path(tempdir).joinpath(script_name)
            await self.receive_file(connection, script_path, size)
            try:
                result = await asyncio.wait_for(self.run_script(script_path), 30)
            except asyncio.TimeoutError:
                raise ProcessTimedOut()
        await self.send(connection, result)

    async def receive_action(self, connection: socket.socket) -> str:
        action = (await self.loop.sock_recv(connection, self.BUFFER_SIZE)).decode("utf-8")
        await self.loop.sock_sendall(connection, self.SUCCESS)
        return action

    async def handle_connection(self, connection: socket.socket) -> None:
        action, *args = (await self.receive_action(connection)).split(":")
        if action in self.actions:
            await self.actions[action](connection, args)

    async def accept_connection(self) -> None:
        connection, _ = await self.loop.sock_accept(self.socket)
        await self.handle_connection(connection)
        connection.close()

    async def run(self) -> None:
        try:
            print("server is open for connections.")
            while True:
                await self.accept_connection()
        except KeyboardInterrupt:
            self.close()
        print("closing the server.")


