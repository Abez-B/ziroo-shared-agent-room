import os
import sys
import re
import json
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
import httpx
from dotenv import load_dotenv, find_dotenv

# Search and load .env from current directory, parent directory, or backend directory
load_dotenv(find_dotenv(usecwd=True))
for env_path in [".env", "backend/.env", "../.env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT_SECONDS", "15.0"))

def is_agent_addressed(content: str) -> bool:
    """Checks if the message explicitly addresses @agent."""
    return bool(re.search(r"@agent\b", content, re.IGNORECASE))

def clean_agent_prompt(content: str) -> str:
    """Strips the @agent mention to extract the actual user prompt."""
    cleaned = re.sub(r"@agent\b", "", content, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else content

class AgentService:
    def __init__(self):
        pass

    def _get_config(self):
        # Refresh from env dynamically
        load_dotenv(find_dotenv(usecwd=True))
        timeout = float(os.getenv("AGENT_TIMEOUT_SECONDS", "15.0"))
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        model = os.getenv("AGENT_MODEL", "").strip()
        mock_mode = os.getenv("MOCK_LLM", "false").lower() in ("true", "1", "yes")
        return timeout, anthropic_key, openai_key, gemini_key, model, mock_mode

    async def generate_response(
        self,
        user_name: str,
        room_code: str,
        prompt: str,
        user_history: List[Dict[str, str]]
    ) -> str:
        """
        Generates an LLM response using strictly the isolated per-user history.
        user_history must contain only messages exchanged between user_name and the Agent.
        """
        timeout, anthropic_key, openai_key, gemini_key, model, mock_mode = self._get_config()
        cleaned_prompt = clean_agent_prompt(prompt)
        system_instruction = (
            f"You are an AI participant in a shared room '{room_code}'. "
            f"You are conversing specifically with user '{user_name}'. "
            f"Always keep your answers helpful, concise, and direct. "
            f"You only have memory of your direct conversation with {user_name}."
        )

        # Dynamic failure testing simulation (for testing failure handling)
        force_fail = os.getenv("AGENT_FORCE_FAILURE", "").lower()
        if force_fail == "timeout":
            await asyncio.sleep(0.05)
            raise TimeoutError(f"Request timed out after {timeout}s")
        elif force_fail == "error":
            await asyncio.sleep(0.05)
            raise RuntimeError("Upstream AI provider is temporarily unavailable (HTTP 503)")
        elif force_fail == "malformed":
            await asyncio.sleep(0.05)
            raise ValueError("Malformed response from AI provider: empty candidate list")

        try:
            async with asyncio.timeout(timeout):
                # 1. Gemini API
                if gemini_key and not mock_mode:
                    logger.info(f"Calling Gemini API for user '{user_name}'...")
                    return await self._call_gemini(gemini_key, model, timeout, system_instruction, cleaned_prompt, user_history)

                # 2. Anthropic Claude API
                if anthropic_key and not mock_mode:
                    logger.info(f"Calling Anthropic API for user '{user_name}'...")
                    return await self._call_anthropic(anthropic_key, model, timeout, system_instruction, cleaned_prompt, user_history)

                # 3. OpenAI API
                if openai_key and not mock_mode:
                    logger.info(f"Calling OpenAI API for user '{user_name}'...")
                    return await self._call_openai(openai_key, model, timeout, system_instruction, cleaned_prompt, user_history)

                # 4. Mock mode (fallback when no API key configured or mock explicitly enabled)
                logger.info(f"No API key detected in .env; using offline mock responder for user '{user_name}'.")
                return await self._mock_llm_response(user_name, cleaned_prompt, user_history)
        except TimeoutError:
            raise TimeoutError(f"Agent timed out after {timeout} seconds")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError("Invalid or unauthorized API key (HTTP 401)")
            elif e.response.status_code == 429:
                raise RuntimeError("Rate limit exceeded on AI provider (HTTP 429)")
            raise RuntimeError(f"AI provider returned HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise RuntimeError(f"Network error connecting to AI provider: {type(e).__name__}")

    async def _mock_llm_response(
        self,
        user_name: str,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        """
        Deterministic mock responder that verifies context isolation.
        Inspects strictly the given user's history.
        """
        await asyncio.sleep(0.05) # simulate slight async network latency
        lower_prompt = prompt.lower()

        # Check for context memory queries
        memory_triggers = ["what is my", "what was my", "what's my", "tell me my", "do you remember my"]
        if any(trig in lower_prompt for trig in memory_triggers):
            # Extract key concept asked (e.g. "favorite color", "secret key", "token", etc.)
            for item in reversed(history):
                if item["role"] == "user":
                    content = item["content"].strip()
                    # Skip if the historical item was itself a question
                    if any(q in content.lower() for q in ["what is", "what was", "what's", "who is", "?"]):
                        continue
                    match = re.search(r"(favorite\s+[a-zA-Z]+|secret\s+[a-zA-Z]+|token|key|project\s+name|project|food|color|code|password)\s+(?:is|=|:)\s+([a-zA-Z0-9_\-\s]+)", content, re.IGNORECASE)
                    if match:
                        concept = match.group(1).strip()
                        val = match.group(2).strip().rstrip('.')
                        return f"Your {concept} is {val}."
            return f"I don't recall you mentioning that, {user_name}."

        # Check if user is asking about other users or general info
        if "who am i" in lower_prompt or "my name" in lower_prompt:
            return f"You are {user_name}."

        return f"Hello {user_name}, I received your message: '{prompt}'."

    async def _call_gemini(
        self,
        key: str,
        model_name: str,
        timeout: float,
        system_instruction: str,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        model = model_name or "gemini-3.6-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500}
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()
            raise ValueError(f"Malformed response from Gemini API: {data}")

    async def _call_anthropic(
        self,
        key: str,
        model_name: str,
        timeout: float,
        system_instruction: str,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        model = model_name or "claude-3-haiku-20240307"
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        messages = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "system": system_instruction,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            if content_blocks and "text" in content_blocks[0]:
                return content_blocks[0]["text"].strip()
            raise ValueError(f"Malformed response from Anthropic API: {data}")

    async def _call_openai(
        self,
        key: str,
        model_name: str,
        timeout: float,
        system_instruction: str,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        model = model_name or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": system_instruction}]
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"]["content"].strip()
            raise ValueError(f"Malformed response from OpenAI API: {data}")

agent_service = AgentService()
