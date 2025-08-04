"""
Utility module to extract BAML type field descriptions and types for span metadata.
Enhanced to handle composite types and group fields by their containing classes.
"""

import inspect
import re
from typing import Dict, Any, Type, List, Union
from pydantic import BaseModel


def get_baml_field_descriptions(baml_type_name: str) -> Dict[str, str]:
    """
    Extract field descriptions from the inlined BAML file.
    
    Args:
        baml_type_name: The name of the BAML type (e.g., "PromptOptimizationData")
        
    Returns:
        Dictionary mapping field names to their descriptions
    """
    try:
        from baml_client.inlinedbaml import _file_map
        
        # Get the rag.baml content
        rag_baml_content = _file_map.get("rag.baml", "")
        
        # Find the class definition
        class_pattern = rf"class {baml_type_name} \{{\s*([^}}]+)\s*\}}"
        class_match = re.search(class_pattern, rag_baml_content, re.DOTALL)
        
        if not class_match:
            return {}
        
        class_body = class_match.group(1)
        
        # Extract field descriptions - enhanced to handle different field types
        field_descriptions = {}
        
        # Pattern for string fields with descriptions
        string_field_pattern = r'(\w+)\s+string\s+@description\("([^"]+)"\)'
        for match in re.finditer(string_field_pattern, class_body):
            field_name = match.group(1)
            description = match.group(2)
            field_descriptions[field_name] = description
        
        # Pattern for composite fields with descriptions
        composite_field_pattern = r'(\w+)\s+(\w+)\s+@description\("([^"]+)"\)'
        for match in re.finditer(composite_field_pattern, class_body):
            field_name = match.group(1)
            field_type = match.group(2)
            description = match.group(3)
            field_descriptions[field_name] = description
        
        return field_descriptions
        
    except Exception as e:
        print(f"Warning: Could not extract BAML field descriptions: {e}")
        return {}


def _is_composite_type(type_str: str) -> bool:
    """
    Check if a type string represents a composite type (not a primitive).
    
    Args:
        type_str: The type string to check
        
    Returns:
        True if the type is composite, False otherwise
    """
    # Remove common type wrappers
    clean_type = type_str.replace("typing.", "").replace("Optional[", "").replace("Union[", "")
    clean_type = re.sub(r'\[.*?\]', '', clean_type)  # Remove generic parameters
    
    # List of primitive types
    primitive_types = {
        'str', 'string', 'int', 'integer', 'float', 'bool', 'boolean', 
        'None', 'NoneType', 'Any', 'object'
    }
    
    return clean_type not in primitive_types


def _extract_composite_class_name(type_str: str) -> str:
    """
    Extract the composite class name from a type string.
    
    Args:
        type_str: The type string to parse
        
    Returns:
        The composite class name
    """
    # Handle Optional[Type] and Union[None, Type] patterns
    if "Optional[" in type_str:
        match = re.search(r'Optional\[([^\]]+)\]', type_str)
        if match:
            return match.group(1).replace("typing.", "")
    
    if "Union[" in type_str:
        # Extract the first non-None type
        match = re.search(r'Union\[([^\]]+)\]', type_str)
        if match:
            types = [t.strip() for t in match.group(1).split(",")]
            for t in types:
                if t not in ["None", "typing_extensions.Literal['None']"]:
                    return t.replace("typing.", "")
    
    # Handle List[Type] patterns
    if "List[" in type_str:
        match = re.search(r'List\[([^\]]+)\]', type_str)
        if match:
            return match.group(1).replace("typing.", "")
    
    # Handle direct class references
    clean_type = type_str.replace("typing.", "")
    return clean_type


def _get_composite_class_metadata(composite_class: Type[BaseModel]) -> Dict[str, Any]:
    """
    Extract metadata for a composite class.
    
    Args:
        composite_class: The composite class to analyze
        
    Returns:
        Dictionary containing composite class metadata
    """
    metadata = {
        "class_name": composite_class.__name__,
        "fields": {},
        "nested_composites": {}
    }
    
    # Get field information from the Pydantic model
    model_fields = composite_class.model_fields
    
    for field_name, field_info in model_fields.items():
        type_str = str(field_info.annotation)
        
        # Clean up the type display
        if type_str.startswith("<class '") and type_str.endswith("'>"):
            type_str = type_str[8:-2]  # Remove "<class '" and "'>"
        
        field_metadata = {
            "type": type_str,
            "is_composite": _is_composite_type(type_str)
        }
        
        metadata["fields"][field_name] = field_metadata
        
        # Track nested composite types
        if _is_composite_type(type_str):
            composite_name = _extract_composite_class_name(type_str)
            metadata["nested_composites"][field_name] = composite_name
    
    return metadata


def get_baml_type_metadata(baml_type_class: Type[BaseModel]) -> Dict[str, Dict[str, str]]:
    """
    Extract field descriptions and types from a BAML type class.
    
    Args:
        baml_type_class: The BAML type class (e.g., PromptOptimizationData)
        
    Returns:
        Dictionary mapping field names to their metadata (description, type)
    """
    metadata = {}
    
    # Get field information from the Pydantic model
    model_fields = baml_type_class.model_fields
    
    # Get BAML field descriptions
    baml_descriptions = get_baml_field_descriptions(baml_type_class.__name__)
    
    for field_name, field_info in model_fields.items():
        # Get description from BAML or use default
        description = baml_descriptions.get(field_name, "No description available")
        
        # Clean up the type display
        type_str = str(field_info.annotation)
        if type_str.startswith("<class '") and type_str.endswith("'>"):
            type_str = type_str[8:-2]  # Remove "<class '" and "'>"
        
        field_metadata = {
            "type": type_str,
            "description": description,
            "is_composite": _is_composite_type(type_str)
        }
        metadata[field_name] = field_metadata
    
    return metadata


def create_structured_prompt_metadata(
    prompt_data: BaseModel, 
    baml_type_class: Type[BaseModel]
) -> Dict[str, Any]:
    """
    Create structured metadata that groups fields by their containing classes.
    
    Args:
        prompt_data: The actual prompt data object
        baml_type_class: The BAML type class for metadata extraction
        
    Returns:
        Structured metadata dictionary with fields grouped by class
    """
    # Get BAML type metadata
    baml_metadata = get_baml_type_metadata(baml_type_class)
    
    # Analyze fields
    primitive_fields = {}
    composite_fields = {}
    prompt_content = {}
    
    for field_name, field_info in baml_metadata.items():
        if hasattr(prompt_data, field_name):
            field_value = getattr(prompt_data, field_name)
            value_length = len(str(field_value)) if field_value else 0
            
            field_data = {
                "type": field_info["type"],
                "description": field_info["description"],
                "value_length": value_length,
                "value": field_value
            }
            
            if field_info["is_composite"]:
                composite_fields[field_name] = field_data
            else:
                primitive_fields[field_name] = field_data
                
                # Track prompt content fields (string fields with significant content)
                if isinstance(field_value, str) and value_length > 10:
                    prompt_content[field_name] = {
                        "length": value_length,
                        "preview": field_value[:100] + "..." if value_length > 100 else field_value
                    }
    
    # Analyze composite classes
    composite_class_details = {}
    for field_name, field_data in composite_fields.items():
        composite_type = field_data["type"]
        composite_name = _extract_composite_class_name(composite_type)
        
        # Try to get the actual composite class
        try:
            # Import the composite class from baml_types
            from baml_client import types as baml_types
            composite_class = getattr(baml_types, composite_name, None)
            
            if composite_class and issubclass(composite_class, BaseModel):
                composite_class_details[field_name] = _get_composite_class_metadata(composite_class)
            else:
                composite_class_details[field_name] = {
                    "class_name": composite_name,
                    "fields": {},
                    "nested_composites": {}
                }
        except Exception as e:
            print(f"Warning: Could not analyze composite class {composite_name}: {e}")
            composite_class_details[field_name] = {
                "class_name": composite_name,
                "fields": {},
                "nested_composites": {}
            }
    
    # Create structured metadata
    structured_metadata = {
        "prompt_optimization": {
            "type_name": baml_type_class.__name__,
            "total_fields": len(baml_metadata),
            "primitive_field_count": len(primitive_fields),
            "composite_field_count": len(composite_fields),
            "composite_classes": list(composite_fields.keys())
        },
        "field_analysis": {
            "primitive_fields": primitive_fields,
            "composite_fields": composite_fields
        },
        "composite_class_details": composite_class_details,
        "prompt_content": prompt_content
    }
    
    return structured_metadata


def create_span_metadata_with_baml_info(
    prompt_data: BaseModel, 
    baml_type_class: Type[BaseModel],
    additional_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create span metadata that includes BAML type field descriptions and types.
    Enhanced to handle composite types and group fields by their containing classes.
    
    Args:
        prompt_data: The actual prompt data object
        baml_type_class: The BAML type class for metadata extraction
        additional_metadata: Additional metadata to include
        
    Returns:
        Complete span metadata dictionary
    """
    # Get structured metadata
    structured_metadata = create_structured_prompt_metadata(prompt_data, baml_type_class)
    
    # Start with basic metadata
    metadata = {
        "prompt_available_for_optimization": True,
        "baml_type_name": baml_type_class.__name__,
        "structured_metadata": structured_metadata,
    }
    
    # Add the actual prompt data values for primitive fields
    for field_name, field_info in structured_metadata["field_analysis"]["primitive_fields"].items():
        metadata[f"prompt_{field_name}"] = field_info["value"]
        metadata[f"prompt_{field_name}_length"] = field_info["value_length"]
    
    # Add composite field summaries
    for field_name, field_info in structured_metadata["field_analysis"]["composite_fields"].items():
        metadata[f"prompt_{field_name}_type"] = field_info["type"]
        metadata[f"prompt_{field_name}_length"] = field_info["value_length"]
        
        # Add composite class details
        if field_name in structured_metadata["composite_class_details"]:
            composite_details = structured_metadata["composite_class_details"][field_name]
            metadata[f"prompt_{field_name}_class"] = composite_details["class_name"]
            metadata[f"prompt_{field_name}_fields"] = list(composite_details["fields"].keys())
    
    # Add additional metadata if provided
    if additional_metadata:
        metadata.update(additional_metadata)
    
    return metadata 