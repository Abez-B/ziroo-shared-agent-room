<script>
  import { typingState, userName } from '../stores/room.js';
</script>

{#if $typingState.isTyping}
  <div class="typing-wrap">
    <div class="typing-card">
      <div class="agent-avatar">AI</div>
      <span class="typing-text">
        Agent is typing for <strong class="target-name">{$typingState.targetUser === $userName ? 'you' : $typingState.targetUser}</strong>
      </span>
      <div class="dots">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>
  </div>
{/if}

<style>
  .typing-wrap {
    display: flex;
    justify-content: flex-start;
    margin: 4px 0 8px 0;
  }
  .typing-card {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #121212;
    border: 1px solid #262626;
    padding: 6px 12px;
    border-radius: 9999px;
  }
  .agent-avatar {
    width: 16px;
    height: 16px;
    background: #ffffff;
    color: #000000;
    border-radius: 50%;
    font-size: 8.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .typing-text {
    font-size: 11.5px;
    color: #a8a8a8;
  }
  .target-name {
    color: #ffffff;
    font-weight: 600;
  }
  .dots {
    display: flex;
    align-items: center;
    gap: 3px;
  }
  .dot {
    width: 3.5px;
    height: 3.5px;
    border-radius: 50%;
    background: #ffffff;
    animation: pulse-dot 1.2s infinite ease-in-out;
  }
  .dot:nth-child(2) {
    animation-delay: 0.2s;
  }
  .dot:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes pulse-dot {
    0%, 80%, 100% {
      transform: scale(0.6);
      opacity: 0.3;
    }
    40% {
      transform: scale(1.1);
      opacity: 1;
    }
  }
</style>
