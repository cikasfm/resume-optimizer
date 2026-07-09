#!/usr/bin/env python3
"""
Shared configuration loader for resume build scripts.
"""
import os
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "resume_config.yaml"
SECRETS_FILE = ROOT / "config" / "secrets.yaml"

_config_cache = None
_secrets_cache = None

def load_config():
    """Load configuration from YAML file."""
    global _config_cache
    if _config_cache is None:
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f)
    
    return _config_cache

def get_output_filename(pattern_key, **kwargs):
    """
    Generate output filename from pattern.
    
    Args:
        pattern_key: Key in output_patterns config (e.g., 'baseline_docx')
        **kwargs: Variables to substitute in pattern (name, timestamp, company, job_title)
    
    Returns:
        Formatted filename string
    """
    config = load_config()
    patterns = config['output_patterns']
    
    if pattern_key not in patterns:
        raise ValueError(f"Unknown output pattern key: {pattern_key}")
    
    pattern = patterns[pattern_key]
    
    # Default values
    defaults = {
        'name': config.get('name', 'Resume'),
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'company': '',
        'job_title': '',
    }
    
    # Merge defaults with provided kwargs
    vars_dict = {**defaults, **kwargs}
    
    # Replace variables in pattern
    filename = pattern.format(**vars_dict)
    
    return filename

def get_path(path_key):
    """Get a path from config, resolved relative to project root."""
    config = load_config()
    paths = config['paths']
    
    if path_key not in paths:
        raise ValueError(f"Unknown path key: {path_key}")
    
    return ROOT / paths[path_key]

def get_ai_config():
    """Get AI configuration section."""
    config = load_config()
    return config.get('ai_prompts', {})

def get_provider_config():
    """Get provider configuration merged with secrets."""
    config = load_config()
    ai_config = config.get('ai_prompts', {})
    secrets = load_secrets()
    
    # Merge config and secrets
    provider_config = {
        'provider': ai_config.get('provider', 'openai'),
        'model': ai_config.get('model', 'gpt-4o'),
        'temperature': ai_config.get('temperature', 0.7),
        'max_tokens': ai_config.get('max_tokens', 8000),
        'ollama_base_url': ai_config.get('ollama_base_url', 'http://localhost:11434'),
        'ollama_model': ai_config.get('ollama_model', 'llama3.2'),
        # API keys from secrets
        'openai_api_key': secrets.get('openai_api_key'),
        'gemini_api_key': secrets.get('gemini_api_key'),
        'groq_api_key': secrets.get('groq_api_key'),
        'huggingface_api_key': secrets.get('huggingface_api_key'),
    }
    
    return provider_config

def load_secrets():
    """Load secrets from secrets.yaml file (if it exists)."""
    global _secrets_cache
    if _secrets_cache is None:
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                _secrets_cache = yaml.safe_load(f) or {}
        else:
            _secrets_cache = {}
    return _secrets_cache

def get_openai_api_key():
    """
    Get OpenAI API key from config/secrets.yaml.
    
    Returns:
        API key string or None if not found
    
    Raises:
        FileNotFoundError: If secrets.yaml doesn't exist
        ValueError: If openai_api_key is not set in secrets.yaml
    """
    secrets = load_secrets()
    api_key = secrets.get('openai_api_key')
    
    if not api_key:
        if not SECRETS_FILE.exists():
            raise FileNotFoundError(
                f"Secrets file not found: {SECRETS_FILE}\n"
                f"Please create it by copying: cp config/secrets.yaml.example config/secrets.yaml\n"
                f"Then edit config/secrets.yaml and add your OpenAI API key."
            )
        else:
            raise ValueError(
                f"openai_api_key not found in {SECRETS_FILE}\n"
                f"Please add your OpenAI API key to the secrets.yaml file."
            )
    
    return api_key
