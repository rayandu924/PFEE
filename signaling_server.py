import asyncio
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
from aiortc.sdp import candidate_from_sdp

# Dictionnaire pour stocker les connexions WebRTC
connected_peers = {}

# Ajouter un serveur STUN pour l'optimisation des candidats ICE
# Vous pouvez également ajouter un serveur TURN en tant que solution de secours
stun_server = "stun:stun.l.google.com:19302"
ice_servers = [{"urls": stun_server}]  # Ajouter un serveur TURN si nécessaire ici

# Gestionnaire WebSocket pour la signalisation
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    peer_id = str(id(ws))
    connected_peers[peer_id] = ws
    print(f"Nouveau pair connecté: {peer_id}")
    
    # Créer une nouvelle connexion WebRTC pour ce pair
    peer_connection = RTCPeerConnection(configuration={"iceServers": ice_servers})

    # Gérer les événements ICE
    @peer_connection.on("icecandidate")
    async def on_ice_candidate(candidate):
        if candidate:
            # Envoyer les candidats ICE au pair via WebSocket
            await ws.send_json({
                "type": "candidate",
                "candidate": candidate.to_sdp()
            })

    # Optimisation 2 : Minimiser les messages de signalisation
    # Utiliser uniquement les messages essentiels (offre/réponse et candidats ICE)
    
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = json.loads(msg.data)

            # Gérer une offre (offer) du pair
            if data["type"] == "offer":
                # Définir la description distante
                offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await peer_connection.setRemoteDescription(offer)

                # Créer et envoyer une réponse (answer)
                answer = await peer_connection.createAnswer()
                await peer_connection.setLocalDescription(answer)

                # Envoyer la réponse au pair
                await ws.send_json({
                    "type": peer_connection.localDescription.type,
                    "sdp": peer_connection.localDescription.sdp
                })

            # Gérer les candidats ICE
            elif data["type"] == "candidate":
                candidate = candidate_from_sdp(data["candidate"])
                await peer_connection.addIceCandidate(candidate)

        # Autres messages de signalisation peuvent être ignorés si non nécessaires

    return ws

# Lancer le serveur de signalisation WebSocket
async def main():
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    print("Serveur de signalisation WebRTC démarré sur ws://localhost:8080")
    
    # Garder le serveur en cours d'exécution
    while True:
        await asyncio.sleep(3600)

# Démarrage du serveur de signalisation
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Serveur arrêté.")
