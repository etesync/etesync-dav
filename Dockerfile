FROM python:3.8

ENV ETESYNC_DATA_DIR "/data"
ENV ETESYNC_SERVER_HOSTS "0.0.0.0:37358,[::]:37358"

# Make this file a build dep for the next steps
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

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
