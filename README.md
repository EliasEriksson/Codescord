# Codescord

#### Public host
discord [invite link](https://discord.com/api/oauth2/authorize?client_id=749273748934230018&permissions=128&scope=bot).

#### Currently supported languages
* python / py
* cpp / c++
* C
* javascript / js (node.js)
* go
* Java
* php (cli does not give you files back currently)

more languages can easily be added by adding a procedure for the language in `Codescord.Common.languages.Languages`
, pointing to that procedure in `Codescord.Server.server.Server.languages` (in its init)
and update the docker image to contain the runtime/compilers necessary. \
PRs are welcome :)

## Usage
There are two ways to execute highlighted code blocks. This is a setting and can be changed
 with `/codescord auto-run on`. \
 OBS! The first text after the tipple \`\`\` is what determines how the code will be run on the server side.
 ` ```python` for python  ` ```c++` for c++ etc. \
OBS! a new line after the language name is required. see usage and example bellow.
### Manual run (default)
If disabled it can be re-enabled with `/codescord auto-run off`
To execute a highlighted code block in this setting simply use:
###### Raw text:
````
/run```py
print("hello world")
```
````
Manual run can also accept system arguments:
###### Raw text:
````
/run 123 456 789```py
import sys
print(sys.argv[1:] if len(sys.argv) > 1 else "No sys args")
```
````
### Automatic run
To enable this feature run: `/codescord auto-run on` in one of your servers 
text channels the bot can read. When it is enabled 
simply send a discord message with a highlighted code block.
###### Raw text

````
My code is so cool!
```python
print("hello world!")
```
````

### Example
###### Raw text
````
My code is so cool!
/run```py
print("hello world")
```
````
###### Discord formatted message
My code is so cool! \
/run
```python
print("hello world!")
```

###### Bot response

```
hello world!
```

## If you want to self host
#### Requirements
* python3.8+
* python packages:
    * discord.py
    * tortoise-orm
    * aiosqlite
* docker


### Prep
* install python3.8+ ([source from official python site](https://www.python.org/) or [deadsnakes ppa](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa))
* install [docker](https://docs.docker.com/get-docker/)
* set the environment variable `DISCORD_CODESCORD` with the value of your bot token. \
 OBS! must be visible to sudo. \
 add in for example `/etc/environment` with a new line at the bottom `export DISCORD_CODESCORD="your token"`
* make sure localhost is able to go through your desired port range for the application. for each docker container
 that is started one port in the range is used and another container will be queued to open until the process in some
 already running container is done and the used port is freed. each container uses about 30 MB of RAM.
 the default port range is 6090:6096 but can be changed with the `-p` option for `main.py`.

### To Run
1. `git clone https://github.com/EliasEriksson/Codescord.git`
2. `cd Codescord`
3. `python3.x -m venv venv`
4. `source ven/bin/activate`
5. `python -m pip install -r requirements.txt`
6. `sudo venv/bin/python main.py build-docker-image`
7. `python main.py create-database`
8. `sudo venv/bin/python main.py` \
   (this runs the client with the default arguments: \
   `sudo venv/bin/python main.py -p 6090:6096 client`)

### As a Service
1. modify the provided service file to your system/needs.
As a minimum the path to python and `main.py` needs to be changed.
if `Codescord/` is located in `/home/<user>/Apps/` tha paths in ExecStart should be: \
`ExecStart=/home/<user>/Apps/Codescord/venv/bin/python /home/<user>/Apps/Codescord/main.py`
2. `sudo cp codescord.service /lib/systemd/system`
3. `sudo systemctl daemon-reload`
4. to enable on system startup: `sudo systemctl enable codescord.service`
5. `sudo systemctl start codescord.service`
6. to stop: `sudo systemctl stop codescord.service`
7. to remove from startup: `sudo systemctl disable codescord.service`
