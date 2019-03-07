FROM python:3.7

ENV ETESYNC_CONFIG_DIR "/data"
ENV ETESYNC_LISTEN_ADDRESS "0.0.0.0"
ENV ETESYNC_LISTEN_PORT "37358"

RUN pip install etesync-dav scrypt

RUN set -ex ;\
        useradd etesync ;\
        mkdir -p /data ;\
        chown -R etesync: /data

VOLUME /data
EXPOSE 37358

USER etesync

ENTRYPOINT ["etesync-dav"]
