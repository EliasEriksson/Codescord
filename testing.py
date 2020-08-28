stdout = """CONTAINER ID        IMAGE               COMMAND                  CREATED              STATUS                       PORTS                    NAMES
6aa6c2b8c0cb        codescord           "python main.py serv…"   About a minute ago   Exited (137) 6 seconds ago                            manual2
a147ec32f587        codescord           "python main.py serv…"   2 minutes ago        Up 2 minutes                 0.0.0.0:6090->6090/tcp   manual"""

for line in stdout.split("\n"):
    if "codescord" in line:
        name = line.split()[-1]
        print(name)

