FROM python:3.7-buster

WORKDIR /usr/lib/pt-further-link

RUN apt-get update && \
    apt-get install -y pipenv && \
    apt-get clean;

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

ENV FURTHER_LINK_NOSSL=true

COPY server.py server.py
COPY src src

EXPOSE 8028
CMD [ "pipenv", "run", "python3", "server.py" ]
