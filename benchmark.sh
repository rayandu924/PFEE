#!/bin/bash

# Define encoders and their respective payloaders
declare -A encodeurs_payloaders
encodeurs_payloaders=( 
  ["x264enc"]="rtph264pay"
  ["x265enc"]="rtph265pay"
  ["vp8enc"]="rtpvp8pay"
  ["vp9enc"]="rtpvp9pay"
)

# Specify Dockerfile location and image name
dockerfile_location="."
image_name="gstreamer_image"

# Check if the Docker image exists, build if not
if [[ "$(docker images -q $image_name 2> /dev/null)" == "" ]]; then
  docker build -t $image_name $dockerfile_location
fi

# Loop through encoders and their payloaders
for encodeur in "${!encodeurs_payloaders[@]}"; do
  payloader=${encodeurs_payloaders[$encodeur]}
  echo "Testing with encoder: $encodeur and payloader: $payloader"

  # Run sender container
  gst_command="
    gst-launch-1.0 -v \
    videotestsrc num-buffers=100 ! \
    videoconvert ! \
    $encodeur ! \
    $payloader ! \
    webrtcbin stun-server=stun://stun.l.google.com:19302"
  
  docker run --rm \
    --name "${encodeur}_sender" \
    $image_name \
    bash -c "$gst_command"
done
