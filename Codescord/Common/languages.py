from typing import *
import asyncio
from pathlib import Path
from uuid import uuid4


async def subprocess(stdin: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *stdin.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


class Languages:
    @staticmethod
    async def php(file: Union[Path, str], sys_args: str) -> bytes:
        process = await subprocess(f"php -f {file} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def java(file: Union[Path, str], sys_args: str) -> bytes:
        process = await subprocess(f"java {file} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def javascript(file: Union[Path, str], sys_args: str) -> bytes:
        process = await subprocess(f"node {file} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def go(file: Union[Path, str], sys_args: str) -> bytes:
        process = await subprocess(f"go run {file} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def cpp(file: Union[Path, str], sys_args: str) -> bytes:
        executable = file.parent.joinpath(str(uuid4()))
        process = await subprocess(f"g++ -o {executable} {file} {sys_args}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"{executable}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def cs(file: Union[Path, str], sys_args: str) -> bytes:
        cs_project = file.parent.joinpath("cs")

        process = await subprocess(f"dotnet new console --output {cs_project}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"mv {file} {cs_project.joinpath(file.name)}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"rm {cs_project.joinpath('Program.cs')}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"dotnet run --project {cs_project} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def python(file: Union[Path, str], sys_args: str) -> bytes:
        process = await subprocess(f"python3 {file} {sys_args}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def c(file: Union[Path, str], sys_args: str) -> bytes:
        executable = file.parent.joinpath(str(uuid4()))
        process = await subprocess(f"gcc -o {executable} {file} {sys_args}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"{executable}")
        stdout, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr
        return stdout


def get_language_map() -> Dict[str, Callable]:
    return {method_name: getattr(Languages, method_name)
            for method_name in dir(Languages)
            if not method_name.startswith("__")}


if __name__ == '__main__':
    print(get_language_map())
