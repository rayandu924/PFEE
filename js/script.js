const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
let localStream, peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// When signaling server connection is open, start local video stream
signalingSocket.onopen = () => {
  console.log('Connected to the signaling server');
  startLocalStream();
};

// Handle WebSocket messages from the signaling server
signalingSocket.onmessage = async (event) => {
  try {
    let data;

    // Log the type of event.data to check what is being received
    console.log("Received data type:", typeof event.data);

    // Check if event.data is a Blob
    if (event.data instanceof Blob) {
      const textData = await event.data.text(); // Convert Blob to text
      console.log("Blob data received:", textData);
      data = JSON.parse(textData); // Parse the text to JSON
    } else {
      console.log("Non-Blob data received:", event.data);
      data = JSON.parse(event.data); // If not Blob, directly parse
    }

    if (data.offer) {
      handleOffer(data.offer);
    } else if (data.answer) {
      handleAnswer(data.answer);
    } else if (data.candidate) {
      handleCandidate(data.candidate);
    }
  } catch (error) {
    console.error("Error processing WebSocket message:", error);
  }
};

function startLocalStream() {
  navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then(stream => {
      localStream = stream;
      localVideo.srcObject = localStream;
      setupPeerConnection();
    })
    .catch(error => console.error('Error accessing media devices:', error));
}

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection(config);

  // Add local stream tracks to the peer connection
  localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

  // Handle incoming remote stream
  peerConnection.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0];
  };

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

function handleOffer(offer) {
  peerConnection.setRemoteDescription(new RTCSessionDescription(offer))
    .then(() => {
      return peerConnection.createAnswer();
    })
    .then(answer => {
      return peerConnection.setLocalDescription(answer);
    })
    .then(() => {
      signalingSocket.send(JSON.stringify({ answer: peerConnection.localDescription }));
    })
    .catch(error => console.error('Error handling the offer:', error));
}

function handleAnswer(answer) {
  peerConnection.setRemoteDescription(new RTCSessionDescription(answer))
    .catch(error => console.error('Error setting remote description:', error));
}

function handleCandidate(candidate) {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate))
    .catch(error => console.error('Error adding ICE candidate:', error));
}
