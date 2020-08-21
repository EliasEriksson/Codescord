import asyncio
from aionotify import Flags, Watcher
from pathlib import Path



class FileWatcher(Watcher):
    def __init__(self, root_path: Path, *ignored_directories: Path) -> None:
        super(FileWatcher, self).__init__()
        self.watch_descriptors_needed = 0
        self.setup_watcher(root_path, *ignored_directories)
        print(self.watch_descriptors_needed)

        with (path := Path("/proc/sys/fs/inotify")).joinpath("max_user_watches").open("r") as f:
            current_max_amount_of_wd = int(f.read(1))

        # without proper permissions code bellow will error with permissions denied. if True
        # try running code in subprocess instead and the user will be asked to provide password instead
        # if too many watch descriptors are needed increase the max cap
        if self.watch_descriptors_needed > current_max_amount_of_wd:
            with path.joinpath("max_user_watches").open("w") as f:
                f.write(str(self.watch_descriptors_needed + 1000))
            with path.joinpath("max_queued_events").open("w") as f:
                f.write(str((self.watch_descriptors_needed + 1000) // 4))
            with path.joinpath("max_user_instances").open("w") as f:
                f.write(str((self.watch_descriptors_needed + 1000) // 515))



    def setup_watcher(self, directory: Path, *ignored_directories: Path):
        try:
            flags = Flags.MODIFY | Flags.CREATE | Flags.DELETE | Flags.MOVED_FROM | Flags.ATTRIB | Flags.DONT_FOLLOW
            self.watch(str(directory), flags=flags)
            self.watch_descriptors_needed += 1
            for path in directory.iterdir():
                if path.is_dir() and not path.is_symlink():
                    if path not in ignored_directories:
                        self.setup_watcher(path, *ignored_directories)
        except PermissionError:
            pass


async def main(loop):
    watcher = FileWatcher(Path("/home/elias-eriksson"), Path("/home/elias-eriksson/Dev/Pyscord/ignore"))
    print("set up")
    await watcher.setup(loop)
    print("ready")
    while event := await watcher.get_event():
        print(event)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(loop))
    except KeyboardInterrupt:
        pass
