// **********************************
// Receiver - Vital Elements
// **********************************

const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const remoteVideo = document.getElementById('remoteVideo');
let peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// **********************************
// Signaling and WebSocket Handling
// **********************************

signalingSocket.onopen = () => {
  console.log('Signaling server connected');
};

signalingSocket.onmessage = async (event) => {
  try {
    const data = await extractData(event);
    if (data.offer) {
      handleOffer(data.offer);
    } else if (data.candidate) {
      handleCandidate(data.candidate);
    }
  } catch (error) {
    console.error('Error processing WebSocket message:', error);
  }
};

async function extractData(event) {
  if (event.data instanceof Blob) {
    const textData = await event.data.text();
    return JSON.parse(textData);
  } else {
    return JSON.parse(event.data);
  }
}

// **********************************
// Peer Connection Setup for Receiving
// **********************************

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection(config);

  // Handle incoming remote stream
  peerConnection.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0]; // Display remote video
  };

  // Handle ICE candidates and send them to the signaling server
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
    .then(answer => peerConnection.setLocalDescription(answer))
    .then(() => {
      signalingSocket.send(JSON.stringify({ answer: peerConnection.localDescription }));
    })
    .catch(error => console.error('Error handling the offer:', error));
}

function handleCandidate(candidate) {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate))
    .catch(error => console.error('Error adding ICE candidate:', error));
}
