<script>
  import { renderMarkdown } from '../markdown.js';

  export let message;
  export let currentUserName = '';

  let copied = false;

  $: isSelf = message.role === 'human' && message.user_name === currentUserName;
  $: isOther = message.role === 'human' && message.user_name !== currentUserName;
  $: isAgent = message.role === 'agent';
  $: isSystem = message.role === 'system';

  function formatTime(isoString) {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  function getInitials(name) {
    if (!name) return '?';
    return name.slice(0, 2).toUpperCase();
  }

  function copyContent() {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    copied = true;
    setTimeout(() => {
      copied = false;
    }, 1800);
  }
</script>

{#if isSystem}
  <div class="system-container">
    <div class="system-badge" class:is-warning={message.content.includes('⚠️')}>
      <span class="system-text">{message.content}</span>
      <span class="system-time">{formatTime(message.created_at)}</span>
    </div>
  </div>
{:else if isAgent}
  <div class="agent-container">
    <div class="agent-card">
      <div class="agent-header">
        <div class="agent-identity">
          <div class="agent-avatar">AI</div>
          <span class="agent-name">Agent</span>
        </div>
        {#if message.target_user}
          <div class="target-tag">
            <span>to {message.target_user === currentUserName ? 'you' : message.target_user}</span>
          </div>
        {/if}
        <div class="agent-meta-right">
          <button class="copy-msg-btn" on:click={copyContent} title="Copy response">
            {copied ? 'Copied' : 'Copy'}
          </button>
          <span class="msg-time">{formatTime(message.created_at)}</span>
        </div>
      </div>
      <div class="agent-body markdown-content">
        {@html renderMarkdown(message.content)}
      </div>
    </div>
  </div>
{:else if isSelf}
  <div class="self-container">
    <div class="self-bubble">
      <div class="msg-content">{message.content}</div>
      <div class="self-meta">
        <span class="meta-time">{formatTime(message.created_at)}</span>
      </div>
    </div>
  </div>
{:else if isOther}
  <div class="other-container">
    <div class="other-avatar">
      {getInitials(message.user_name)}
    </div>
    <div class="other-bubble-wrap">
      <div class="other-sender-name">{message.user_name}</div>
      <div class="other-bubble">
        <div class="msg-content">{message.content}</div>
        <div class="other-meta">
          <span class="meta-time">{formatTime(message.created_at)}</span>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  /* ── System Notice ── */
  .system-container {
    display: flex;
    justify-content: center;
    margin: 12px 0;
    animation: fadeIn 0.2s ease-out;
  }
  .system-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    font-size: 11px;
    color: #737373;
    letter-spacing: -0.01em;
  }
  .system-badge.is-warning {
    color: #ef4444;
  }
  .system-time {
    color: #525252;
    font-size: 10px;
  }

  /* ── Agent Card ── */
  .agent-container {
    display: flex;
    justify-content: flex-start;
    margin: 8px 0;
    width: 100%;
    animation: fadeIn 0.2s ease-out;
  }
  .agent-card {
    background: #121212;
    border: 1px solid #262626;
    border-radius: 18px;
    padding: 14px 18px;
    max-width: 82%;
    min-width: 260px;
  }
  .agent-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1f1f1f;
  }
  .agent-identity {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .agent-avatar {
    width: 20px;
    height: 20px;
    background: #ffffff;
    color: #000000;
    border-radius: 50%;
    font-size: 9.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: -0.05em;
  }
  .agent-name {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
  }
  .target-tag {
    font-size: 10.5px;
    color: #a8a8a8;
    background: #1c1c1c;
    border: 1px solid #262626;
    padding: 1px 7px;
    border-radius: 9999px;
  }
  .agent-meta-right {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
  }
  .copy-msg-btn {
    background: none;
    border: 1px solid #262626;
    color: #737373;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .copy-msg-btn:hover {
    color: #ffffff;
    border-color: #444444;
  }
  .msg-time {
    font-size: 10px;
    color: #737373;
  }

  /* ── Agent Markdown Styling ── */
  .markdown-content {
    font-size: 13.5px;
    line-height: 1.55;
    color: #f5f5f5;
    word-break: break-word;
  }
  .markdown-content :global(p) {
    margin: 0 0 8px 0;
  }
  .markdown-content :global(p:last-child) {
    margin-bottom: 0;
  }
  .markdown-content :global(strong) {
    color: #ffffff;
    font-weight: 700;
  }
  .markdown-content :global(em) {
    color: #e5e5e5;
  }
  .markdown-content :global(ul), .markdown-content :global(ol) {
    margin: 6px 0 8px 20px;
    padding: 0;
  }
  .markdown-content :global(li) {
    margin-bottom: 4px;
  }
  .markdown-content :global(code) {
    font-family: var(--font-mono, monospace);
    font-size: 12px;
    background: #1c1c1c;
    border: 1px solid #262626;
    padding: 1px 5px;
    border-radius: 4px;
    color: #ffffff;
  }
  .markdown-content :global(pre) {
    background: #000000;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: 8px 0;
  }
  .markdown-content :global(pre code) {
    background: transparent;
    border: none;
    padding: 0;
    font-size: 12px;
    color: #e5e5e5;
  }
  .markdown-content :global(blockquote) {
    border-left: 2px solid #525252;
    padding-left: 10px;
    margin: 6px 0;
    color: #a8a8a8;
  }

  /* ── Self Message Bubble (Instagram Sent) ── */
  .self-container {
    display: flex;
    justify-content: flex-end;
    margin: 3px 0;
    width: 100%;
    animation: fadeIn 0.15s ease-out;
  }
  .self-bubble {
    background: #262626;
    color: #ffffff;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 14px;
    max-width: 72%;
    word-break: break-word;
  }
  .self-meta {
    display: flex;
    justify-content: flex-end;
    margin-top: 2px;
  }
  .self-meta .meta-time {
    font-size: 9.5px;
    color: #8e8e8e;
  }

  /* ── Other Human Message Bubble (Instagram Received) ── */
  .other-container {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 3px 0;
    max-width: 72%;
    animation: fadeIn 0.15s ease-out;
  }
  .other-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #121212;
    border: 1px solid #262626;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10.5px;
    font-weight: 700;
    color: #ffffff;
    flex-shrink: 0;
    margin-top: 14px;
  }
  .other-bubble-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .other-sender-name {
    font-size: 11px;
    font-weight: 600;
    color: #737373;
    padding-left: 4px;
  }
  .other-bubble {
    background: #121212;
    border: 1px solid #262626;
    color: #ffffff;
    border-radius: 18px 18px 18px 4px;
    padding: 10px 14px;
    word-break: break-word;
  }
  .other-meta {
    display: flex;
    justify-content: flex-end;
    margin-top: 2px;
  }
  .other-meta .meta-time {
    font-size: 9.5px;
    color: #737373;
  }
  .msg-content {
    font-size: 13.5px;
    line-height: 1.45;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(3px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>

