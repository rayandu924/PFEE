const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const localVideo = document.getElementById('localVideo');
let localStream, peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// Optimized WebSocket handling
signalingSocket.onopen = () => {
  console.log('Signaling server connected');
  startLocalStream();
};

signalingSocket.onmessage = async (event) => {
  const data = typeof event.data === 'string' ? JSON.parse(event.data) : await event.data.text().then(JSON.parse);
  if (data.answer) handleAnswer(data.answer);
  if (data.candidate) handleCandidate(data.candidate);
};

function startLocalStream() {
  navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then((stream) => {
      localStream = stream;
      localVideo.srcObject = localStream;
      setupPeerConnection();
    })
    .catch(console.error);
}

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection(config);
  localStream.getTracks().forEach((track) => peerConnection.addTrack(track, localStream));
  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      signalingSocket.send(JSON.stringify({ candidate: event.candidate }));
    }
  };
  peerConnection.createOffer()
    .then((offer) => peerConnection.setLocalDescription(offer))
    .then(() => signalingSocket.send(JSON.stringify({ offer: peerConnection.localDescription })))
    .catch(console.error);
}

function handleAnswer(answer) {
  peerConnection.setRemoteDescription(new RTCSessionDescription(answer)).catch(console.error);
}

function handleCandidate(candidate) {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate)).catch(console.error);
}
