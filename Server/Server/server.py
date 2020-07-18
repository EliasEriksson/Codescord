from typing import *
import socket
import asyncio
import tempfile
from pathlib import Path


script_name = "script.py"


def setup_socket() -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 6969))
    sock.setblocking(False)
    sock.listen()
    return sock


class Server:
    def __init__(self, loop=None) -> None:
        self.socket = setup_socket()
        self.loop = loop if loop else asyncio.get_event_loop()

    def close(self) -> None:
        self.socket.close()

    @staticmethod
    async def run_script(script_path: Union[str, Path]) -> bytes:
        print(f"running {script_path} ...")
        process = await asyncio.create_subprocess_exec(
            "python3", script_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print("finished with no errors.")
            return stdout
        print("finished with errors.")
        return stderr

    async def send(self, connection: socket.socket, data: bytes) -> None:
        print("sending over the result to the client...")
        await self.loop.sock_sendall(connection, data)
        print("result sent.")

    async def receive_file(self, connection: socket.socket, script_path: Union[str, Path], size: int):
        received = 0
        with open(script_path, "wb") as script:
            while received < size:
                data = await self.loop.sock_recv(connection, 128)
                received += 128
                script.write(data)

    async def receive_action(self, connection: socket.socket) -> str:
        action = (await self.loop.sock_recv(connection, 128)).decode("utf-8")
        await self.loop.sock_sendall(connection, b"OK")
        return action

    async def handle_connection(self, connection: socket.socket) -> None:
        action = await self.receive_action(connection)
        if action:
            if action.startswith("file:"):
                _, size = action.split(":")
                with tempfile.TemporaryDirectory() as tempdir:
                    script_path = Path(tempdir).joinpath(script_name)
                    print("created environment for connection to live in.")
                    await self.receive_file(connection, script_path, int(size))
                    result = await self.run_script(script_path)
                print("connection environment no longer needed. deleting all related files.")
                await self.send(connection, result)

    async def accept_connection(self) -> None:
        print("awaiting connections...")
        connection, ip = await self.loop.sock_accept(self.socket)
        print(f"connection from {ip}")
        await self.handle_connection(connection)
        print("work finished closing connection")
        connection.close()

    async def run(self) -> None:
        try:
            print("server is open for connections.")
            while True:
                await self.accept_connection()
        except KeyboardInterrupt:
            self.close()
        print("closing the server.")


