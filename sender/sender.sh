#!/bin/bash

# Récupérer les variables d'environnement
RESOLUTION=${RESOLUTION}
CODEC=${CODEC}
FORMAT=${FORMAT}

# Extraire la largeur et la hauteur de la résolution
IFS='x' read -r WIDTH HEIGHT <<< "$RESOLUTION"

# Construire et exécuter le pipeline GStreamer
gst-launch-1.0 videotestsrc ! video/x-raw,width=$WIDTH,height=$HEIGHT ! $CODEC ! $FORMAT host=receiver port=5000
