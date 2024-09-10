const signalingSocket = new WebSocket('ws://localhost:8080/ws');
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});
const localVideo = document.getElementById('localVideo');

// Capture vidéo/audio depuis la caméra/microphone
navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
        // Affiche le flux vidéo local dans l'élément vidéo
        localVideo.srcObject = stream;

        // Ajoute les pistes du flux (vidéo/audio) à la connexion WebRTC
        stream.getTracks().forEach(track => peerConnection.addTrack(track, stream));
    })
    .catch(error => console.error('Erreur d’accès aux médias.', error));

// Gestion des ICE candidates
peerConnection.onicecandidate = event => {
    if (event.candidate) {
        signalingSocket.send(JSON.stringify({
            type: 'candidate',
            candidate: event.candidate
        }));
    }
};

// Créer une offre SDP et l'envoyer via WebSocket
peerConnection.createOffer()
    .then(offer => {
        return peerConnection.setLocalDescription(offer);
    })
    .then(() => {
        signalingSocket.send(JSON.stringify({
            type: 'offer',
            sdp: peerConnection.localDescription.sdp
        }));
    })
    .catch(error => console.error('Erreur de création de l’offre.', error));

// Recevoir la réponse SDP de Peer B et les candidats ICE
signalingSocket.onmessage = message => {
    const data = JSON.parse(message.data);

    if (data.type === 'answer') {
        const answer = new RTCSessionDescription({
            sdp: data.sdp,
            type: 'answer'
        });
        peerConnection.setRemoteDescription(answer);
    } else if (data.type === 'candidate') {
        const candidate = new RTCIceCandidate(data.candidate);
        peerConnection.addIceCandidate(candidate);
    }
};
