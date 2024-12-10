import asyncio
import json
import logging
import os
from typing import Set

from aiohttp import web
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRelay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc-server")

ROOT = os.path.dirname(__file__)
pcs: Set[RTCPeerConnection] = set()  # Set to track active peer connections
relay = MediaRelay()  # Initialize MediaRelay

# Replace "USB Camera" with your exact camera name from FFmpeg
CAMERA_NAME = "USB Camera"

# Initialize MediaPlayer and share the video track via MediaRelay
logger.info("Initializing MediaPlayer for USB Camera")
player = MediaPlayer(
    f"video={CAMERA_NAME}",
    format="dshow",
    options={
        "video_size": "160x120"
    }
)

if player.video:
    relay_track = relay.subscribe(player.video)
    logger.info("MediaPlayer initialized successfully")
else:
    relay_track = None
    logger.error("Failed to initialize video track from MediaPlayer")

async def index(request):
    """
    Serves the main HTML page.
    """
    return web.FileResponse(os.path.join(ROOT, "index.html"))

async def offer(request):
    """
    Handles the SDP offer from the WebRTC client and responds with an SDP answer.
    """
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    except Exception as e:
        logger.error(f"Failed to parse offer: {e}")
        return web.Response(status=400, text="Invalid SDP Offer")

    logger.info(f"Received SDP Offer:\n{offer.sdp}")

    pc = RTCPeerConnection()
    pcs.add(pc)
    logger.info("New RTCPeerConnection created")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state changed to: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)
            logger.info("RTCPeerConnection closed and removed from set")

    # Set remote description first
    try:
        await pc.setRemoteDescription(offer)
    except Exception as e:
        logger.error(f"Failed to set remote description: {e}")
        return web.Response(status=400, text="Failed to set remote description")

    # Check if the offer includes video media sections
    has_video = any(line.startswith('m=video') for line in offer.sdp.splitlines())

    if has_video and relay_track:
        # Add the shared video track to the peer connection
        try:
            pc.addTrack(relay_track)
            logger.info("Shared video track added to RTCPeerConnection")
        except Exception as e:
            logger.error(f"Failed to add video track: {e}")
    else:
        logger.info("No video media sections in SDP offer or no relay track available; not adding video track.")

    # Create SDP answer
    try:
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.info("SDP Answer set as local description")
    except Exception as e:
        logger.error(f"Failed to create or set local description: {e}")
        return web.Response(status=500, text="Failed to create SDP Answer")

    # Log the generated SDP answer for debugging
    logger.debug(f"Generated SDP Answer:\n{pc.localDescription.sdp}")

    # Return SDP answer to client
    response_payload = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }

    return web.json_response(response_payload)

async def on_shutdown(app):
    """
    Cleanup on server shutdown: close all peer connections.
    """
    logger.info("Shutting down server, closing all peer connections...")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    logger.info("All RTCPeerConnections closed")

def main():
    app = web.Application()

    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["POST", "GET", "OPTIONS"]
        )
    })

    # Define resources and add routes with CORS
    resources = [
        ("/", "GET", index),
        ("/offer", "POST", offer)
    ]

    for path, method, handler in resources:
        resource = app.router.add_resource(path)
        route = resource.add_route(method, handler)
        cors.add(resource)  # Add CORS to the entire resource

    # Register shutdown handler
    app.on_shutdown.append(on_shutdown)

    port = 8080
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
