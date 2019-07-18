# Builds a standalone executable from the etesync-dav docker image.
#
# Make sure etesync/etesync-dav is up to date and then
# docker build -t etesync-dav-bundle -f pyinstaller/Dockerfile .
# docker run --rm -it -u $(id -u):$(id -g) -v $(pwd):/repo etesync-dav-bundle

FROM etesync/etesync-dav

USER root

RUN pip install PyInstaller

USER etesync

ENTRYPOINT ["bash"]
CMD ["-c", "cd /repo/pyinstaller && ./bundle.sh"]
