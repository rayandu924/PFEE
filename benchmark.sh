#!/bin/bash

# Définir les encodeurs et formats que vous souhaitez tester
encodeurs=("y4menc" "x265enc" "x264enc" "webpenc" "wavpackenc" "wavenc" "vp9enc" "vp8enc" "vorbisenc" "voamrwbenc" "avenc_zmbv")

# Spécifier l'emplacement du Dockerfile
dockerfile_location="."  # Remplacez par le chemin de votre Dockerfile
image_name="gstreamer_image"

# Vidéo d'entrée pour les tests
video_file="/home/rayandu924/lesstency/video.mp4"

# Fichier CSV où enregistrer les résultats
csv_file="latency_results.csv"

# Vérifier si l'image existe déjà
if [[ "$(docker images -q $image_name 2> /dev/null)" == "" ]]; then
  echo "Building Docker image..."
  docker build -t $image_name $dockerfile_location
else
  echo "Docker image already exists."
fi

# Créer ou réinitialiser le fichier CSV
echo "Encodeur,LatenceMin(ms),LatenceMax(ms)" > $csv_file

# Fonction pour extraire la latence depuis les logs
extract_latency() {
  log_file=$1
  # Chercher les lignes de latence dans les logs (hypothèse : 'latency:' dans les logs)
  latencies=$(grep -oP "latency \((\d+)\): \d+" "$log_file" | awk '{print $3}')

  # Calculer les latences minimales et maximales
  min_latency=$(echo "$latencies" | sort -n | head -n 1)
  max_latency=$(echo "$latencies" | sort -n | tail -n 1)

  # Si aucune latence trouvée, définir à 0
  min_latency=${min_latency:-0}
  max_latency=${max_latency:-0}

  echo "$min_latency,$max_latency"
}

# Boucle sur les encodeurs
for encodeur in "${encodeurs[@]}"; do  
  echo "Running test for encodeur: $encodeur"

  # Construire la commande GStreamer pour l'encodeur et le format donnés
  gst_command="GST_DEBUG=2 gst-launch-1.0 -v filesrc location=$video_file ! video/x-raw,width=1920,height=1080 ! videoconvert ! $encodeur ! fakesink sync=true"

  # Exécuter la commande GStreamer dans un conteneur Docker avec un nom unique
  log_file="logs/${encodeur}_log.txt"
  docker run --rm --name "${encodeur}_container" $image_name bash -c "$gst_command" 2>&1 | tee "$log_file"

  # Extraire la latence depuis les logs
  latencies=$(extract_latency "$log_file")

  # Écrire les résultats dans le fichier CSV
  echo "$encodeur,$latencies" >> $csv_file
done

echo "Latency measurements saved to $csv_file"
