FROM python:3.9-bullseye

WORKDIR /tmp/further-link

COPY . ./
RUN pip install -e .

ENV FURTHER_LINK_NOSSL=true

EXPOSE 8028
CMD [ "further-link" ]
