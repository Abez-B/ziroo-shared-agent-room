<script>
  import { onMount, tick } from 'svelte';
  import { userName, roomCode, messages, activeUsers, connectionStatus } from '../stores/room.js';
  import { sendChatMessage, disconnectWebSocket } from '../ws.js';
  import MessageBubble from './MessageBubble.svelte';
  import TypingIndicator from './TypingIndicator.svelte';

  let inputContent = '';
  let messagesContainer;
  let copiedRoom = false;
  let inputElement;

  $: if ($messages) {
    scrollToBottom();
  }

  async function scrollToBottom() {
    await tick();
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  function handleSend() {
    const text = inputContent.trim();
    if (!text) return;
    try {
      sendChatMessage(text);
      inputContent = '';
      if (inputElement) inputElement.focus();
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === 'Escape') {
      inputContent = '';
    }
  }

  function insertAgentMention() {
    if (!inputContent.startsWith('@agent')) {
      inputContent = `@agent ${inputContent}`.trim() + ' ';
    }
    if (inputElement) inputElement.focus();
  }

  function usePrompt(promptText) {
    inputContent = promptText;
    if (inputElement) inputElement.focus();
  }

  function copyRoomCode() {
    navigator.clipboard.writeText($roomCode);
    copiedRoom = true;
    setTimeout(() => {
      copiedRoom = false;
    }, 2000);
  }

  onMount(() => {
    scrollToBottom();
    if (inputElement) inputElement.focus();
  });
</script>

<div class="chat-container">
  <!-- Top Header Bar -->
  <header class="chat-header">
    <div class="header-left">
      <button class="room-title-btn" on:click={copyRoomCode} title="Click to copy room code">
        <span class="live-dot" class:is-connected={$connectionStatus === 'connected'}></span>
        <span class="room-name">#{$roomCode}</span>
        <span class="copy-badge">{copiedRoom ? 'Copied' : 'Copy'}</span>
      </button>
    </div>

    <div class="header-right">
      <div class="members-info">
        {#each $activeUsers as u}
          <span class="member-pill" class:is-me={u === $userName}>
            {u === $userName ? `${u} (You)` : u}
          </span>
        {/each}
      </div>

      <button class="leave-btn" on:click={disconnectWebSocket} title="Leave room">
        Leave
      </button>
    </div>
  </header>

  {#if $connectionStatus !== 'connected'}
    <div class="connection-banner">
      <span>Connecting to room...</span>
    </div>
  {/if}

  <!-- Messages viewport -->
  <main class="messages-viewport" bind:this={messagesContainer}>
    {#if $messages.length === 0}
      <div class="empty-state">
        <div class="empty-avatar">Z</div>
        <h2 class="empty-title">#{$roomCode}</h2>
        <p class="empty-desc">
          Shared chat room with an AI participant. Address <strong>@agent</strong> to ask questions—each user's context is strictly isolated.
        </p>

        <div class="prompt-chips">
          <button class="prompt-chip" on:click={() => usePrompt('@agent Remember this: My secret project is Project Nova.')}>
            @agent Remember this: My secret project is Project Nova.
          </button>
          <button class="prompt-chip" on:click={() => usePrompt('@agent What is my secret project?')}>
            @agent What is my secret project?
          </button>
        </div>
      </div>
    {:else}
      <div class="messages-list">
        {#each $messages as message (message.id)}
          <MessageBubble {message} currentUserName={$userName} />
        {/each}
      </div>
    {/if}
  </main>

  <!-- Bottom Input Bar -->
  <footer class="input-dock">
    <TypingIndicator />

    <div class="input-pill">
      <button
        type="button"
        class="mention-btn"
        class:is-active={inputContent.includes('@agent')}
        on:click={insertAgentMention}
        title="Address @agent"
      >
        @agent
      </button>

      <input
        type="text"
        bind:this={inputElement}
        bind:value={inputContent}
        on:keydown={handleKeydown}
        placeholder="Message or ask @agent..."
        class="message-input"
        autocomplete="off"
      />

      <button
        type="button"
        class="send-btn"
        disabled={!inputContent.trim()}
        on:click={handleSend}
      >
        Send
      </button>
    </div>
  </footer>
</div>

<style>
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
    background: #000000;
    color: #ffffff;
    position: relative;
    z-index: 1;
    overflow: hidden;
  }

  /* ── Header ── */
  .chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: #000000;
    border-bottom: 1px solid #262626;
    flex-shrink: 0;
  }
  .header-left {
    display: flex;
    align-items: center;
  }
  .room-title-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
  }
  .room-name {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
  }
  .live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #525252;
    display: inline-block;
    transition: background-color 0.2s;
  }
  .live-dot.is-connected {
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
  }
  .connection-banner {
    background: #1a1a1a;
    border-bottom: 1px solid #262626;
    padding: 6px 16px;
    text-align: center;
    font-size: 11px;
    color: #a8a8a8;
  }
  .copy-badge {
    font-size: 10.5px;
    color: #737373;
    border: 1px solid #262626;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .members-info {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .member-pill {
    font-size: 11px;
    background: #121212;
    border: 1px solid #262626;
    color: #8e8e8e;
    padding: 3px 8px;
    border-radius: 9999px;
  }
  .member-pill.is-me {
    color: #ffffff;
    border-color: #404040;
    font-weight: 600;
  }
  .leave-btn {
    background: none;
    border: none;
    color: #737373;
    font-size: 12.5px;
    cursor: pointer;
    padding: 4px 8px;
    transition: color 0.15s;
  }
  .leave-btn:hover {
    color: #ffffff;
  }

  /* ── Messages Viewport ── */
  .messages-viewport {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    background: #000000;
  }
  .messages-list {
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
    gap: 2px;
  }

  /* ── Empty State ── */
  .empty-state {
    margin: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    max-width: 440px;
    text-align: center;
    padding: 32px 20px;
  }
  .empty-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #121212;
    border: 1px solid #262626;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 12px;
  }
  .empty-title {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 6px;
  }
  .empty-desc {
    font-size: 13px;
    color: #8e8e8e;
    line-height: 1.45;
    margin-bottom: 20px;
  }
  .prompt-chips {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .prompt-chip {
    background: #121212;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    color: #a8a8a8;
    font-size: 12.5px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .prompt-chip:hover {
    background: #1a1a1a;
    border-color: #363636;
    color: #ffffff;
  }

  /* ── Input Dock (Instagram Pill Style) ── */
  .input-dock {
    padding: 10px 20px 16px 20px;
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
    box-sizing: border-box;
    background: #000000;
  }
  .input-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #121212;
    border: 1px solid #262626;
    border-radius: 24px;
    padding: 6px 10px 6px 12px;
    transition: border-color 0.15s;
  }
  .input-pill:focus-within {
    border-color: #404040;
  }
  .mention-btn {
    background: #262626;
    border: 1px solid #363636;
    color: #ffffff;
    font-size: 11.5px;
    font-weight: 600;
    padding: 5px 9px;
    border-radius: 14px;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .mention-btn:hover, .mention-btn.is-active {
    background: #ffffff;
    color: #000000;
    border-color: #ffffff;
  }
  .message-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #ffffff;
    font-size: 13.5px;
    font-family: inherit;
  }
  .message-input::placeholder {
    color: #737373;
  }
  .send-btn {
    background: none;
    border: none;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    padding: 4px 8px;
    transition: opacity 0.15s;
  }
  .send-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  .send-btn:not(:disabled):hover {
    opacity: 0.8;
  }
</style>
