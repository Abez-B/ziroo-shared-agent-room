import { messages, activeUsers, connectionStatus, connectionError, typingState, isJoined } from './stores/room.js';

let socket = null;
let currentRoom = null;
let currentUser = null;
let reconnectTimer = null;
let shouldReconnect = true;

export function connectWebSocket(room, user) {
  if (socket) {
    disconnectWebSocket();
  }

  currentRoom = room.trim();
  currentUser = user.trim();
  shouldReconnect = true;

  connectionStatus.set('connecting');
  connectionError.set(null);

  // Compute websocket host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
  const wsUrl = `${protocol}//${host}/ws/${encodeURIComponent(currentRoom)}?name=${encodeURIComponent(currentUser)}`;

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      connectionStatus.set('connected');
      isJoined.set(true);
      sessionStorage.setItem('ziroo_room', currentRoom);
      sessionStorage.setItem('ziroo_user', currentUser);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleIncomingEvent(data);
      } catch (err) {
        console.error('Failed to parse incoming WS message:', err, event.data);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket error encountered:', err);
      connectionError.set('Connection error occurred.');
    };

    socket.onclose = (event) => {
      connectionStatus.set('disconnected');
      if (shouldReconnect && event.code !== 1000 && event.code !== 1008) {
        // Attempt clean reconnect after short delay
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
          if (shouldReconnect) {
            connectWebSocket(currentRoom, currentUser);
          }
        }, 2000);
      }
    };
  } catch (err) {
    connectionStatus.set('error');
    connectionError.set(err.message || 'Failed to initialize WebSocket');
  }
}

function handleIncomingEvent(event) {
  const { type, payload } = event;

  switch (type) {
    case 'history_sync':
      if (payload.messages) {
        messages.set(payload.messages);
      }
      if (payload.active_users) {
        activeUsers.set(payload.active_users);
      }
      break;

    case 'chat_message':
      messages.update((prev) => [...prev, payload]);
      break;

    case 'system_notice':
      messages.update((prev) => [
        ...prev,
        {
          id: 'sys-' + Date.now() + Math.random().toString(36).substr(2, 4),
          room_code: currentRoom,
          user_name: 'system',
          role: 'system',
          content: payload.content,
          created_at: new Date().toISOString()
        }
      ]);
      break;

    case 'room_state':
      if (payload.active_users) {
        activeUsers.set(payload.active_users);
      }
      break;

    case 'typing':
      typingState.set({
        isTyping: !!payload.is_typing,
        targetUser: payload.target_user || null,
        userName: payload.user_name || 'agent'
      });
      break;

    default:
      console.log('Unhandled event type:', type, payload);
  }
}

export function sendChatMessage(content) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error('WebSocket is not connected');
  }
  socket.send(JSON.stringify({ content }));
}

export function disconnectWebSocket() {
  shouldReconnect = false;
  clearTimeout(reconnectTimer);
  if (socket) {
    socket.close(1000, 'User left room');
    socket = null;
  }
  connectionStatus.set('disconnected');
  isJoined.set(false);
}
