# Pyscord

requires python3.8+\
python packages:
* discord.py
* tortoise-orm
* aiosqlite
* aionotify

docker (https://docs.docker.com/get-docker/)

## To Run
1. `git clone https://github.com/EliasEriksson/Codescord.git`
2. `cd Codescord`
3. `python3.x -m venv venv`
4. `source ven/bin/activate`
5. `python -m pip install -r requirements.txt`
6. `sudo venv/bin/python main.py build-docker-image`
7. `python main.py create-database`
