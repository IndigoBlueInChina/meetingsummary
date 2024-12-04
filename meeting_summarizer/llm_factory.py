from typing import Optional, Dict, Any
import requests
import json
import logging
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str = "qwen2.5", api_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            self.logger.error(f"Ollama generation error: {str(e)}")
            return None

class VLLMProvider(LLMProvider):
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": kwargs.get("temperature", 0.7),
                    **kwargs
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["text"]
        except Exception as e:
            self.logger.error(f"VLLM generation error: {str(e)}")
            return None

class DeepseekProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": kwargs.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Deepseek generation error: {str(e)}")
            return None

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": kwargs.get("model", "gpt-3.5-turbo"),
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"OpenAI generation error: {str(e)}")
            return None

class LLMFactory:
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> LLMProvider:
        providers = {
            "ollama": OllamaProvider,
            "vllm": VLLMProvider,
            "deepseek": DeepseekProvider,
            "openai": OpenAIProvider
        }
        
        if provider_type not in providers:
            raise ValueError(f"Unsupported provider type: {provider_type}")
            
        return providers[provider_type](**kwargs) 