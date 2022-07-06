FROM debian:bullseye

RUN apt-get update && \
    apt-get install -y python3-tk python3-pip && \
    apt-get clean

RUN pip3 install -U pip

RUN apt-get update && \
    apt-get install -y novnc net-tools procps xvfb x11vnc && \
    apt-get clean

WORKDIR /further-link

COPY pyproject.toml setup.py setup.cfg MANIFEST.in ./
COPY debian debian
COPY LICENSE README.rst ./
COPY further_link further_link
COPY scripts scripts

RUN pip3 install .

ENV FURTHER_LINK_NOSSL=true

EXPOSE 8028
EXPOSE 60000-61000
CMD [ "further-link" ]
