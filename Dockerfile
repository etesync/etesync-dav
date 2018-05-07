FROM python:3.6

ENV ETESYNC_CONFIG_DIR "/data"
ENV ETESYNC_LISTEN_ADDRESS "0.0.0.0"
ENV ETESYNC_LISTEN_PORT "37358"

COPY . /tmp
RUN cd /tmp && python setup.py install

VOLUME /data
EXPOSE 37358

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
