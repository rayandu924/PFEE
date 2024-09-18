// **********************************
// Sender - Vital Elements
// **********************************

const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const localVideo = document.getElementById('localVideo');
let localStream, peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// **********************************
// Signaling and WebSocket Handling
// **********************************

signalingSocket.onopen = () => {
  console.log('Signaling server connected');
  startLocalStream();
};

signalingSocket.onmessage = async (event) => {
  try {
    const data = await extractData(event);
    if (data.answer) {
      handleAnswer(data.answer);
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
// Local Stream and Peer Connection Setup
// **********************************

function startLocalStream() {
  navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then(stream => {
      localStream = stream;
      localVideo.srcObject = localStream; // Display local video
      setupPeerConnection();
    })
    .catch(error => console.error('Error accessing media devices:', error));
}

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection(config);

  // Add local stream tracks to the peer connection
  localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

  // Handle ICE candidates and send them to the signaling server
  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      signalingSocket.send(JSON.stringify({ candidate: event.candidate }));
    }
  };

  // Create and send an offer to the signaling server
  peerConnection.createOffer()
    .then(offer => {
      return peerConnection.setLocalDescription(offer);
    })
    .then(() => {
      signalingSocket.send(JSON.stringify({ offer: peerConnection.localDescription }));
    })
    .catch(error => console.error('Error creating an offer:', error));
}

function handleAnswer(answer) {
  peerConnection.setRemoteDescription(new RTCSessionDescription(answer))
    .catch(error => console.error('Error setting remote description:', error));
}

function handleCandidate(candidate) {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate))
    .catch(error => console.error('Error adding ICE candidate:', error));
}
