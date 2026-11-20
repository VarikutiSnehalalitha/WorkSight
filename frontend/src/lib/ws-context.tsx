"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export interface RealtimeMessage {
  type: string;
  payload?: Record<string, unknown>;
  receivedAt: number;
}

interface WsContextValue {
  connected: boolean;
  lastMessage: RealtimeMessage | null;
}

const WsContext = createContext<WsContextValue>({
  connected: false,
  lastMessage: null,
});

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<RealtimeMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) {
      setConnected(false);
      return;
    }

    let active = true;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pingInterval: ReturnType<typeof setInterval> | null = null;

    const connect = () => {
      if (!active) return;
      try {
        const ws = new WebSocket(`${WS_BASE}/ws?token=${encodeURIComponent(token)}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!active) return;
          setConnected(true);
          pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send("ping");
            }
          }, 25000);
        };

        ws.onmessage = (evt) => {
          try {
            const parsed = JSON.parse(evt.data);
            if (parsed.type && parsed.type !== "pong") {
              setLastMessage({
                type: parsed.type,
                payload: parsed.payload,
                receivedAt: Date.now(),
              });
            }
          } catch {
            // ignore malformed frames
          }
        };

        ws.onclose = () => {
          if (!active) return;
          setConnected(false);
          if (pingInterval) clearInterval(pingInterval);
          reconnectTimer = setTimeout(connect, 4000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        setConnected(false);
      }
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pingInterval) clearInterval(pingInterval);
      wsRef.current?.close();
    };
  }, [token]);

  return (
    <WsContext.Provider value={{ connected, lastMessage }}>
      {children}
    </WsContext.Provider>
  );
}

export function useRealtime() {
  return useContext(WsContext);
}
