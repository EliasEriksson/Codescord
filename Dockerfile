FROM python:3.10-buster

# misc
RUN apt update
RUN apt install -y software-properties-common

# node.js install
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs

# go install
RUN wget https://golang.org/dl/go1.15.1.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.15.1.linux-amd64.tar.gz
RUN rm go1.15.1.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

# java install
RUN apt install -y default-jdk

# php install
#RUN apt-add-repository ppa:ondrej/pkg-gearman
#RUN apt update
RUN apt install -y php-cli

# C# install
RUN wget https://packages.microsoft.com/config/debian/10/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
RUN dpkg -i packages-microsoft-prod.deb
RUN rm packages-microsoft-prod.deb
RUN apt update
RUN apt install -y apt-transport-https
RUN apt install -y dotnet-sdk-5.0

# cleanup
RUN rm -rf /var/lib/apt/lists/*

# setup the server
WORKDIR /Codescord
# C# setup to reduce time
RUN dotnet new console --output cs
RUN rm cs/Program.cs

# python setup
COPY requirements.txt /Codescord/requirements.txt
COPY process.requirements.txt /Codescord/process.requirements.txt
RUN python -m pip install -r /Codescord/requirements.txt
RUN python -m pip install -r /Codescord/process.requirements.txt

COPY Codescord /Codescord/Codescord
COPY Discord /Codescord/Discord
COPY main.py /Codescord/main.py


CMD ["python", "main.py", "server"]
