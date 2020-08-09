from typing import *
import asyncio
from pathlib import Path


class Languages:
    @staticmethod
    async def cpp(file: Union[Path, str]) -> bytes:
        executable = "executable"
        process = await asyncio.create_subprocess_exec(
            "g++", "-o", file.parent.joinpath(executable), file,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if not process.returncode == 0:
            print(f"stderr1 {stderr}")
            return stderr

        process = await asyncio.create_subprocess_exec(
            file.parent.joinpath(executable),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
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
