// client.js
let pc = null;

async function start() {
  pc = new RTCPeerConnection();

  // Indique que le client souhaite recevoir uniquement un flux vidéo
  pc.addTransceiver('video', { direction: 'recvonly' });

  pc.ontrack = (event) => {
    const video = document.getElementById('video');
    if (video.srcObject !== event.streams[0]) {
      video.srcObject = event.streams[0];
    }
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const response = await fetch('/offer', {
    method: 'POST',
    body: JSON.stringify({
      sdp: pc.localDescription.sdp,
      type: pc.localDescription.type,
    }),
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const answer = await response.json();
  await pc.setRemoteDescription(new RTCSessionDescription(answer));
}

window.onload = start;
