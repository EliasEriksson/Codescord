FROM python:3.8-buster

# misc
RUN apt update
RUN apt install -y software-properties-common

# node.js install
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs

# go install
RUN wget https://golang.org/dl/go1.15.1.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.15.1.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

# java install
RUN apt install -y default-jdk

# php install
#RUN apt-add-repository ppa:ondrej/pkg-gearman
#RUN apt update
RUN apt install -y php-cli

# cleanup
RUN rm -rf /var/lib/apt/lists/*

# setup the server
WORKDIR /Codescord
COPY Codescord /Codescord/Codescord
COPY Discord /Codescord/Discord
COPY requirements.txt /Codescord/requirements.txt
COPY process.requirements.txt /Codescord/process.requirements.txt
COPY main.py /Codescord/main.py

RUN python -m pip install -r /Codescord/requirements.txt
RUN python -m pip install -r /Codescord/process.requirements.txt

CMD ["python", "main.py", "server"]
