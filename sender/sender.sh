#!/bin/bash

# Paramètres : largeur, hauteur, codec, format
WIDTH=$1
HEIGHT=$2
CODEC=$3
FORMAT=$4

gst-launch-1.0 videotestsrc ! video/x-raw,width=$WIDTH,height=$HEIGHT ! $CODEC ! $FORMAT://receiver:5000
