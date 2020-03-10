FROM python:3.7-stretch

ENV ETESYNC_DATA_DIR "/data"
ENV ETESYNC_LISTEN_ADDRESS "0.0.0.0"
ENV ETESYNC_LISTEN_PORT "37358"

# Make this file a build dep for the next steps
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt scrypt

COPY . /app
RUN pip install /app

RUN set -ex ;\
        useradd etesync ;\
        mkdir -p /data ;\
        chown -R etesync: /data

VOLUME /data
EXPOSE 37358

USER etesync

ENTRYPOINT ["etesync-dav"]
