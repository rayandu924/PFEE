const signalingSocket = new WebSocket('ws://localhost:8080/ws');
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});
const remoteVideo = document.getElementById('remoteVideo');

// Gestion des ICE candidates
peerConnection.onicecandidate = event => {
    if (event.candidate) {
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

// Recevoir l'offre SDP de Peer A, envoyer une réponse SDP
signalingSocket.onmessage = message => {
    const data = JSON.parse(message.data);

    if (data.type === 'offer') {
        console.log("Offre SDP reçue :", data.sdp);
        const offer = new RTCSessionDescription({
            sdp: data.sdp,
            type: 'offer'
        });

        peerConnection.setRemoteDescription(offer)
            .then(() => {
                console.log("Offre SDP définie comme Remote Description.");
                return peerConnection.createAnswer();
            })
            .then(answer => {
                console.log("Réponse SDP créée :", answer);
                return peerConnection.setLocalDescription(answer);
            })
            .then(() => {
                console.log("Réponse SDP définie localement.");
                signalingSocket.send(JSON.stringify({
                    type: 'answer',
                    sdp: peerConnection.localDescription.sdp
                }));
                console.log("Réponse SDP envoyée via WebSocket.");
            });
    } else if (data.type === 'candidate') {
        console.log("Candidat ICE distant reçu :", data.candidate);
        const candidate = new RTCIceCandidate(data.candidate);
        peerConnection.addIceCandidate(candidate)
            .then(() => console.log("Candidat ICE distant ajouté."));
    }
};

// Afficher le flux vidéo reçu
peerConnection.ontrack = event => {
    console.log("Flux vidéo/audio reçu :", event.streams[0]);
    remoteVideo.srcObject = event.streams[0];
};
