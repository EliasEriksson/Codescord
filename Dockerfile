FROM python:3.8-buster

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs

RUN wget https://golang.org/dl/go1.15.1.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.15.1.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

WORKDIR /Codescord

COPY Codescord /Codescord/Codescord
COPY Discord /Codescord/Discord
COPY requirements.txt /Codescord/requirements.txt
COPY main.py /Codescord/main.py

RUN python -m pip install -r /Codescord/requirements.txt

CMD ["python", "main.py", "server"]
