import asyncio
import json
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GstApp
from aiohttp import web
from av import VideoFrame
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCConfiguration
)

Gst.init(None)
pcs = set()

class RTSPVideoStreamTrack(VideoStreamTrack):
    """
    Un VideoStreamTrack qui lit depuis un flux RTSP en utilisant GStreamer.
    """
    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url

        # Créer le pipeline GStreamer
        self.pipeline = Gst.parse_launch(
            f'rtspsrc location={self.rtsp_url} latency=0 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true'
        )

        # Récupérer appsink
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)

        # Démarrer le pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

        self.frame = None

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()

        # Convertir le buffer GStreamer en ndarray NumPy
        success, mapinfo = buf.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR
        try:
            data = mapinfo.data
            width = caps.get_structure(0).get_value('width')
            height = caps.get_structure(0).get_value('height')
            array = np.frombuffer(data, np.uint8).reshape((height, width, 3))
            self.frame = array
        finally:
            buf.unmap(mapinfo)

        return Gst.FlowReturn.OK

    async def recv(self):
        # Attendre que la frame soit disponible
        while self.frame is None:
            await asyncio.sleep(0.001)

        frame = self.frame
        self.frame = None

        # Créer un VideoFrame pour WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format='bgr24')
        video_frame.pts, video_frame.time_base = self.next_timestamp()
        return video_frame

    async def stop(self):
        self.pipeline.set_state(Gst.State.NULL)

async def index(request):
    content = open('client.html', 'r').read()
    return web.Response(content_type='text/html', text=content)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection(
        RTCConfiguration(iceServers=[], bundlePolicy='max-bundle')
    )
    pcs.add(pc)

    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        print('État de la connexion ICE : %s' % pc.iceConnectionState)
        if pc.iceConnectionState == 'failed':
            await pc.close()
            pcs.discard(pc)

    # Ajouter le track vidéo
    rtsp_url = 'rtsp://votre_flux_rtsp'  # Remplacez par votre URL RTSP
    video_track = RTSPVideoStreamTrack(rtsp_url)
    video_sender = pc.addTrack(video_track)

    # Configurer les paramètres pour réduire la latence
    parameters = video_sender.getParameters()
    if parameters.encodings:
        for encoding in parameters.encodings:
            encoding.maxBitrate = 500000  # Ajustez selon vos besoins
            encoding.maxFramerate = 30
            encoding.priority = 'high'
            encoding.networkPriority = 'high'
        await video_sender.setParameters(parameters)

    # Gérer l'échange SDP
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type='application/json',
        text=json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        })
    )

async def on_shutdown(app):
    # Fermer toutes les connexions
    coroutines = [pc.close() for pc in pcs]
    await asyncio.gather(*coroutines)
    for pc in pcs:
        for sender in pc.getSenders():
            track = sender.track
            if track and hasattr(track, 'stop'):
                await track.stop()

app = web.Application()
app.on_shutdown.append(on_shutdown)
app.router.add_get('/', index)
app.router.add_post('/offer', offer)

if __name__ == '__main__':
    web.run_app(app, port=8080)
