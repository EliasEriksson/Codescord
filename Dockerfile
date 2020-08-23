FROM python:3.8-buster

WORKDIR /app

ENV PORT 6969

COPY Codescord /app/Codescord
COPY Discord /app/Discord
COPY requirements.txt /app/requirements.txt
COPY main.py /app/main.py

RUN python -m pip install -r /app/requirements.txt

CMD ["python", "main.py", "server"]
