#!/bin/bash

# Récupérer les variables d'environnement
codec=${CODEC}
format=${FORMAT}

# Vérifier que les variables d'environnement sont définies
if [ -z "$codec" ] || [ -z "$format" ]; then
    echo "Error: CODEC and FORMAT environment variables must be set."
    exit 1
fi

# Exécuter la commande GStreamer pour recevoir la vidéo
gst-launch-1.0 $FORMAT port=5000 ! application/x-rtp,media=video,encoding-name=H264 ! rtph264depay ! $codec ! videoconvert ! autovideosink
