from typing import Optional, Dict, Any
import requests
import json
import logging
from abc import ABC, abstractmethod
from config.settings import Settings

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self):
        settings = Settings()
        llm_config = settings.get_all()["llm"]
        self.model_name = llm_config["model_name"]
        self.api_url = llm_config["api_url"]
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
    def __init__(self):
        settings = Settings()
        llm_config = settings.get_all()["llm"]
        self.api_url = llm_config["api_url"]
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
        settings = Settings()
        llm_config = settings.get_all()["llm"]
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model_name = llm_config.get("deepseek_model", "deepseek-chat")
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": kwargs.get("model", self.model_name),
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
        settings = Settings()
        llm_config = settings.get_all()["llm"]
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model_name = llm_config.get("openai_model", "gpt-3.5-turbo")
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": kwargs.get("model", self.model_name),
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

    @staticmethod
    def get_default_provider() -> LLMProvider:
        """获取默认的LLM提供者实例"""
        try:
            settings = Settings()
            llm_config = settings.get_all()["llm"]
            provider_type = llm_config.get("provider", "ollama")  # 从配置获取提供者类型，默认为ollama
            
            # 根据提供者类型创建实例
            if provider_type in ["deepseek", "openai"]:
                api_key = llm_config.get(f"{provider_type}_api_key")
                if not api_key:
                    raise ValueError(f"Missing API key for {provider_type}")
                return LLMFactory.create_provider(provider_type, api_key=api_key)
            else:
                return LLMFactory.create_provider(provider_type)
                
        except Exception as e:
            logging.error(f"Failed to create LLM provider: {str(e)}")
            # 如果出错，返回默认的Ollama提供者
            return OllamaProvider() 