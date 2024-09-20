# Janus Gateway Custom Repository

This repository contains a customized version of the Janus Gateway for RTSP streaming.

## Table of Contents
1. [Installation](#installation)
2. [Modifying Video Stream Configuration](#modifying-video-stream-configuration)
3. [Launching Janus](#launching-janus)
4. [Accessing the Web Client](#accessing-the-web-client)
5. [Viewing WebRTC Metrics](#viewing-webrtc-metrics)

---

## Installation

### Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/rayandu924/lesstency.git
cd lesstency
```

### Install Dependencies

Janus requires several dependencies to function correctly. Run the following command to install all necessary libraries:

```bash
sudo apt-get update
sudo apt-get install -y libmicrohttpd-dev libjansson-dev \
  libssl-dev libsrtp2-dev libsofia-sip-ua-dev libglib2.0-dev \
  libopus-dev libogg-dev libini-config-dev libcollection-dev \
  libyaml-dev pkg-config gengetopt libtool automake
```

Ensure all libraries are installed successfully before proceeding.

---

## Modifying Video Stream Configuration

To modify the video stream, you need to update the configuration file for the streaming plugin.

1. Open the configuration file:
   ```bash
   sudo nano /usr/local/etc/janus/janus.plugin.streaming.jcfg
   ```

2. Find the section related to `rtsp-test` and modify it as follows:

   ```plaintext
   rtsp-test: {
       ...
       url = "rtsp://ip-address:port/stream";
       ...
   }
   ```

   Update the `url` field with the correct RTSP stream URL. Make sure this stream is accessible and functional on your machine.

---

## Launching Janus

Once you have modified the stream configuration, you can now launch Janus:

```bash
sudo janus
```

**Note**: Ensure that the RTSP stream is active and working before launching Janus, or it will fail to retrieve the stream.

---

## Accessing the Web Client

To test Janus, use the web client located in the repository. Follow these steps:

1. Navigate to the `client` directory:
   ```bash
   cd lesstency/client
   ```

2. Open the `index.html` file in your browser:
   ```bash
   open index.html
   ```

3. In the web interface:
   - Click on **Start Stream**.
   - Select the stream labeled **Local RTMP Stream**.
   - Click **Watch** to view the stream.

---

## Viewing WebRTC Metrics

For detailed WebRTC metrics, you can use Chrome's WebRTC internal tool. Open a new Chrome tab and go to:

```plaintext
chrome://webrtc-internals/
```

This will provide you with detailed information and statistics about the active WebRTC streams.

---