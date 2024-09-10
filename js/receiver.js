const signalingSocket = new WebSocket('ws://localhost:8080/ws');
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});
const remoteVideo = document.getElementById('remoteVideo');

// Gestion des ICE candidates
peerConnection.onicecandidate = event => {
    if (event.candidate) {
        signalingSocket.send(JSON.stringify({
            type: 'candidate',
            candidate: event.candidate
        }));
    }
};

// Recevoir l'offre SDP de Peer A, envoyer une réponse SDP
signalingSocket.onmessage = message => {
    const data = JSON.parse(message.data);

    if (data.type === 'offer') {
        const offer = new RTCSessionDescription({
            sdp: data.sdp,
            type: 'offer'
        });

        peerConnection.setRemoteDescription(offer)
            .then(() => peerConnection.createAnswer())
            .then(answer => peerConnection.setLocalDescription(answer))
            .then(() => {
                signalingSocket.send(JSON.stringify({
                    type: 'answer',
                    sdp: peerConnection.localDescription.sdp
                }));
            });
    } else if (data.type === 'candidate') {
        const candidate = new RTCIceCandidate(data.candidate);
        peerConnection.addIceCandidate(candidate);
    }
};

// Afficher le flux vidéo reçu
peerConnection.ontrack = event => {
    remoteVideo.srcObject = event.streams[0];
};
