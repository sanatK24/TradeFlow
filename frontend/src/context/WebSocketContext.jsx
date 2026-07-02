import React, { createContext, useContext, useEffect, useState, useRef } from "react";

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children }) => {
    const [connected, setConnected] = useState(false);
    const socketRef = useRef(null);
    const handlersRef = useRef({}); // message_type -> Set of callbacks

    const subscribe = (type, callback) => {
        if (!handlersRef.current[type]) {
            handlersRef.current[type] = new Set();
        }
        handlersRef.current[type].add(callback);
        return () => unsubscribe(type, callback);
    };

    const unsubscribe = (type, callback) => {
        if (handlersRef.current[type]) {
            handlersRef.current[type].delete(callback);
            if (handlersRef.current[type].size === 0) {
                delete handlersRef.current[type];
            }
        }
    };

    const connect = (token) => {
        if (socketRef.current) {
            socketRef.current.close();
        }

        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        // Connect to FastAPI ws port (default 8000 in dev)
        const wsUrl = `ws://localhost:8001/ws${token ? `?token=${token}` : ""}`;
        
        console.log("Connecting to WebSocket:", wsUrl);
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WebSocket connected.");
            setConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                const { type, data } = message;
                
                if (handlersRef.current[type]) {
                    handlersRef.current[type].forEach((cb) => cb(data));
                }
            } catch (err) {
                // If it's a simple string like "pong"
                if (event.data === "pong") {
                    // console.log("WebSocket pong received");
                } else {
                    console.error("Error parsing WebSocket message:", err);
                }
            }
        };

        ws.onclose = () => {
            console.log("WebSocket disconnected.");
            setConnected(false);
            socketRef.current = null;
        };

        ws.onerror = (err) => {
            console.error("WebSocket error:", err);
        };

        socketRef.current = ws;
    };

    const disconnect = () => {
        if (socketRef.current) {
            socketRef.current.close();
            socketRef.current = null;
            setConnected(false);
        }
    };

    // Heartbeat to keep connection alive
    useEffect(() => {
        const interval = setInterval(() => {
            if (socketRef.current && connected) {
                socketRef.current.send("ping");
            }
        }, 10000);

        return () => {
            clearInterval(interval);
            disconnect();
        };
    }, [connected]);

    return (
        <WebSocketContext.Provider value={{ connected, subscribe, connect, disconnect }}>
            {children}
        </WebSocketContext.Provider>
    );
};
