const express = require('express');
const WebSocket = require('ws');
const app = express();
const PORT = 3000;

// Serve static files (for serving the client HTML and JS)
app.use(express.static('public'));

// Start HTTP server
const server = app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});

// WebSocket signaling server
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  console.log('A client connected');

  // Relay messages between clients
  ws.on('message', (message) => {
    wss.clients.forEach(client => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  });

  ws.on('close', () => {
    console.log('A client disconnected');
  });
});
