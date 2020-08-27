FROM python:3.8-buster

WORKDIR /Codescord

COPY Codescord /Codescord/Codescord
COPY Discord /Codescord/Discord
COPY requirements.txt /Codescord/requirements.txt
COPY main.py /Codescord/main.py

RUN python -m pip install -r /Codescord/requirements.txt

CMD ["python", "main.py", "server"]
