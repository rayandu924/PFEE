#!/bin/bash

# Définir les encodeurs et formats que vous souhaitez tester
encodeurs=("y4menc" "x265enc" "x264enc" "webpenc" "wavpackenc" "wavenc" "vp9enc" "vp8enc" "vorbisenc" "voamrwbenc" "avenc_zmbv")

# Spécifier l'emplacement du Dockerfile
dockerfile_location="." 
image_name="gstreamer_image"

# Vérifier si l'image existe déjà
if [[ "$(docker images -q $image_name 2> /dev/null)" == "" ]]; then
  echo "Building Docker image..."
  docker build -t $image_name $dockerfile_location
else
  echo "Docker image already exists."
fi

for encodeur in "${encodeurs[@]}"; do
  echo "Launching test for encodeur: $encodeur"

  gst_command="
    gst-launch-1.0 -v \
    videotestsrc num-buffers=100 ! \
    video/x-raw, width=1280, height=720 ! \
    videoconvert ! \
    $encodeur ! \
    fakesink sync=true
  "
  
  # Exécuter la commande et rediriger toutes les sorties vers le fichier log
  docker run --rm \
    --name "${encodeur}_container" \
    $image_name \
    bash -c "$gst_command" 2>&1 | tee "logs/${encodeur}_log.txt"
done