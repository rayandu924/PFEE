const signalingSocket = new WebSocket('ws://localhost:8080/ws');
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});
const localVideo = document.getElementById('localVideo');
let hasReceivedAnswer = false;  // Flag pour vérifier si on a reçu une réponse

// Capture vidéo/audio depuis la caméra/microphone
navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
        console.log("Capture de la vidéo et de l'audio réussie.");
        localVideo.srcObject = stream;

        // Ajoute les pistes du flux à la connexion WebRTC
        stream.getTracks().forEach(track => {
            peerConnection.addTrack(track, stream);
            console.log(`Piste ajoutée : ${track.kind}`);
        });
    })
    .catch(error => console.error('Erreur d’accès aux médias.', error));

// Gestion des ICE candidates
peerConnection.onicecandidate = event => {
    if (event.candidate && hasReceivedAnswer) {  // N'envoyer les candidats ICE que si une réponse a été reçue
        if (signalingSocket.readyState === WebSocket.OPEN) {
            console.log("Candidat ICE local généré :", event.candidate);
            signalingSocket.send(JSON.stringify({
                type: 'candidate',
                candidate: event.candidate
            }));
        } else {
            console.log("WebSocket is not open, cannot send candidate.");
        }
    }
};

// Attendre que le WebSocket soit ouvert avant d'envoyer l'offre SDP
signalingSocket.onopen = () => {
    console.log("Connexion WebSocket établie.");
    
    // Créer une offre SDP et l'envoyer via WebSocket
    peerConnection.createOffer()
        .then(offer => {
            console.log("Offre SDP créée :", offer);
            return peerConnection.setLocalDescription(offer);
        })
        .then(() => {
            console.log("Offre SDP définie localement.");
            signalingSocket.send(JSON.stringify({
                type: 'offer',
                sdp: peerConnection.localDescription.sdp
            }));
            console.log("Offre SDP envoyée via WebSocket.");
        })
        .catch(error => console.error('Erreur de création de l’offre.', error));
};

// Recevoir la réponse SDP de Peer B et les candidats ICE
signalingSocket.onmessage = message => {
    const data = JSON.parse(message.data);

    if (data.type === 'answer') {
        console.log("Réponse SDP reçue :", data.sdp);
        const answer = new RTCSessionDescription({
            sdp: data.sdp,
            type: 'answer'
        });
        peerConnection.setRemoteDescription(answer)
            .then(() => {
                console.log("Réponse SDP définie comme Remote Description.");
                hasReceivedAnswer = true;  // Une réponse a été reçue, nous pouvons commencer à échanger des candidats ICE
            });
    } else if (data.type === 'candidate' && hasReceivedAnswer) {  // N'accepter les candidats ICE que si une réponse a été reçue
        console.log("Candidat ICE distant reçu :", data.candidate);
        const candidate = new RTCIceCandidate(data.candidate);
        peerConnection.addIceCandidate(candidate)
            .then(() => console.log("Candidat ICE distant ajouté."));
    }
};

signalingSocket.onerror = error => {
    console.error("Erreur WebSocket :", error);
};
