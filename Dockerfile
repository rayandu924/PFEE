# Dockerfile pour webrtc-server

# Utiliser Python 3.10 slim
FROM python:3.10-slim

# Installer les dépendances système requises
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt requirements.txt
COPY server.py server.py
COPY static/ static/

# Mettre à jour pip
RUN pip install --upgrade pip

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port 8080 pour le serveur web
EXPOSE 8080

# Démarrer le serveur
CMD ["python", "server.py"]
