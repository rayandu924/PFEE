const express = require('express');
const WebSocket = require('ws');
const app = express();
const PORT = 3000;

app.use(express.static('public'));

const server = app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  ws.isAlive = true;
  
  ws.on('pong', () => {
    ws.isAlive = true;  // Reset isAlive on pong
  });

  // Reduce ping interval to check for dead connections more frequently (10 seconds)
  const interval = setInterval(() => {
    wss.clients.forEach(client => {
      if (!client.isAlive) return client.terminate(); // Terminate dead connections
      client.isAlive = false;
      client.ping();  // Send a ping to verify if client is alive
    });
  }, 10000); // Ping every 10 seconds

  ws.on('message', (message) => {
    try {
      const parsedMessage = JSON.parse(message);

      // Broadcast only to specific peers, not all clients
      if (parsedMessage.candidate || parsedMessage.offer || parsedMessage.answer) {
        wss.clients.forEach(client => {
          // Send only to clients that are ready and not the sender
          if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(message);
          }
        });
      }
    } catch (error) {
      console.error('Invalid WebSocket message:', error);
      // Optionally, send error feedback to the client
      ws.send(JSON.stringify({ error: 'Invalid message format' }));
    }
  });

  ws.on('close', () => {
    clearInterval(interval); // Clear ping interval on close
    console.log('A client disconnected');
  });
});
