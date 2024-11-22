import asyncio
import json
import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import time  # Ajouté pour les pauses dans les tentatives de connexion

pcs = set()

class CameraStreamTrack(VideoStreamTrack):
    """
    Un track vidéo pour envoyer les frames de la caméra Insta360 Pro 2 via RTSP
    """

    def __init__(self):
        super().__init__()
        self.cap = None
        self.initialize_capture()

    def initialize_capture(self, retries=5, delay=2):
        for attempt in range(retries):
            self.cap = cv2.VideoCapture('rtsp://rtsp-server:8554/video360')
            if self.cap.isOpened():
                print("Connexion au flux RTSP réussie.")
                return
            else:
                print(f"Échec de la connexion au flux RTSP. Tentative {attempt + 1}/{retries}...")
                time.sleep(delay)
        raise Exception("Impossible de se connecter au flux RTSP après plusieurs tentatives.")

    async def recv(self):
        if not self.cap:
            raise Exception("Capture vidéo non initialisée.")
        # Lire une frame du flux RTSP
        ret, frame = self.cap.read()
        if not ret:
            # Attendre un court instant si la frame n'est pas disponible
            await asyncio.sleep(0.01)
            return await self.recv()

        # Convertir l'image si nécessaire (par exemple, si le flux est en format différent)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")

        # Mettre à jour les timestamps
        video_frame.pts, video_frame.time_base = await self.next_timestamp()

        return video_frame

    def stop(self):
        super().stop()
        if self.cap:
            self.cap.release()

async def index(request):
    return web.FileResponse('static/index.html')

async def javascript(request):
    return web.FileResponse('static/client.js')

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection State:", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Ajouter le flux vidéo de la caméra
    pc.addTrack(CameraStreamTrack())

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/client.js', javascript)
app.router.add_post('/offer', offer)
app.router.add_static('/static/', path='static/')

async def on_shutdown(app):
    # Fermer toutes les connexions peer
    coroutines = [pc.close() for pc in pcs]
    await asyncio.gather(*coroutines)
    pcs.clear()

app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, port=8080)
