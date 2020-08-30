from typing import *
import asyncio
from pathlib import Path


async def subprocess(stdin: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *stdin.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


class Languages:
    @staticmethod
    async def cpp(file: Union[Path, str]) -> bytes:
        executable = "executable"
        process = await subprocess(f"g++ -o {file.parent.joinpath(executable)} {file}")
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            print(f"stderr1 {stderr}")
            return stderr

        process = await subprocess(f"{file.parent.joinpath(executable)}")
        stdout, stderr = await process.communicate()
        if not process.returncode == 0:
            print(f"stderr2 {stderr}")
            return stderr
        return stdout

    @staticmethod
    async def python(file: Union[Path, str]) -> bytes:
        process = await asyncio.create_subprocess_exec(
            "python3", file, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout
        return stderr

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


def get_language_map() -> Dict[str, Callable]:
    return {method_name: getattr(Languages, method_name)
            for method_name in dir(Languages)
            if not method_name.startswith("__")}


if __name__ == '__main__':
    print(get_language_map())
