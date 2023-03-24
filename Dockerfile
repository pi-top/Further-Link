FROM debian:bullseye

ARG PYTHON_PACKAGE_VERSION

# Install pip3 and python3 with tk graphics
RUN apt-get update && \
    apt-get install -y python3-tk python3-pip && \
    apt-get clean

RUN pip3 install -U pip

# Install pi-top OS source
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean

RUN git clone https://github.com/pi-top/pi-topOS-Apt-Source.git && \
    cd pi-topOS-Apt-Source && \
    cp keys/* /usr/share/keyrings/ && \
    cp sources/pi-top-os.list /etc/apt/sources.list.d/ && \
    apt-get update && \
    rm -rf /pi-topOS-Apt-Source

# Install pt-web-vnc
COPY pt-web-vnc_0.3.1-3~8.gbpfbf64b_all.deb /tmp/
RUN apt-get update && \
    apt-get install -y /tmp/pt-web-vnc_0.3.1-3~8.gbpfbf64b_all.deb && \
    apt-get clean

WORKDIR /further-link

COPY pyproject.toml setup.py setup.cfg MANIFEST.in ./
COPY debian debian
COPY LICENSE README.rst ./
COPY further_link further_link

RUN pip3 install .

ENV FURTHER_LINK_NOSSL=true
ENV PYTHONUNBUFFERED=1
ENV PYTHON_PACKAGE_VERSION=$PYTHON_PACKAGE_VERSION

EXPOSE 8028
EXPOSE 60100-60999
CMD [ "further-link" ]
