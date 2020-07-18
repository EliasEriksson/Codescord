import tempfile
from pathlib import Path, PosixPath
import subprocess


with tempfile.TemporaryDirectory() as tempdir:
    script_path = Path(tempdir).joinpath("script.py")
    with open(script_path, "wb") as script:
        script.write(b'print("hello world!")\n')
    result = subprocess.run(["python3", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        print("success!")
        print(result.stdout.decode("utf-8"))
    else:
        print("Crash!")
        print(result.stderr.decode("utf-8"))
    print(script_path)

