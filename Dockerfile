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
RUN apt-get update && \
    apt-get install -y pt-web-vnc && \
    apt-get clean

# Install pitop SDK prerequisites
RUN apt-get update && \
    apt-get install -y pkg-config libsystemd0 libsystemd-dev && \
    pip3 install cmake && \
    apt-get clean

# Install pitop SDK
# using pip for onnxruntime as there is only armhf debian build
RUN pip3 install pitop==0.26.3.post1

# Install useful extras from pt-os
RUN apt-get update && \
    # not installable apt-get install -y pt-os-ui-mods && \
    apt-get install -y chromium && \
    apt-get install -y vim && \
    apt-get install -y python3-matplotlib && \
    # no audio DEBIAN_FRONTEND='noninteractive' apt-get install -y sonic-pi python3-sonic && \
    apt-get clean

WORKDIR /further-link

COPY pyproject.toml setup.py setup.cfg MANIFEST.in ./
COPY debian debian
COPY LICENSE README.rst ./
COPY further_link further_link

RUN pip3 install .

ENV FURTHER_LINK_NOSSL=true
ENV FURTHER_LINK_MAX_PROCESSES=4
ENV PYTHONUNBUFFERED=1
ENV PYTHON_PACKAGE_VERSION=$PYTHON_PACKAGE_VERSION

EXPOSE 8028
EXPOSE 61100-61103
CMD [ "further-link" ]
