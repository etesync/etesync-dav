FROM python:3.7

ENV ETESYNC_CONFIG_DIR "/data"
ENV ETESYNC_LISTEN_ADDRESS "0.0.0.0"
ENV ETESYNC_LISTEN_PORT "37358"

# Make this file a build dep for the next steps
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt scrypt

# Make this file a build dep for the next steps
COPY etesync_dav/_version.py /tmp/
RUN pip install etesync-dav

RUN set -ex ;\
        useradd etesync ;\
        mkdir -p /data ;\
        chown -R etesync: /data

VOLUME /data
EXPOSE 37358

USER etesync

ENTRYPOINT ["etesync-dav"]
