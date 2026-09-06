<script>
  import { userName, roomCode, connectionStatus, connectionError } from '../stores/room.js';
  import { connectWebSocket } from '../ws.js';

  let inputName = $userName || '';
  let inputRoom = $roomCode || '';
  let errorMsg = '';

  const quickRooms = ['design-lab', 'engineering-sync', 'founders-room'];

  function generateRandomRoom() {
    const adjectives = ['cosmic', 'zenith', 'vector', 'pulse', 'quantum', 'nexus', 'hyper'];
    const nouns = ['hub', 'lab', 'node', 'sync', 'space', 'vault'];
    const num = Math.floor(100 + Math.random() * 900);
    const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    inputRoom = `${adj}-${noun}-${num}`;
  }

  function handleJoin() {
    if (!inputName.trim()) {
      errorMsg = 'Please enter your name.';
      return;
    }
    if (!inputRoom.trim()) {
      errorMsg = 'Please enter a room code.';
      return;
    }

    errorMsg = '';
    userName.set(inputName.trim());
    roomCode.set(inputRoom.trim().toLowerCase());
    connectWebSocket(inputRoom.trim().toLowerCase(), inputName.trim());
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      handleJoin();
    }
  }
</script>

<div class="join-wrapper">
  <div class="join-card">
    <div class="logo-mark">
      <div class="logo-circle">Z</div>
    </div>

    <h1 class="join-title">Ziroo Room</h1>
    <p class="join-subtitle">
      Multiplayer chat with an AI participant and per-user context isolation.
    </p>

    {#if errorMsg || $connectionError}
      <div class="error-banner">
        <span>{errorMsg || $connectionError}</span>
      </div>
    {/if}

    <form class="join-form" on:submit|preventDefault={handleJoin}>
      <div class="input-group">
        <label for="name-input">Your name</label>
        <input
          id="name-input"
          type="text"
          bind:value={inputName}
          on:keydown={handleKeydown}
          placeholder="Name"
          maxlength="30"
          autocomplete="off"
          required
        />
      </div>

      <div class="input-group">
        <div class="label-row">
          <label for="room-input">Room code</label>
          <button type="button" class="gen-btn" on:click={generateRandomRoom}>
            Random code
          </button>
        </div>
        <input
          id="room-input"
          type="text"
          bind:value={inputRoom}
          on:keydown={handleKeydown}
          placeholder="Room code"
          maxlength="40"
          autocomplete="off"
          required
        />
      </div>

      <div class="preset-row">
        {#each quickRooms as room}
          <button
            type="button"
            class="preset-pill"
            class:active={inputRoom === room}
            on:click={() => (inputRoom = room)}
          >
            {room}
          </button>
        {/each}
      </div>

      <button type="submit" class="join-btn" disabled={$connectionStatus === 'connecting'}>
        {#if $connectionStatus === 'connecting'}
          <span>Connecting...</span>
        {:else}
          <span>Join Room</span>
        {/if}
      </button>
    </form>
  </div>
</div>

<style>
  .join-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    min-height: 100vh;
    padding: 24px;
    background: #000000;
    box-sizing: border-box;
    position: relative;
    z-index: 1;
  }
  .join-card {
    background: #121212;
    border: 1px solid #262626;
    border-radius: 16px;
    padding: 36px 32px;
    max-width: 400px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .logo-mark {
    margin-bottom: 14px;
  }
  .logo-circle {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #ffffff;
    color: #000000;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 800;
  }
  .join-title {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.02em;
    margin-bottom: 6px;
  }
  .join-subtitle {
    font-size: 13px;
    color: #8e8e8e;
    text-align: center;
    line-height: 1.45;
    margin-bottom: 24px;
  }
  .error-banner {
    width: 100%;
    background: #1a1a1a;
    border: 1px solid #333333;
    color: #ef4444;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
    margin-bottom: 16px;
    text-align: center;
  }
  .join-form {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .input-group label {
    font-size: 12px;
    font-weight: 600;
    color: #a8a8a8;
  }
  .label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .gen-btn {
    background: none;
    border: none;
    color: #a8a8a8;
    font-size: 11px;
    cursor: pointer;
    text-decoration: underline;
  }
  .gen-btn:hover {
    color: #ffffff;
  }
  .input-group input {
    background: #000000;
    border: 1px solid #262626;
    border-radius: 8px;
    color: #ffffff;
    font-size: 14px;
    padding: 10px 12px;
    outline: none;
    transition: border-color 0.15s;
  }
  .input-group input:focus {
    border-color: #555555;
  }
  .input-group input::placeholder {
    color: #525252;
  }
  .preset-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .preset-pill {
    background: #1a1a1a;
    border: 1px solid #262626;
    color: #8e8e8e;
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .preset-pill:hover, .preset-pill.active {
    background: #262626;
    border-color: #404040;
    color: #ffffff;
  }
  .join-btn {
    margin-top: 8px;
    background: #ffffff;
    color: #000000;
    border: none;
    font-size: 14px;
    font-weight: 700;
    padding: 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .join-btn:hover:not(:disabled) {
    opacity: 0.9;
  }
  .join-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>
