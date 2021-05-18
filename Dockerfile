FROM python:3.7-buster

WORKDIR /usr/lib/pt-further-link

RUN apt-get update && \
    apt-get install -y pipenv && \
    apt-get clean;

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

ENV FURTHER_LINK_NOSSL=true

RUN ls
COPY server.py server.py
RUN ls
COPY src src
RUN ls
COPY data.txt data.txt

# overwrite version file based on changelog version
COPY debian/changelog changelog
RUN echo __version__ = \'$(\
  sed -n "1 s/pt-further-link (\(.*\)).*/\1/p" changelog\
)\' > src/lib/further_link/version.py \
&& rm changelog

EXPOSE 8028
CMD [ "pipenv", "run", "python3", "server.py" ]
