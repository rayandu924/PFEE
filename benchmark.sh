#!/bin/bash

# Définir la durée du test en secondes
TEST_DURATION=100

# Fonction pour mesurer la latence avec tracing
measure_latency() {
    codec=$1
    resolution=$2
    format=$3

    echo "Testing Codec: $codec, Resolution: $resolution, Format: $format"

    # Configurer les variables d'environnement pour Docker Compose
    export RESOLUTION=$resolution
    export CODEC=$codec
    export FORMAT=$format

    # Lancer les services avec tracing
    env GST_DEBUG="GST_TRACER:7" \
        GST_TRACERS="latency(flags=element+pipeline)" \
        GST_DEBUG_FILE=./latency.log \
        docker-compose up -d

    # Attendre que la vidéo soit transmise
    sleep $TEST_DURATION  # Utiliser la constante de durée

    # Vérifier si le fichier de log existe et n'est pas vide
    if [ ! -s ./latency.log ]; then
        echo "Error: Latency log file is empty or does not exist."
        docker-compose down
        return
    fi

    # Analyser le fichier de log pour extraire la latence
    latency_sum=$(grep "element-latency" ./latency.log | awk -F"time=" '{sum+=$2} END {print sum}')
    count=$(grep "element-latency" ./latency.log | wc -l)

    if [ $count -gt 0 ]; then
        average_latency=$(echo "$latency_sum / $count" | bc)
    else
        average_latency=0
    fi

    # Stocker les résultats
    echo "Codec: $codec, Resolution: $resolution, Format: $format, Average Latency: ${average_latency}ns" >> results/benchmark_results.txt

    # Nettoyer l'environnement Docker
    docker-compose down
}

# Dossier pour enregistrer les résultats
mkdir -p results

# Boucle sur toutes les combinaisons
codecs=("x264enc")
resolutions=("1280x720" "1920x1080" "3840x2160")
formats=("udp" "rtp" "webrtc")

for codec in "${codecs[@]}"; do
  for resolution in "${resolutions[@]}"; do
    for format in "${formats[@]}"; do
      measure_latency $codec $resolution $format
    done
  done
done

echo "Benchmark terminé ! Les résultats sont dans le fichier results/benchmark_results.txt."
