export function createChatWebSocket(
  onToken: (token: string) => void,
  onStart: () => void,
  onEnd: () => void,
  onError: (error: any) => void
) {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  const maxReconnectDelay = 30000;

  const connect = () => {
    ws = new WebSocket('ws://localhost:8000/ws/chat');

    ws.onopen = () => {
      reconnectAttempts = 0;
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'token') {
          onToken(data.payload.token);
        } else if (data.type === 'start') {
          onStart();
        } else if (data.type === 'end') {
          onEnd();
        } else if (data.type === 'error') {
          onError(data.payload);
        }
      } catch (e) {
        console.error('Error parsing WS message', e);
      }
    };

    ws.onclose = () => {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay);
      reconnectAttempts++;
      setTimeout(connect, delay);
    };

    ws.onerror = (err) => {
      onError(err);
    };
  };

  connect();

  return {
    sendMessage: (message: string, sessionId?: string) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message, sessionId }));
      }
    },
    disconnect: () => {
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    }
  };
}
