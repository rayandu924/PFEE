import asyncio
import json
import logging
import os
import uuid
from typing import Set, Optional

from aiohttp import web
import aiohttp_cors
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer,
)
from aiortc.contrib.media import MediaPlayer, MediaRelay

# ========================================
# Configuration
# ========================================

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("webrtc-server")

# Server configuration
ROOT = os.path.dirname(__file__)
PORT = 8080
HOST = "0.0.0.0"

# Media configuration
CAMERA_NAME = "USB Camera"  # Nom de la caméra à ajuster
MEDIA_FORMAT = "dshow" if os.name == "nt" else "v4l2"
MEDIA_OPTIONS = {
    "rtbufsize": "1000000000",
    "video_size": "1280x720",  # Résolution améliorée
    "framerate": "10",  # Taux de rafraîchissement
}

# WebRTC configuration
ICE_SERVERS = [
    RTCIceServer(
        urls=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]
    ),
    # Vous pouvez ajouter des serveurs TURN ici si nécessaire
]
RTC_CONFIG = RTCConfiguration(
    iceServers=ICE_SERVERS,
    #iceTransportPolicy="all",  # Exemple de politique de transport ICE
    # bundlePolicy="max-bundle",  # Commenté si non supporté
    #sdpSemantics="unified-plan",  # Semantique SDP
)

# Track configuration
TRACK_OPTIONS = {
    "bitrate": 500,  # Bitrate en kbps
    "codec": "VP8",  # Codec vidéo
}

# ========================================
# Global Variables
# ========================================

pcs: Set[RTCPeerConnection] = set()
relay = MediaRelay()
connections = {}

# ========================================
# Media Player Initialization
# ========================================

def initialize_media_player() -> Optional:
    """
    Initialise le MediaPlayer pour capturer la vidéo de la caméra.
    """
    logger.info(f"Initialisation de MediaPlayer pour la caméra {CAMERA_NAME}")
    try:
        player = MediaPlayer(
            f"video={CAMERA_NAME}",
            format=MEDIA_FORMAT,
            options=MEDIA_OPTIONS,
        )
        if player.video:
            relay_track = relay.subscribe(player.video)
            logger.info("MediaPlayer initialisé avec succès")
            return relay_track
        else:
            logger.error("Aucune piste vidéo trouvée dans MediaPlayer")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de MediaPlayer : {e}")
        return None

relay_track = initialize_media_player()

# ========================================
# Helper Functions
# ========================================

async def wait_for_ice_gathering_complete(
    pc: RTCPeerConnection, timeout: int = 10
) -> None:
    """
    Attend que la collecte ICE soit terminée ou qu'un délai soit atteint.
    """
    if pc.iceGatheringState == "complete":
        return

    fut = asyncio.get_event_loop().create_future()

    def on_state_change():
        if pc.iceGatheringState == "complete":
            if not fut.done():
                fut.set_result(None)

    pc.on("icegatheringstatechange", on_state_change)

    try:
        await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError:
        logger.warning("La collecte ICE a expiré")

def create_peer_connection(connection_id: str) -> RTCPeerConnection:
    """
    Crée et configure une nouvelle RTCPeerConnection.
    """
    pc = RTCPeerConnection(configuration=RTC_CONFIG)
    pcs.add(pc)
    connections[connection_id] = pc
    logger.info(f"Nouvelle RTCPeerConnection créée avec ID : {connection_id}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"État de la connexion {connection_id} changé en : {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)
            connections.pop(connection_id, None)
            logger.info(f"RTCPeerConnection {connection_id} fermée et supprimée")

    return pc

# ========================================
# Route Handlers
# ========================================

async def handle_index(request: web.Request) -> web.FileResponse:
    """
    Sert la page HTML principale.
    """
    logger.debug("Requête GET reçue pour '/'")
    return web.FileResponse(os.path.join(ROOT, "index.html"))

async def handle_offer(request: web.Request) -> web.Response:
    """
    Traite les offres SDP envoyées par les clients.
    """
    logger.debug("Requête POST reçue sur /offer")
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        logger.debug(f"Offre SDP analysée :\n{offer.sdp}")
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Échec de l'analyse de l'offre SDP : {e}")
        return web.Response(status=400, text="Offre SDP invalide")

    connection_id = str(uuid.uuid4())
    pc = create_peer_connection(connection_id)

    try:
        await pc.setRemoteDescription(offer)
        logger.info(f"Description distante définie pour {connection_id}")
    except Exception as e:
        logger.error(f"Échec de la définition de la description distante pour {connection_id} : {e}")
        return web.Response(status=400, text="Échec de la définition de la description distante")

    # Ajout de la piste vidéo si disponible
    if "video" in offer.sdp and relay_track:
        try:
            pc.addTrack(relay_track)
            logger.info(f"Piste vidéo partagée ajoutée à RTCPeerConnection {connection_id}")
        except Exception as e:
            logger.error(f"Échec de l'ajout de la piste vidéo pour {connection_id} : {e}")
    else:
        logger.warning(f"Aucune section média vidéo dans l'offre SDP ou piste relay indisponible pour {connection_id}")

    try:
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.info(f"Réponse SDP locale créée pour {connection_id}")
    except Exception as e:
        logger.error(f"Échec de la création ou de la définition de la description locale pour {connection_id} : {e}")
        return web.Response(status=500, text="Échec de la création de la réponse SDP")

    await wait_for_ice_gathering_complete(pc)

    response_payload = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "id": connection_id,
    }

    logger.debug(f"Payload de réponse pour {connection_id} : {response_payload}")

    return web.json_response(response_payload)

async def handle_candidate(request: web.Request) -> web.Response:
    """
    Traite les candidats ICE envoyés par les clients.
    """
    try:
        params = await request.json()
        connection_id = params["id"]
        candidate = RTCIceCandidate(
            sdpMid=params["sdpMid"],
            sdpMLineIndex=params["sdpMLineIndex"],
            candidate=params["candidate"],
        )
        logger.info(f"Candidat ICE reçu pour {connection_id} : {candidate.candidate}")
    except KeyError as e:
        logger.error(f"Clé manquante dans le payload du candidat ICE : {e}")
        return web.Response(status=400, text="Candidat ICE invalide")
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON pour le candidat ICE : {e}")
        return web.Response(status=400, text="Candidat ICE invalide")

    pc = connections.get(connection_id)
    if not pc:
        logger.error(f"Aucune RTCPeerConnection trouvée pour l'ID de connexion : {connection_id}")
        return web.Response(status=400, text="ID de connexion invalide")

    try:
        await pc.addIceCandidate(candidate)
        logger.info(f"Candidat ICE ajouté avec succès pour {connection_id}")
    except Exception as e:
        logger.error(f"Échec de l'ajout du candidat ICE pour {connection_id} : {e}")
        return web.Response(status=400, text="Échec de l'ajout du candidat ICE")

    return web.Response(status=200, text="Candidat ICE ajouté avec succès")

# ========================================
# Server Setup
# ========================================

async def on_shutdown(app: web.Application) -> None:
    """
    Nettoie toutes les connexions peer lors de l'arrêt du serveur.
    """
    logger.info("Arrêt du serveur, fermeture de toutes les RTCPeerConnections...")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    connections.clear()
    logger.info("Toutes les RTCPeerConnections ont été fermées")

def setup_routes(app: web.Application) -> None:
    """
    Configure les routes de l'application avec CORS.
    """
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["POST", "GET", "OPTIONS"]
        )
    })

    routes = [
        ("/", "GET", handle_index),
        ("/offer", "POST", handle_offer),
        ("/candidate", "POST", handle_candidate),
    ]

    for path, method, handler in routes:
        resource = app.router.add_resource(path)
        route = resource.add_route(method, handler)
        cors.add(route)

def main() -> None:
    """
    Point d'entrée principal du serveur.
    """
    app = web.Application()
    setup_routes(app)
    app.on_shutdown.append(on_shutdown)

    logger.info(f"Démarrage du serveur de signalement sur http://{HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
