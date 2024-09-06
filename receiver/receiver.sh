#!/bin/bash

# Paramètres : codec, format
CODEC=$1
FORMAT=$2

gst-launch-1.0 $FORMAT://sender:5000 ! $CODEC ! fakesink
