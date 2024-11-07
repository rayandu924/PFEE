import asyncio
import json
import numpy as np
import threading
import gi
import os
import logging

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstApp, GLib
from aiohttp import web
from av import VideoFrame
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack
)

# Configuration du Logging
DEBUG_MODE = True
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] %(levelname)s:%(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('RTMP-WebRTC')

Gst.init(None)
pcs = set()

class RTMPVideoStreamTrack(VideoStreamTrack):
    """
    Un VideoStreamTrack qui lit depuis un flux RTMP en utilisant GStreamer.
    """
    def __init__(self, rtmp_url):
        super().__init__()
        self.rtmp_url = rtmp_url

        # Créer le pipeline GStreamer avec des ajustements pour faible latence
        self.pipeline = Gst.parse_launch(
            f'rtmpsrc location={self.rtmp_url} latency=0 ! '
            'flvdemux ! decodebin ! videoconvert ! '
            'video/x-raw,format=BGR ! queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 ! appsink name=sink '
            'emit-signals=true sync=false drop=true'
        )

        # Récupérer appsink
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)

        # Ajouter un gestionnaire de messages pour le bus GStreamer
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

        # Créer un contexte GStreamer et une boucle
        self.mainloop = GLib.MainLoop()
        self.context = self.mainloop.get_context()

        # Démarrer la boucle GStreamer dans un thread séparé
        self.thread = threading.Thread(target=self.mainloop.run, daemon=True)
        self.thread.start()

        # Démarrer le pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.debug("Pipeline GStreamer démarré")

        self.frame = None

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer Error: {err}, {debug}")
        elif t == Gst.MessageType.EOS:
            logger.warning("GStreamer End of Stream")
        elif DEBUG_MODE and t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            logger.debug(f"GStreamer State Changed: {old_state.value_nick} -> {new_state.value_nick}")
        else:
            if DEBUG_MODE:
                logger.debug(f"GStreamer Message: {t}")

    def on_new_sample(self, sink):
        logger.debug("Nouvel échantillon reçu")
        sample = sink.emit('pull-sample')
        if sample is None:
            logger.warning("Échec de la récupération de l'échantillon")
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        caps = sample.get_caps()

        # Convertir le buffer GStreamer en ndarray NumPy
        success, mapinfo = buf.map(Gst.MapFlags.READ)
        if not success:
            logger.warning("Échec du mapping du buffer")
            return Gst.FlowReturn.ERROR
        try:
            data = mapinfo.data
            width = caps.get_structure(0).get_value('width')
            height = caps.get_structure(0).get_value('height')
            logger.debug(f"Frame reçue de taille {width}x{height}")
            array = np.frombuffer(data, np.uint8).reshape((height, width, 3))
            self.frame = array
        finally:
            buf.unmap(mapinfo)

        return Gst.FlowReturn.OK

    async def recv(self):
        logger.debug("Réception d'une nouvelle frame")
        # Attendre que la frame soit disponible
        wait_count = 0
        while self.frame is None:
            await asyncio.sleep(0.001)
            wait_count += 1
            if DEBUG_MODE and wait_count % 1000 == 0:
                logger.debug("En attente d'une frame...")

        frame = self.frame
        self.frame = None

        # Créer un VideoFrame pour WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format='bgr24')
        video_frame.pts, video_frame.time_base = await self.next_timestamp()
        return video_frame

    def stop(self):
        logger.debug("Arrêt du pipeline GStreamer")
        self.pipeline.set_state(Gst.State.NULL)
        self.mainloop.quit()
        self.thread.join()
        super().stop()

async def index(request):
    logger.debug("Chargement de la page index")
    try:
        with open('client.html', 'r') as f:
            content = f.read()
        return web.Response(content_type='text/html', text=content)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de client.html: {e}")
        return web.Response(status=500, text="Erreur du serveur")

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
    logger.debug("Offre SDP reçue")

    pc = RTCPeerConnection()
    pcs.add(pc)
    logger.debug("Nouvelle connexion RTCPeerConnection ajoutée")

    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        logger.info(f"État de la connexion ICE : {pc.iceConnectionState}")
        if pc.iceConnectionState == 'failed':
            await pc.close()
            pcs.discard(pc)
            logger.warning("Connexion ICE échouée et PeerConnection fermée")

    # Ajouter le track vidéo sans modifier les paramètres
    rtmp_url = 'rtmp://127.0.0.1/live/monflux'
    video_track = RTMPVideoStreamTrack(rtmp_url)
    pc.addTrack(video_track)
    logger.debug("Track vidéo ajoutée à PeerConnection")

    # Gérer l'échange SDP
    await pc.setRemoteDescription(offer)
    logger.debug("Description distante définie")
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    logger.debug("Réponse SDP créée et définie")

    return web.Response(
        content_type='application/json',
        text=json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        })
    )

async def on_shutdown(app):
    logger.debug("Arrêt de l'application, fermeture des PeerConnections")
    # Fermer toutes les connexions
    coroutines = [pc.close() for pc in pcs]
    await asyncio.gather(*coroutines)
    for pc in pcs:
        for sender in pc.getSenders():
            track = sender.track
            if track and hasattr(track, 'stop'):
                track.stop()

app = web.Application()
app.on_shutdown.append(on_shutdown)
app.router.add_get('/', index)
app.router.add_post('/offer', offer)

if __name__ == '__main__':
    logger.info("Démarrage du serveur WebRTC sur le port 8080")
    web.run_app(app, port=8080)
