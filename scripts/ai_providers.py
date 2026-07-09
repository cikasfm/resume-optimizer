#!/usr/bin/env python3
"""
AI Provider abstraction layer for resume optimization.
Supports multiple AI providers including free options.
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response from the AI provider.
        
        Args:
            system_prompt: System/instruction prompt
            user_prompt: User input prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider (paid, but high quality)."""
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
    
    def generate(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o", 
                 temperature: float = 0.7, max_tokens: int = 8000, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content


class OllamaProvider(AIProvider):
    """Ollama provider (FREE, local LLM - requires Ollama installed locally)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        import requests
        self.requests = requests
    
    def generate(self, system_prompt: str, user_prompt: str, model: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 8000, **kwargs) -> str:
        model = model or self.model
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = self.requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=300  # Ollama can be slow
        )
        response.raise_for_status()
        return response.json()["response"]


class GoogleGeminiProvider(AIProvider):
    """Google Gemini API provider (FREE tier available)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        import requests
        self.requests = requests
    
    def generate(self, system_prompt: str, user_prompt: str, model: str = "gemini-2.5-pro",
                 temperature: float = 0.7, max_tokens: int = 8000, **kwargs) -> str:
        import time
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Use v1 endpoint which supports newer Gemini models (e.g., gemini-2.5-pro)
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        # Retry on rate limit (429) with exponential backoff
        max_retries = 3
        base_delay = 30  # seconds
        
        for attempt in range(max_retries + 1):
            # Verbose progress logs
            if kwargs.get('verbose'):
                print(f"[gemini] attempt {attempt+1}/{max_retries+1} -> POST {url}")
            try:
                response = self.requests.post(url, json=payload, timeout=120)
            except Exception as e:
                # Network/connection level error
                if kwargs.get('verbose'):
                    print(f"[gemini] request exception: {e}")
                raise RuntimeError(f"Gemini request failed: {e}") from e

            if response.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    if kwargs.get('verbose'):
                        print(f"[gemini] rate limited (429). Sleeping {delay}s before retry")
                    time.sleep(delay)
                    continue
                # Exhausted retries - include body for debugging
                body = None
                try:
                    body = response.text
                except Exception:
                    body = '<unreadable response body>'
                raise RuntimeError(f"Gemini rate-limited after retries. Status=429. Body={body}")

            # Raise for other non-2xx and include response body when possible
            try:
                response.raise_for_status()
            except Exception as e:
                body = None
                try:
                    body = response.text
                except Exception:
                    body = '<unreadable response body>'
                if kwargs.get('verbose'):
                    print(f"[gemini] non-2xx response: {getattr(response, 'status_code', None)}")
                    print(f"[gemini] response body (truncated): {body[:1000]}")
                raise RuntimeError(f"Gemini API returned status {getattr(response, 'status_code', None)}: {body}") from e

            # Try to parse JSON and return text content, with helpful errors
            try:
                data = response.json()
                if kwargs.get('verbose'):
                    print(f"[gemini] received response JSON keys: {list(data.keys())}")
            except Exception as e:
                if kwargs.get('verbose'):
                    print(f"[gemini] non-JSON response: {response.text[:1000]}")
                raise RuntimeError(f"Gemini API returned non-JSON response: {response.text}") from e

            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # If caller requested verbose/debug info, return both text and raw JSON
                if kwargs.get('verbose'):
                    return {"text": text, "raw": data}
                return text
            except Exception as e:
                # Include the full JSON for debugging
                raise RuntimeError(f"Gemini API response missing expected fields. Full response: {json.dumps(data)}") from e


class GroqProvider(AIProvider):
    """Groq API provider (FREE tier available, very fast)."""
    
    def __init__(self, api_key: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)
    
    def generate(self, system_prompt: str, user_prompt: str, model: str = "llama-3.1-70b-versatile",
                 temperature: float = 0.7, max_tokens: int = 8000, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content


class HuggingFaceProvider(AIProvider):
    """Hugging Face Inference API provider (FREE tier available)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        import requests
        self.requests = requests
    
    def generate(self, system_prompt: str, user_prompt: str, model: str = "mistralai/Mistral-7B-Instruct-v0.2",
                 temperature: float = 0.7, max_tokens: int = 8000, **kwargs) -> str:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = self.requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "inputs": full_prompt,
                "parameters": {
                    "temperature": temperature,
                    "max_new_tokens": min(max_tokens, 512)  # HF free tier limit
                }
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").replace(full_prompt, "").strip()
        return str(result)


def get_provider(provider_name: str, config: Dict[str, Any]) -> AIProvider:
    """Factory function to get the appropriate AI provider.
    
    Args:
        provider_name: Name of the provider ('openai', 'ollama', 'gemini', 'groq', 'huggingface')
        config: Configuration dictionary with API keys and settings
        
    Returns:
        AIProvider instance
    """
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        api_key = config.get('openai_api_key')
        if not api_key:
            raise ValueError("openai_api_key not found in config")
        return OpenAIProvider(api_key)
    
    elif provider_name == "ollama":
        base_url = config.get('ollama_base_url', 'http://localhost:11434')
        model = config.get('ollama_model', 'llama3.2')
        return OllamaProvider(base_url=base_url, model=model)
    
    elif provider_name == "gemini":
        api_key = config.get('gemini_api_key')
        if not api_key:
            raise ValueError("gemini_api_key not found in config")
        return GoogleGeminiProvider(api_key)
    
    elif provider_name == "groq":
        api_key = config.get('groq_api_key')
        if not api_key:
            raise ValueError("groq_api_key not found in config")
        return GroqProvider(api_key)
    
    elif provider_name == "huggingface":
        api_key = config.get('huggingface_api_key')
        if not api_key:
            raise ValueError("huggingface_api_key not found in config")
        return HuggingFaceProvider(api_key)
    
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: openai, ollama, gemini, groq, huggingface")
