"""
LLM Adapters - Concrete implementations of LLMPort

Supports multiple LLM backends:
1. Ollama (local)
2. AWS Endpoint (SageMaker/custom)
3. HuggingFace Inference Endpoint
4. OpenAI API
"""

import logging
import requests
from typing import Optional
from langchain_ollama import ChatOllama

from .llm_port import LLMPort

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(LLMPort):
    """
    Ollama LLM Adapter - Local LLM via Ollama
    
    Usage:
        llm = OllamaLLMAdapter(
            base_url="http://localhost:11434",
            model="llama3.2:3b"
        )
        response = llm.invoke("What is AWS Support?")
    """
    
    def __init__(self, base_url: str, model: str, temperature: float = 0.7):
        """
        Initialize Ollama adapter.
        
        Args:
            base_url: Ollama server URL
            model: Model name (e.g., "llama3.2:3b")
            temperature: Sampling temperature
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        
        # Initialize LangChain Ollama client
        self.client = ChatOllama(
            base_url=base_url,
            model=model,
            temperature=temperature
        )
        
        logger.info(f"Initialized Ollama LLM: {model} at {base_url}")
    
    def invoke(self, prompt: str, temperature: float | None = None) -> str:
        """
        Invoke Ollama model with prompt.

        Args:
            prompt: Input prompt text
            temperature: Optional temperature override for this invocation
        """
        # Use temperature override if provided, otherwise use default
        if temperature is not None:
            # Create temporary client with different temperature
            temp_client = ChatOllama(
                base_url=self.base_url,
                model=self.model,
                temperature=temperature
            )
            response = temp_client.invoke(prompt)
        else:
            response = self.client.invoke(prompt)

        answer = response.content if hasattr(response, 'content') else str(response)
        return answer
    
    def get_model_name(self) -> str:
        """Get model name."""
        return f"ollama/{self.model}"


class AWSEndpointLLMAdapter(LLMPort):
    """
    AWS Endpoint LLM Adapter - Custom model on AWS SageMaker/Inference Endpoint
    
    This adapter is for your custom DPO-trained model hosted on AWS.
    
    Usage:
        llm = AWSEndpointLLMAdapter(
            endpoint_url="https://your-model.sagemaker.us-east-1.amazonaws.com/invocations",
            api_key="your-api-key",
            model_name="custom-support-model-dpo-v1"
        )
        response = llm.invoke("What is AWS Support?")
    """
    
    def __init__(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        model_name: str = "custom-model",
        timeout: int = 60
    ):
        """
        Initialize AWS Endpoint adapter.
        
        Args:
            endpoint_url: AWS endpoint URL
            api_key: API key for authentication (if required)
            model_name: Model identifier
            timeout: Request timeout in seconds
        """
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        
        logger.info(f"Initialized AWS Endpoint LLM: {model_name} at {endpoint_url}")
    
    def invoke(self, prompt: str, temperature: float | None = None) -> str:
        """
        Invoke AWS endpoint with prompt.

        Args:
            prompt: Input prompt text
            temperature: Optional temperature override for this invocation

        Assumes endpoint accepts JSON with format:
        {
            "inputs": "prompt text",
            "parameters": {"max_new_tokens": 512, "temperature": 0.7}
        }

        And returns:
        {
            "generated_text": "response text"
        }

        Adjust this based on your actual endpoint format.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Use temperature override if provided, otherwise use default 0.7
        temp_value = temperature if temperature is not None else 0.7

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": temp_value,
                "do_sample": True
            }
        }
        
        try:
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract generated text (adjust based on your endpoint format)
            if isinstance(result, list) and len(result) > 0:
                answer = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                answer = result.get("generated_text", result.get("text", ""))
            else:
                answer = str(result)
            
            return answer
            
        except Exception as e:
            logger.error(f"AWS Endpoint error: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Get model name."""
        return f"aws/{self.model_name}"


class HuggingFaceEndpointLLMAdapter(LLMPort):
    """
    HuggingFace Inference Endpoint LLM Adapter

    For models deployed on HuggingFace Inference Endpoints.

    Usage:
        llm = HuggingFaceEndpointLLMAdapter(
            endpoint_url="https://your-endpoint.aws.endpoints.huggingface.cloud",
            api_token="hf_xxxxxxxxxxxxx",
            model_name="custom-support-model"
        )
        response = llm.invoke("What is AWS Support?")
    """

    def __init__(
        self,
        endpoint_url: str,
        api_token: str,
        model_name: str = "custom-model",
        timeout: int = 60
    ):
        """
        Initialize HuggingFace Endpoint adapter.

        Args:
            endpoint_url: HuggingFace endpoint URL
            api_token: HuggingFace API token
            model_name: Model identifier
            timeout: Request timeout in seconds
        """
        self.endpoint_url = endpoint_url
        self.api_token = api_token
        self.model_name = model_name
        self.timeout = timeout

        logger.info(f"Initialized HuggingFace Endpoint LLM: {model_name}")

    def invoke(self, prompt: str, temperature: float | None = None) -> str:
        """
        Invoke HuggingFace endpoint with prompt.

        Args:
            prompt: Input prompt text
            temperature: Optional temperature override for this invocation
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        # Use temperature override if provided, otherwise use default 0.7
        temp_value = temperature if temperature is not None else 0.7

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": temp_value,
                "return_full_text": False
            }
        }

        try:
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            # Extract generated text
            if isinstance(result, list) and len(result) > 0:
                answer = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                answer = result.get("generated_text", result.get("text", ""))
            else:
                answer = str(result)

            return answer

        except Exception as e:
            logger.error(f"HuggingFace Endpoint error: {e}")
            raise

    def get_model_name(self) -> str:
        """Get model name."""
        return f"huggingface/{self.model_name}"


def create_llm_adapter(
    backend: str,
    **kwargs
) -> LLMPort:
    """
    Factory function to create LLM adapter based on backend type.

    Args:
        backend: LLM backend type ("ollama", "aws_endpoint", "huggingface_endpoint")
        **kwargs: Backend-specific configuration

    Returns:
        LLM adapter instance

    Examples:
        # Ollama
        llm = create_llm_adapter(
            backend="ollama",
            base_url="http://localhost:11434",
            model="llama3.2:3b"
        )

        # AWS Endpoint
        llm = create_llm_adapter(
            backend="aws_endpoint",
            endpoint_url="https://your-model.sagemaker.us-east-1.amazonaws.com/invocations",
            api_key="your-api-key",
            model_name="custom-support-model-dpo-v1"
        )

        # HuggingFace Endpoint
        llm = create_llm_adapter(
            backend="huggingface_endpoint",
            endpoint_url="https://your-endpoint.aws.endpoints.huggingface.cloud",
            api_token="hf_xxxxxxxxxxxxx",
            model_name="custom-support-model"
        )
    """
    if backend == "ollama":
        return OllamaLLMAdapter(**kwargs)
    elif backend == "aws_endpoint":
        return AWSEndpointLLMAdapter(**kwargs)
    elif backend == "huggingface_endpoint":
        return HuggingFaceEndpointLLMAdapter(**kwargs)
    else:
        raise ValueError(
            f"Unknown LLM backend: {backend}. "
            f"Supported: ollama, aws_endpoint, huggingface_endpoint"
        )


