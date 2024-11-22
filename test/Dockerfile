# Utiliser une image Debian slim comme base
FROM debian:bullseye-slim

# Installer les dépendances nécessaires, y compris curl et FFmpeg
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Télécharger et installer MediaMTX
RUN curl -L https://github.com/bluenviron/mediamtx/releases/download/v1.9.3/mediamtx_v1.9.3_linux_amd64.tar.gz \
    | tar -xz \
    && mv mediamtx /usr/local/bin/

# Copier le fichier de configuration dans le conteneur
COPY mediamtx.yml /mediamtx.yml

# Copier la vidéo 360 dans le conteneur (si nécessaire)
COPY video360.mp4 /video360.mp4

# Exposer le port RTSP
EXPOSE 8554

# Commande par défaut pour lancer le serveur
CMD ["mediamtx", "/mediamtx.yml"]
