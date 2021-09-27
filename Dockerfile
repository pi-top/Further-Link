FROM python:3.9-bullseye

WORKDIR /tmp/further-link

COPY pyproject.toml setup.py setup.cfg MANIFEST.in ./
COPY LICENSE README.rst ./
COPY further_link further_link
RUN pip install .

ENV FURTHER_LINK_NOSSL=true

EXPOSE 8028
CMD [ "further-link" ]
