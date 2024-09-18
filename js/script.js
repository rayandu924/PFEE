//faire que de la diffusion finalement pas de reception
// reception uniquement coté casque vr
// prendre un flux 
// clean le code et enlever les choses inutiles
const signalingServerUrl = 'ws://localhost:3000'; // WebSocket signaling server URL
const signalingSocket = new WebSocket(signalingServerUrl);
const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
const codecToForce = 'AV1'; // for example, 'H264' or 'VP8' or 'VP9' or 'AV1'
let localStream, peerConnection;

const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// Camera configuration (resolution, frame rate, etc.)
const cameraConstraints = {
    video: {
        width: { ideal: 7680 },  // Résolution idéale : 8K (7680 pixels de large)
        height: { ideal: 4320 }, // Résolution idéale : 8K (4320 pixels de haut)
        frameRate: { ideal: 60, max: 60 },  // 60 FPS constant
        aspectRatio: 16 / 9,  // Aspect ratio : 16:9
        facingMode: 'user',  // 'user' pour la caméra frontale, 'environment' pour la caméra arrière
    },
    audio: false  // Pas d'audio
};  

// When signaling server connection is open, start local video stream
signalingSocket.onopen = () => {
  console.log('Signaling server connected');
  startLocalStream();
};

// Handle WebSocket messages from the signaling server
signalingSocket.onmessage = async (event) => {
  try {
    const data = await extractData(event);
    if (data.offer) {
      handleOffer(data.offer);
    } else if (data.answer) {
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

function startLocalStream() {
  navigator.mediaDevices.getUserMedia(cameraConstraints)
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

  // Create and send an offer to the signaling server with forced codec
  peerConnection.createOffer()
    .then(offer => {
      let modifiedSDP = forceCodecInSDP(offer.sdp, codecToForce);
      offer.sdp = modifiedSDP;
      console.log('Send Offer SDP:', offer.sdp);
      return peerConnection.setLocalDescription(offer);
    })
    .then(() => {
      signalingSocket.send(JSON.stringify({ offer: peerConnection.localDescription }));
    })
    .catch(error => console.error('Error creating an offer:', error));

  // Log connection state changes
  peerConnection.oniceconnectionstatechange = () => {
    if (peerConnection.iceConnectionState === 'connected') {
      logCodecInfo();  // Log codec info when the connection is established
    }
  };
}

function handleOffer(offer) {
  peerConnection.setRemoteDescription(new RTCSessionDescription(offer))
    .then(() => peerConnection.createAnswer())
    .then(answer => {
      let modifiedSDP = forceCodecInSDP(answer.sdp, codecToForce);
      answer.sdp = modifiedSDP;
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

// Function to log codec information
function logCodecInfo() {
  peerConnection.getStats(null).then(stats => {
    stats.forEach(report => {
      if (report.type === 'inbound-rtp' || report.type === 'outbound-rtp') {
        const codecId = report.codecId;
        stats.forEach(innerReport => {
          if (innerReport.id === codecId) {
            console.log(`Using codec: ${innerReport.mimeType}`);
          }
        });
      }
    });
  }).catch(error => console.error('Error retrieving stats:', error));
}

// Function to force the codec (H.264 or another) in the SDP
function forceCodecInSDP(sdp, codec) {
  const lines = sdp.split('\r\n');
  let mLineIndex = null;
  let codecRtpMap = null;

  // Find the m=video line
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].indexOf('m=video') === 0) {
      mLineIndex = i;
      break;
    }
  }

  // If the m=video line was found, find the corresponding codec
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].indexOf(`a=rtpmap`) === 0 && lines[i].indexOf(codec) !== -1) {
      codecRtpMap = lines[i].split(' ')[0].split(':')[1];
      break;
    }
  }

  // If the codec was found, modify the m=video line to prioritize the codec
  if (mLineIndex !== null && codecRtpMap !== null) {
    const mLineElements = lines[mLineIndex].split(' ');
    const newMLine = [mLineElements[0], mLineElements[1], mLineElements[2], codecRtpMap, ...mLineElements.slice(3).filter(el => el !== codecRtpMap)];
    lines[mLineIndex] = newMLine.join(' ');
  }

  return lines.join('\r\n');
}
