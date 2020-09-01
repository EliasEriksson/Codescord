from typing import *
import asyncio
from pathlib import Path


async def subprocess(stdin: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *stdin.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


class Languages:
    @staticmethod
    async def javascript(file: Union[Path, str]) -> bytes:
        process = await subprocess(f"node {file}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def go(file: Union[Path, str]) -> bytes:
        process = await subprocess(f"go run {file}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def cpp(file: Union[Path, str]) -> bytes:
        executable = "executable"
        process = await subprocess(f"g++ -o {file.parent.joinpath(executable)} {file}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"{file.parent.joinpath(executable)}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def python(file: Union[Path, str]) -> bytes:
        process = await subprocess(f"python3 {file}")
        stdout, stderr = await process.communicate()
        return stdout if process.returncode == 0 else stderr

    @staticmethod
    async def c(file: Union[Path, str]) -> bytes:
        executable = "executable"
        process = await subprocess(f"gcc -o {file.parent.joinpath(executable)} {file}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr

        process = await subprocess(f"{file.parent.joinpath(executable)}")
        stdout, stderr = await process.communicate()
        if not process.returncode == 0:
            return stderr
        return stdout


def get_language_map() -> Dict[str, Callable[[Union[Path, str]], bytes]]:
    return {method_name: getattr(Languages, method_name)
            for method_name in dir(Languages)
            if not method_name.startswith("__")}


if __name__ == '__main__':
    print(get_language_map())
