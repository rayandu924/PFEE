FROM ubuntu:latest

# Installer les dépendances de base
RUN apt-get update && apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    && apt-get clean

# Copier les scripts
COPY receiver.sh receiver.sh

CMD ["/bin/bash"]
