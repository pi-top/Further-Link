FROM python:3.7-buster

WORKDIR /usr/lib/pt-further-link

RUN apt-get update && \
    apt-get install -y pipenv && \
    apt-get clean;

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

COPY cert.pem cert.pem
COPY key.pem key.pem
COPY data data
COPY server.py server.py
COPY src src

EXPOSE 8028
CMD [ "pipenv", "run", "python3", "server.py" ]
