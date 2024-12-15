import asyncio
import json
import logging
import os
from typing import Set
import uuid

from aiohttp import web
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer, MediaRelay

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("webrtc-server")

ROOT = os.path.dirname(__file__)
pcs: Set[RTCPeerConnection] = set()
relay = MediaRelay()
connections = {}

# Nom de la caméra (à ajuster selon votre système)
CAMERA_NAME = "USB Camera"

# Initialisation de MediaPlayer
logger.info("Initialisation de MediaPlayer pour la caméra USB")
player = MediaPlayer(
    f"video={CAMERA_NAME}",
    format="dshow" if os.name == "nt" else "v4l2",
    options={
        "video_size": "160x120"
    }
)

if player.video:
    relay_track = relay.subscribe(player.video)
    logger.info("MediaPlayer initialisé avec succès")
else:
    relay_track = None
    logger.error("Échec de l'initialisation de la piste vidéo depuis MediaPlayer")

async def index(request):
    """
    Sert la page HTML principale.
    """
    logger.debug("Requête GET reçue pour '/'")
    return web.FileResponse(os.path.join(ROOT, "index.html"))

async def wait_for_ice_gathering_complete(pc: RTCPeerConnection, timeout=10):
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

async def offer(request):
    """
    Traite les offres SDP des clients et répond avec des réponses SDP contenant un identifiant de connexion unique.
    """
    logger.debug("Requête POST reçue sur /offer")
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        logger.debug(f"Offre SDP analysée :\n{offer.sdp}")
    except Exception as e:
        logger.error(f"Échec de l'analyse de l'offre SDP : {e}")
        return web.Response(status=400, text="Offre SDP invalide")

    logger.info("Offre SDP reçue du client")

    pc = RTCPeerConnection()
    pcs.add(pc)
    logger.info("Nouvelle RTCPeerConnection créée")

    connection_id = str(uuid.uuid4())
    connections[connection_id] = pc
    logger.info(f"ID de connexion attribué : {connection_id}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"État de la connexion changé en : {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)
            connections.pop(connection_id, None)
            logger.info("RTCPeerConnection fermée et supprimée")

    # Définir la description distante avec l'offre SDP
    try:
        await pc.setRemoteDescription(offer)
        logger.info("Description distante définie avec l'offre SDP")
    except Exception as e:
        logger.error(f"Échec de la définition de la description distante : {e}")
        return web.Response(status=400, text="Échec de la définition de la description distante")

    # Vérifier si l'offre inclut des sections média vidéo
    has_video = any(line.startswith('m=video') for line in offer.sdp.splitlines())

    if has_video and relay_track:
        try:
            pc.addTrack(relay_track)
            logger.info("Piste vidéo partagée ajoutée à RTCPeerConnection")
        except Exception as e:
            logger.error(f"Échec de l'ajout de la piste vidéo : {e}")
    else:
        logger.info("Aucune section média vidéo dans l'offre SDP ou aucune piste relay disponible ; piste vidéo non ajoutée")

    # Créer la réponse SDP
    try:
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.info("Réponse SDP locale créée et définie")
    except Exception as e:
        logger.error(f"Échec de la création ou de la définition de la description locale : {e}")
        return web.Response(status=500, text="Échec de la création de la réponse SDP")

    # Attendre la collecte ICE
    await wait_for_ice_gathering_complete(pc, timeout=10)

    logger.debug(f"Réponse SDP générée :\n{pc.localDescription.sdp}")

    response_payload = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "id": connection_id
    }

    logger.debug(f"Payload de réponse envoyé : {response_payload}")

    return web.json_response(response_payload)

async def candidate(request):
    """
    Traite les candidats ICE envoyés par les clients.
    """
    try:
        params = await request.json()
        logger.info(f"Payload de candidat ICE reçu : {params}")
        connection_id = params["id"]
        candidate = RTCIceCandidate(
            sdpMid=params["sdpMid"],
            sdpMLineIndex=params["sdpMLineIndex"],
            candidate=params["candidate"]
        )
    except KeyError as e:
        logger.error(f"Clé manquante dans le payload du candidat ICE : {e}")
        return web.Response(status=400, text="Candidat ICE invalide")
    except Exception as e:
        logger.error(f"Échec de l'analyse du candidat ICE : {e}")
        return web.Response(status=400, text="Candidat ICE invalide")

    logger.info(f"Ajout du candidat ICE pour l'ID de connexion {connection_id} :\n{candidate.candidate}")

    pc = connections.get(connection_id)
    if not pc:
        logger.error(f"Aucune RTCPeerConnection trouvée pour l'ID de connexion : {connection_id}")
        return web.Response(status=400, text="ID de connexion invalide")

    try:
        await pc.addIceCandidate(candidate)
        logger.info("Candidat ICE ajouté avec succès")
    except Exception as e:
        logger.error(f"Échec de l'ajout du candidat ICE : {e}")
        return web.Response(status=400, text="Échec de l'ajout du candidat ICE")

    return web.Response(status=200, text="Candidat ICE ajouté avec succès")

async def on_shutdown(app):
    """
    Nettoie toutes les connexions peer lors de l'arrêt du serveur.
    """
    logger.info("Arrêt du serveur, fermeture de toutes les RTCPeerConnections...")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    connections.clear()
    logger.info("Toutes les RTCPeerConnections ont été fermées")

def main():
    app = web.Application()

    # Configuration de CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["POST", "GET", "OPTIONS"]
        )
    })

    # Définition des routes avec CORS
    resources = [
        ("/", "GET", index),
        ("/offer", "POST", offer),
        ("/candidate", "POST", candidate)
    ]

    for path, method, handler in resources:
        resource = app.router.add_resource(path)
        route = resource.add_route(method, handler)
        cors.add(route)

    # Enregistrement du gestionnaire d'arrêt
    app.on_shutdown.append(on_shutdown)

    port = 8080
    logger.info(f"Démarrage du serveur de signalement sur http://0.0.0.0:{port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
