import { useCallback, useEffect, useRef, useState } from 'react';
import { WS_URL } from '../utils/constants';

/**
 * WebSocket hook for connecting to the MAD pipeline server.
 * Handles connection lifecycle, reconnection, and message parsing.
 */
export function useWebSocket() {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback((onMessage) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
    };
    ws.onerror = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        onMessage(event);
      } catch { /* ignore malformed */ }
    };

    return ws;
  }, []);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const close = useCallback(() => {
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  return { connect, send, close, connected };
}
