import asyncio
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp

# Dictionnaire pour stocker les connexions WebRTC
connected_peers = {}

# Gestionnaire WebSocket pour la signalisation
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    peer_id = str(id(ws))
    connected_peers[peer_id] = ws
    print(f"Nouveau pair connecté: {peer_id}")
    
    try:
        # Créer une nouvelle connexion WebRTC pour ce pair avec la configuration des serveurs STUN/TURN
        peer_connection = RTCPeerConnection()
        print("Nouvelle connexion WebRTC créée pour le pair:", peer_id)

        # Gérer les événements ICE
        @peer_connection.on("icecandidate")
        async def on_ice_candidate(candidate):
            if candidate:
                print("Candidat ICE généré pour le pair:", peer_id, candidate.to_sdp())
                await ws.send_json({
                    "type": "candidate",
                    "candidate": candidate.to_sdp()
                })

        # Attente des messages WebSocket du client
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(f"Message reçu du pair {peer_id}: {data}")

                # Gérer une offre (offer) du pair
                if data["type"] == "offer":
                    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                    print(f"Offre SDP reçue du pair {peer_id}: {offer.sdp}")
                    await peer_connection.setRemoteDescription(offer)

                    # Créer et envoyer une réponse (answer)
                    answer = await peer_connection.createAnswer()
                    await peer_connection.setLocalDescription(answer)

                    print(f"Réponse SDP envoyée au pair {peer_id}: {answer.sdp}")
                    await ws.send_json({
                        "type": peer_connection.localDescription.type,
                        "sdp": peer_connection.localDescription.sdp
                    })

                # Gérer les candidats ICE
                elif data["type"] == "candidate":
                    print(f"Candidat ICE reçu du pair {peer_id}: {data['candidate']}")
                    candidate = candidate_from_sdp(data["candidate"])
                    await peer_connection.addIceCandidate(candidate)

            else:
                print(f"Message inattendu reçu du pair {peer_id}: {msg}")

    except Exception as e:
        print(f"Erreur lors du traitement du pair {peer_id}: {e}")
    finally:
        # Retirer la connexion à la fin de la session WebSocket
        del connected_peers[peer_id]
        print(f"Connexion fermée pour le pair {peer_id}")

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
