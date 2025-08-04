"""
BAML Request Body Extractor for Prompt Optimization

This module provides utilities to extract request bodies from BAML instrumented calls
for use in prompt optimization efforts.
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from baml_py import Collector


@dataclass
class BAMLRequestData:
    """Data structure for storing BAML request information."""
    function_name: str
    request_body: Dict[str, Any]
    url: str
    method: str
    headers: Dict[str, str]
    timestamp: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None


class BAMLRequestExtractor:
    """
    Extracts request body data from BAML instrumented calls for optimization analysis.
    """
    
    def __init__(self):
        """Initialize the BAML request extractor."""
        pass
    
    def extract_request_from_collector(self, collector: Collector, function_name: str = None) -> Optional[BAMLRequestData]:
        """
        Extract request data from a BAML collector.
        
        Args:
            collector: The BAML collector instance
            function_name: Optional function name filter
            
        Returns:
            BAMLRequestData if found, None otherwise
        """
        if not collector or not collector.last:
            return None
        
        log = collector.last
        
        # Filter by function name if specified
        if function_name and log.function_name != function_name:
            return None
        
        # Get the first call (or selected call if available)
        call = log.selected_call if log.selected_call else (log.calls[0] if log.calls else None)
        
        if not call or not call.http_request:
            return None
        
        try:
            # Extract request body
            request_body = self._parse_request_body(call.http_request.body)
            
            return BAMLRequestData(
                function_name=log.function_name,
                request_body=request_body,
                url=call.http_request.url,
                method=call.http_request.method,
                headers=dict(call.http_request.headers),
                timestamp=log.timing.start_time_utc_ms if log.timing else None,
                additional_metadata={
                    "client_name": call.client_name,
                    "provider": call.provider,
                    "duration_ms": call.timing.duration_ms if call.timing else None,
                    "usage": {
                        "input_tokens": call.usage.input_tokens if call.usage else None,
                        "output_tokens": call.usage.output_tokens if call.usage else None,
                    } if call.usage else None
                }
            )
            
        except Exception as e:
            print(f"[WARNING] Failed to extract request data: {e}")
            return None
    
    def extract_requests_from_collector(self, collector: Collector, function_name: str = None) -> List[BAMLRequestData]:
        """
        Extract all request data from a BAML collector.
        
        Args:
            collector: The BAML collector instance
            function_name: Optional function name filter
            
        Returns:
            List of BAMLRequestData objects
        """
        if not collector or not collector.logs:
            return []
        
        requests = []
        
        for log in collector.logs:
            # Filter by function name if specified
            if function_name and log.function_name != function_name:
                continue
            
            # Process each call in the log
            for call in log.calls:
                if not call.http_request:
                    continue
                
                try:
                    request_body = self._parse_request_body(call.http_request.body)
                    
                    request_data = BAMLRequestData(
                        function_name=log.function_name,
                        request_body=request_body,
                        url=call.http_request.url,
                        method=call.http_request.method,
                        headers=dict(call.http_request.headers),
                        timestamp=log.timing.start_time_utc_ms if log.timing else None,
                        additional_metadata={
                            "client_name": call.client_name,
                            "provider": call.provider,
                            "duration_ms": call.timing.duration_ms if call.timing else None,
                            "selected": call.selected,
                            "usage": {
                                "input_tokens": call.usage.input_tokens if call.usage else None,
                                "output_tokens": call.usage.output_tokens if call.usage else None,
                            } if call.usage else None
                        }
                    )
                    
                    requests.append(request_data)
                    
                except Exception as e:
                    print(f"[WARNING] Failed to extract request data from call: {e}")
                    continue
        
        return requests
    
    def _parse_request_body(self, http_body) -> Dict[str, Any]:
        """
        Parse the HTTP body from a BAML HttpRequest.
        
        Args:
            http_body: The HTTPBody object from BAML
            
        Returns:
            Parsed request body as a dictionary
        """
        if not http_body:
            return {}
        
        try:
            # Try to get JSON first
            body_json = http_body.json()
            if body_json:
                return body_json
            
            # Fall back to text
            body_text = http_body.text()
            if body_text:
                # Try to parse as JSON
                try:
                    return json.loads(body_text)
                except json.JSONDecodeError:
                    # Return as text if not JSON
                    return {"text": body_text}
            
            return {}
            
        except Exception as e:
            print(f"[WARNING] Failed to parse request body: {e}")
            return {}
    
    def get_prompt_from_request(self, request_data: BAMLRequestData) -> Optional[str]:
        """
        Extract the prompt from a BAML request for optimization analysis.
        
        Args:
            request_data: The BAML request data
            
        Returns:
            The prompt string if found, None otherwise
        """
        if not request_data or not request_data.request_body:
            return None
        
        # Common patterns for extracting prompts from different LLM providers
        body = request_data.request_body
        
        # OpenAI/OpenRouter pattern
        if "messages" in body:
            messages = body["messages"]
            if messages and isinstance(messages, list):
                # Get the last user message (most recent prompt)
                for message in reversed(messages):
                    if message.get("role") == "user":
                        return message.get("content", "")
        
        # Anthropic pattern
        if "prompt" in body:
            return body["prompt"]
        
        # Google pattern
        if "contents" in body:
            contents = body["contents"]
            if contents and isinstance(contents, list):
                for content in reversed(contents):
                    if content.get("role") == "user":
                        parts = content.get("parts", [])
                        if parts and isinstance(parts, list):
                            for part in parts:
                                if part.get("text"):
                                    return part["text"]
        
        # Fallback: look for any text content
        if "text" in body:
            return body["text"]
        
        return None
    
    def get_model_from_request(self, request_data: BAMLRequestData) -> Optional[str]:
        """
        Extract the model name from a BAML request.
        
        Args:
            request_data: The BAML request data
            
        Returns:
            The model name if found, None otherwise
        """
        if not request_data:
            return None
        
        # Try to get from headers first
        headers = request_data.headers
        if headers:
            # Common header patterns
            for header_name in ["x-model", "anthropic-version", "model"]:
                if header_name in headers:
                    return headers[header_name]
        
        # Try to get from request body
        body = request_data.request_body
        if body:
            # OpenAI/OpenRouter pattern
            if "model" in body:
                return body["model"]
            
            # Anthropic pattern
            if "model" in body:
                return body["model"]
        
        # Fallback to client name from metadata
        if request_data.additional_metadata and "client_name" in request_data.additional_metadata:
            return request_data.additional_metadata["client_name"]
        
        return None


# Global instance for easy access
baml_request_extractor = BAMLRequestExtractor()


def extract_request_from_collector(collector: Collector, function_name: str = None) -> Optional[BAMLRequestData]:
    """
    Convenience function to extract request data from a BAML collector.
    
    Args:
        collector: The BAML collector instance
        function_name: Optional function name filter
        
    Returns:
        BAMLRequestData if found, None otherwise
    """
    return baml_request_extractor.extract_request_from_collector(collector, function_name)


def extract_requests_from_collector(collector: Collector, function_name: str = None) -> List[BAMLRequestData]:
    """
    Convenience function to extract all request data from a BAML collector.
    
    Args:
        collector: The BAML collector instance
        function_name: Optional function name filter
        
    Returns:
        List of BAMLRequestData objects
    """
    return baml_request_extractor.extract_requests_from_collector(collector, function_name)


def get_prompt_from_request(request_data: BAMLRequestData) -> Optional[str]:
    """
    Convenience function to extract the prompt from a BAML request.
    
    Args:
        request_data: The BAML request data
        
    Returns:
        The prompt string if found, None otherwise
    """
    return baml_request_extractor.get_prompt_from_request(request_data)


def get_model_from_request(request_data: BAMLRequestData) -> Optional[str]:
    """
    Convenience function to extract the model name from a BAML request.
    
    Args:
        request_data: The BAML request data
        
    Returns:
        The model name if found, None otherwise
    """
    return baml_request_extractor.get_model_from_request(request_data) 