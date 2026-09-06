<script>
  import { isJoined } from './lib/stores/room.js';
  import JoinScreen from './lib/components/JoinScreen.svelte';
  import ChatRoom from './lib/components/ChatRoom.svelte';
</script>

<main class="app-root">
  {#if $isJoined}
    <ChatRoom />
  {:else}
    <JoinScreen />
  {/if}
</main>

<style>
  .app-root {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    background-color: #000000;
  }
</style>

