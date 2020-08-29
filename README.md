# Codescord

requires python3.8+\
python packages:
* discord.py
* tortoise-orm
* aiosqlite

docker (https://docs.docker.com/get-docker/)

make sure localhost is allowed to go thru ports 6090:6120+ (one port per possible container, 
30 ports = 30 concurrent connections).

## Discord invite
discord [invite link](https://discord.com/api/oauth2/authorize?client_id=749273748934230018&permissions=2048&scope=bot).



## Prep
* install python3.8+ ([source from official python site](https://www.python.org/) or [deadsnakes ppa](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa))
* install [docker](https://docs.docker.com/get-docker/)
* set the environment variable `DISCORD_CODESCORD` with the value of your bot token. \
 OBS! must be visible to sudo. \
 add in for example `/etc/environment` with a new line at the bottom `export DISCORD_CODESCORD="your token"`

## To Run
1. `git clone https://github.com/EliasEriksson/Codescord.git`
2. `cd Codescord`
3. `python3.x -m venv venv`
4. `source ven/bin/activate`
5. `python -m pip install -r requirements.txt`
6. `sudo venv/bin/python main.py build-docker-image`
7. `python main.py create-database`
8. `sudo venv/bin/python main.py client`

## As a Service
1. modify the provided service file to your system/needs.
As a minimum the path to python and `main.py` needs to be changed.
if `Codescord/` is located in `/home/<user>/Apps/` tha paths in ExecStart should be: \
`ExecStart=/home/<user>/Apps/Codescord/venv/bin/python /home/<user>/Apps/Codescord/main.py client`
2. `sudo cp codescord.service /lib/systemd/system`
3. `sudo systemctl daemon-reload`
4. to enable on system startup: `sudo systemctl enable codescord.service`
5. `sudo systemctl start codescord.service`
6. to stop: `sudo systemctl stop codescord.service`
7. to remove from startup: `sudo systemctl disable codescord.service`
