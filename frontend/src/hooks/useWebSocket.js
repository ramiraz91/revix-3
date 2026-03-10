import { useEffect, useRef, useCallback, useState } from 'react';
import { toast } from 'sonner';

const RECONNECT_DELAY = 3000;
const HEARTBEAT_INTERVAL = 30000;

export function useWebSocket(token) {
  const wsRef = useRef(null);
  const heartbeatRef = useRef(null);
  const reconnectRef = useRef(null);
  const [connected, setConnected] = useState(false);

  const playNotificationSound = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.5);
    } catch (e) {
      // Audio not available
    }
  }, []);

  const playUrgentSound = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'square';
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      // Three beeps
      [0, 0.2, 0.4].forEach(t => {
        osc.frequency.setValueAtTime(1200, ctx.currentTime + t);
        osc.frequency.setValueAtTime(0, ctx.currentTime + t + 0.1);
      });
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.8);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.8);
    } catch (e) {
      // Audio not available
    }
  }, []);

  const handleMessage = useCallback((event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'connected' || msg.type === 'pong') return;

      const isUrgent = msg.data?.urgente || msg.data?.popup;
      const title = msg.data?.titulo || msg.data?.message || 'Notificación';
      const body = msg.data?.mensaje || '';

      // Play sound
      if (msg.play_sound !== false) {
        if (isUrgent) {
          playUrgentSound();
        } else {
          playNotificationSound();
        }
      }

      // Show toast
      if (isUrgent) {
        toast.warning(title, { description: body, duration: 10000 });
      } else {
        toast.info(title, { description: body, duration: 5000 });
      }

      // Dispatch custom event for components that need to react
      window.dispatchEvent(new CustomEvent('ws-notification', { detail: msg }));
    } catch (e) {
      // ignore parse errors
    }
  }, [playNotificationSound, playUrgentSound]);

  const connect = useCallback(() => {
    if (!token) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/notifications?token=${token}`;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      setConnected(false);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      // Auto-reconnect
      reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [token, handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on cleanup
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { connected };
}
