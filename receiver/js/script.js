const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const remoteVideo = document.getElementById('remoteVideo');
let peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// Optimized WebSocket handling
signalingSocket.onopen = () => console.log('Signaling server connected');
signalingSocket.onmessage = async (event) => {
  const data = typeof event.data === 'string' ? JSON.parse(event.data) : await event.data.text().then(JSON.parse);
  if (data.offer) handleOffer(data.offer);
  if (data.candidate) handleCandidate(data.candidate);
};

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection(config);
  peerConnection.ontrack = (event) => remoteVideo.srcObject = event.streams[0]; // Directly set remote stream
  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      signalingSocket.send(JSON.stringify({ candidate: event.candidate }));
    }
  };
}

function handleOffer(offer) {
  setupPeerConnection();
  peerConnection.setRemoteDescription(new RTCSessionDescription(offer))
    .then(() => peerConnection.createAnswer())
    .then((answer) => peerConnection.setLocalDescription(answer))
    .then(() => signalingSocket.send(JSON.stringify({ answer: peerConnection.localDescription })))
    .catch(console.error);
}

function handleCandidate(candidate) {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate)).catch(console.error);
}
