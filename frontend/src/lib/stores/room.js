import { writable, derived } from 'svelte/store';

export const userName = writable(sessionStorage.getItem('ziroo_user') || '');
export const roomCode = writable(sessionStorage.getItem('ziroo_room') || '');
export const isJoined = writable(false);
export const connectionStatus = writable('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
export const connectionError = writable(null);
export const messages = writable([]);
export const activeUsers = writable([]);
export const typingState = writable({ isTyping: false, targetUser: null, userName: 'agent' });

export function resetRoomState() {
  messages.set([]);
  activeUsers.set([]);
  typingState.set({ isTyping: false, targetUser: null, userName: 'agent' });
  connectionStatus.set('disconnected');
  connectionError.set(null);
  isJoined.set(false);
}
