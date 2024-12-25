from typing import Optional, Dict, Any
from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.llms.openllm import OpenLLM
from config.settings import Settings
from utils.flexible_logger import Logger

class LLMFactory:
    """LLM Factory using LlamaIndex"""
    
    def __init__(self):
        self._providers: Dict[str, LLM] = {}
        self.settings = Settings()
        self.llm_config = self.settings.get_all()["llm"]
        self.logger = Logger(
            name="llm_factory",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.logger.info("Initializing LLM Factory")
        
    def register_openai(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> None:
        """Register OpenAI provider"""
        self.logger.info("Registering OpenAI provider")
        api_key = api_key or self.llm_config.get("api_key")
        model = model or self.llm_config.get("model_name", "gpt-3.5-turbo")
        api_base = api_base or self.llm_config.get("api_url")
        
        if not api_key:
            self.logger.error("OpenAI API key is required")
            raise ValueError("OpenAI API key is required")
            
        llm = OpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            api_base=api_base,
            **kwargs
        )
        self._providers['openai'] = llm
        self.logger.info(f"OpenAI provider registered with model: {model}")
        
    def register_deepseek(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> None:
        """Register DeepSeek provider using OpenLLM"""
        self.logger.info("Registering DeepSeek provider")
        api_key = api_key or self.llm_config.get("api_key")
        model = model or self.llm_config.get("model_name", "deepseek-chat")
        api_base = api_base or self.llm_config.get("api_url", "https://api.deepseek.com/v1")
        
        if not api_key:
            self.logger.error("DeepSeek API key is required")
            raise ValueError("DeepSeek API key is required")
            
        llm = OpenLLM(
            model=model,
            api_base=api_base,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )
        self._providers['deepseek'] = llm
        self.logger.info(f"DeepSeek provider registered with model: {model}")
        
    def register_ollama(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> None:
        """Register Ollama provider"""
        self.logger.info("Registering Ollama provider")
        model = model or self.llm_config.get("model_name", "qwen2.5")
        base_url = base_url or self.llm_config.get("api_url", "http://localhost:11434")
        
        llm = Ollama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            **kwargs
        )
        self._providers['ollama'] = llm
        self.logger.info(f"Ollama provider registered with model: {model}")
        
    def register_custom_provider(
        self,
        name: str,
        provider: LLM
    ) -> None:
        """Register a custom LLM provider"""
        self._providers[name] = provider
        
    def get_llm(self, provider_name: str) -> LLM:
        """Get LLM instance by provider name"""
        if provider_name not in self._providers:
            self.logger.error(f"Provider {provider_name} not found")
            raise KeyError(f"Provider {provider_name} not found")
        return self._providers[provider_name]

    @staticmethod
    def create_default() -> 'LLMFactory':
        """创建默认的LLM工厂实例"""
        logger = Logger(name="llm_factory", console_output=True, file_output=True)
        try:
            factory = LLMFactory()
            settings = Settings()
            llm_config = settings.get_all()["llm"]
            
            # 从配置中获取 provider 类型
            provider_type = llm_config.get("provider", "ollama")
            logger.info(f"Creating default LLM factory with provider: {provider_type}")
            
            # 从配置中获取对应的 API key 和其他设置
            api_key = llm_config.get("api_key")
            model_name = llm_config.get("model_name")
            api_url = llm_config.get("api_url")
            
            # 根据 provider 类型注册对应的 LLM
            if provider_type == "openai":
                factory.register_openai(
                    api_key=api_key,
                    model=model_name,
                    api_base=api_url
                )
            elif provider_type == "ollama":
                factory.register_ollama(
                    model=model_name,
                    base_url=api_url
                )
            elif provider_type == "deepseek":
                factory.register_deepseek(
                    api_key=api_key,
                    model=model_name,
                    api_base=api_url
                )
            else:
                logger.error(f"Unsupported provider type: {provider_type}")
                raise ValueError(f"Unsupported provider type: {provider_type}")
                
            return factory
            
        except Exception as e:
            logger.error(f"Failed to create default LLM factory: {str(e)}")
            raise

    @staticmethod
    def get_llm_instance() -> LLM:
        """
        直接获取一个 LLM 实例，基于配置文件中的设置
        
        Returns:
            LLM: LlamaIndex LLM 实例
        """
        logger = Logger(name="llm_factory", console_output=True, file_output=True)
        try:
            settings = Settings()
            llm_config = settings.get_all()["llm"]
            provider_type = llm_config.get("provider", "ollama")
            
            logger.info(f"Creating LLM instance for provider: {provider_type}")
            
            if provider_type == "openai":
                api_key = llm_config.get("api_key")
                if not api_key:
                    raise ValueError("OpenAI API key is required")
                return OpenAI(
                    api_key=api_key,
                    model=llm_config.get("model_name", "gpt-3.5-turbo"),
                    temperature=llm_config.get("temperature", 0.7),
                    api_base=llm_config.get("api_url")
                )
                
            elif provider_type == "ollama":
                return Ollama(
                    model=llm_config.get("model_name", "qwen2.5"),
                    base_url=llm_config.get("api_url", "http://localhost:11434"),
                    temperature=llm_config.get("temperature", 0),
                    request_timeout=300  # 设置超时时间为 300 秒（5分钟）
                )
                
            elif provider_type == "deepseek":
                api_key = llm_config.get("api_key")
                if not api_key:
                    raise ValueError("DeepSeek API key is required")
                return OpenLLM(
                    model=llm_config.get("model_name", "deepseek-chat"),
                    api_base=llm_config.get("api_url", "https://api.deepseek.com/v1"),
                    api_key=api_key,
                    temperature=llm_config.get("temperature", 0.7)
                )
                
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")
                
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {str(e)}")
            raise

# 使用示例
def simple_example():
    # 创建工厂实例
    factory = LLMFactory()
    
    # 注册 providers
    factory.register_openai(
        api_key="your-openai-key",
        model="gpt-4"
    )
    
    factory.register_ollama(model="llama2")
    
    # 使用 OpenAI
    openai_llm = factory.get_llm("openai")
    response = openai_llm.complete("Hello!")
    print("OpenAI response:", response)
    
    # 使用 Ollama
    ollama_llm = factory.get_llm("ollama")
    response = ollama_llm.complete("Hello!")
    print("Ollama response:", response)

# 使用高级特性的示例
def advanced_example():
    factory = LLMFactory()
    
    # 添加回调管理器用于监控
    callback_manager = CallbackManager([])
    
    # 注册带有回调的 OpenAI provider
    factory.register_openai(
        api_key="your-openai-key",
        model="gpt-4",
        callback_manager=callback_manager
    )
    
    llm = factory.get_llm("openai")
    
    # 使用聊天消息格式
    messages = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content="You are a helpful assistant."
        ),
        ChatMessage(
            role=MessageRole.USER,
            content="What is artificial intelligence?"
        )
    ]
    
    # 使用流式输出
    response_iter = llm.stream_chat(messages)
    for response in response_iter:
        print(response.delta, end="", flush=True)
    print()

# 结构化输出示例
def structured_output_example():
    from llama_index.core.output_parsers import PydanticOutputParser
    from pydantic import BaseModel
    
    class AIDefinition(BaseModel):
        short_definition: str
        key_concepts: list[str]
        applications: list[str]
    
    factory = LLMFactory()
    factory.register_openai(api_key="your-openai-key")
    llm = factory.get_llm("openai")
    
    # 创建输出解析器
    parser = PydanticOutputParser(AIDefinition)
    
    # 构建提示
    prompt = f"""
    Define artificial intelligence and provide key information.
    {parser.get_format_instructions()}
    """
    
    # 获取结构化响应
    response = llm.complete(prompt)
    parsed_response = parser.parse(response)
    print("Structured Response:", parsed_response)
