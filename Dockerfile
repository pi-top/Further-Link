FROM python:3.9-bullseye

WORKDIR /tmp/further-link

RUN apt-get update && \
    apt-get install -y python3 && \
    apt-get clean

COPY . ./
RUN python3 setup.py install

ENV FURTHER_LINK_NOSSL=true

EXPOSE 8028
CMD [ "further-link" ]
