#!/usr/bin/env python3
"""
Optimize resume for a specific job posting using AI.

Usage:
    python scripts/optimize_resume.py <job_description_url> [--company COMPANY] [--verbose]

Options:
    --company, -c    Company name (for file naming)
    --verbose, -v   Show detailed error information when errors occur

API Key Configuration:
    Set your OpenAI API key in config/secrets.yaml:
    1. Copy the example: cp config/secrets.yaml.example config/secrets.yaml
    2. Edit config/secrets.yaml and add your API key
"""
# Suppress urllib3 OpenSSL warning on macOS (LibreSSL compatibility) BEFORE any imports
# This warning appears because macOS Python uses LibreSSL instead of OpenSSL
# It's harmless and doesn't affect functionality - urllib3 v2 works fine with LibreSSL
import os
import sys
import warnings

# Custom warning filter function to suppress urllib3 OpenSSL warnings
_original_showwarning = warnings.showwarning

def _filter_urllib3_warnings(message, category, filename, lineno, file=None, line=None):
    """Filter out urllib3 OpenSSL warnings."""
    if 'urllib3' in str(filename) and ('OpenSSL' in str(message) or 'NotOpenSSLWarning' in str(category)):
        return  # Suppress this warning
    _original_showwarning(message, category, filename, lineno, file, line)

warnings.showwarning = _filter_urllib3_warnings

# Also use standard warning filters
warnings.filterwarnings('ignore', message='.*urllib3.*OpenSSL.*')
warnings.filterwarnings('ignore', message='.*NotOpenSSLWarning.*')
warnings.filterwarnings('ignore', category=UserWarning, module='urllib3')

# Import urllib3 and disable warnings
import urllib3
try:
    # Try to disable the specific NotOpenSSLWarning
    urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)
except (AttributeError, TypeError):
    # Fallback: disable all urllib3 warnings
    urllib3.disable_warnings()

import json
import re
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from datetime import datetime
# OpenAI imports are now optional - only needed if using OpenAI provider
sys.path.insert(0, str(Path(__file__).parent))
from config_loader import get_path, get_output_filename, get_ai_config, get_provider_config
from ai_providers import get_provider

ROOT = Path(__file__).resolve().parents[1]
RESUME_SRC = get_path('resume_source')
OUTDIR = get_path('optimized_dir')
CHANGELOG_FILE = get_path('changelog')

def fetch_job_description(url):
    """Fetch job description content from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Try to extract text content (basic implementation)
        # For better results, consider using libraries like beautifulsoup4 or readability
        content = response.text
        
        # Simple text extraction - remove HTML tags crudely
        # In production, you might want to use beautifulsoup4 for better parsing
        import re
        # Remove script and style elements
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content[:10000]  # Limit to first 10k chars to avoid token limits
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch job description from {url}: {e}")

def read_resume():
    """Read current resume markdown."""
    if not RESUME_SRC.exists():
        raise FileNotFoundError(f"Resume file not found: {RESUME_SRC}")
    
    return RESUME_SRC.read_text(encoding='utf-8')

def call_ai_provider(job_description, current_resume, verbose=False):
    """Call AI provider to optimize resume and generate cover letter.
    
    Args:
        job_description: The job description text
        current_resume: The current resume markdown
        verbose: If True, include detailed error information in error messages
    """
    # Get provider configuration
    provider_config = get_provider_config()
    ai_config = get_ai_config()
    
    provider_name = provider_config['provider']
    
    # Store provider_name for error handling
    global _current_provider_name
    _current_provider_name = provider_name
    
    # Get the appropriate provider
    try:
        provider = get_provider(provider_name, provider_config)
    except ValueError as e:
        raise RuntimeError(
            f"❌ Provider Configuration Error\n\n"
            f"Failed to initialize AI provider '{provider_name}'.\n\n"
            f"💡 Details: {str(e)}\n\n"
            f"📋 Available FREE providers:\n"
            f"  • ollama - Install locally: https://ollama.ai (completely free)\n"
            f"  • gemini - Get API key: https://makersuite.google.com/app/apikey (free tier)\n"
            f"  • groq - Get API key: https://console.groq.com/keys (free tier, very fast)\n"
            f"  • huggingface - Get API key: https://huggingface.co/settings/tokens (free tier)\n\n"
            f"Set 'provider' in config/resume_config.yaml and add API keys to config/secrets.yaml"
        )
    
    # Construct the prompt
    system_prompt = ai_config['resume_optimization_prompt']
    cover_letter_prompt = ai_config['cover_letter_prompt']
    changelog_instructions = ai_config['changelog_instructions']
    
    user_prompt = f"""Please optimize my resume for the following job description and generate a cover letter.

JOB DESCRIPTION:
{job_description}

CURRENT RESUME:
{current_resume}

Please provide your response in the following JSON format:
{{
  "optimized_resume": "<the optimized resume in markdown format>",
  "cover_letter": "<the cover letter in markdown format>",
  "changelog": "<list of changes made, formatted as markdown bullets>"
}}

{changelog_instructions}

{cover_letter_prompt}
"""
    
    try:
        # Call the provider
        # Pass verbose flag to provider so it can return raw/debug info when requested
        content_result = provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=provider_config.get('model'),
            temperature=provider_config.get('temperature', 0.7),
            max_tokens=provider_config.get('max_tokens', 8000),
            verbose=verbose
        )

        # Provider may return either a raw string or a dict with 'text' and 'raw' when verbose
        raw_provider_response = None
        if isinstance(content_result, dict):
            raw_provider_response = content_result.get('raw')
            content = content_result.get('text', '')
        else:
            content = content_result

        # When verbose, print raw provider response (LLM output / thinking) for debugging
        if verbose and raw_provider_response is not None:
            try:
                print('\n--- LLM raw response (debug) ---')
                print(json.dumps(raw_provider_response, indent=2))
                print('--- end LLM raw response ---\n')
            except Exception:
                print('\n--- LLM raw response (debug) ---')
                print(str(raw_provider_response))
                print('--- end LLM raw response ---\n')
        
        # Try to extract JSON from the response
        # Sometimes the model wraps JSON in markdown code blocks
        json_str = None
        
        # First try: Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Second try: Find JSON object directly (handle nested braces)
            # Use a more sophisticated approach to find balanced braces
            brace_count = 0
            start_idx = content.find('{')
            if start_idx != -1:
                for i in range(start_idx, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = content[start_idx:i+1]
                            break
        
        if not json_str:
            # Last resort: Save the raw response for debugging
            debug_file = OUTDIR / f"ai_response_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            OUTDIR.mkdir(parents=True, exist_ok=True)
            debug_file.write_text(content, encoding='utf-8')
            raise ValueError(
                f"Could not extract JSON from AI response. "
                f"Raw response saved to {debug_file} for debugging."
            )
        
        try:
            result = json.loads(json_str)
            # Validate required fields
            required_fields = ['optimized_resume', 'cover_letter', 'changelog']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                raise ValueError(f"Missing required fields in AI response: {', '.join(missing_fields)}")
            return result
        except json.JSONDecodeError as e:
            # Save problematic JSON for debugging
            debug_file = OUTDIR / f"ai_response_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            OUTDIR.mkdir(parents=True, exist_ok=True)
            debug_file.write_text(f"JSON Parse Error: {e}\n\nExtracted JSON:\n{json_str}\n\nFull Response:\n{content}", encoding='utf-8')
            raise ValueError(
                f"Failed to parse JSON from AI response: {e}. "
                f"Debug info saved to {debug_file}"
            )
    
    except Exception as e:
        # Generic error handling for all providers
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Get provider name from global (set before try block)
        provider_name = globals().get('_current_provider_name', 'AI')
        
        # Check for common error patterns
        if 'insufficient_quota' in error_msg or ('429' in error_msg and 'quota' in error_msg.lower()):
            msg = (
                f"❌ {provider_name.upper()} API Quota Exceeded\n\n"
                f"Your {provider_name} account has no credits remaining.\n\n"
            )
            if provider_name == 'openai':
                msg += (
                    "📋 Steps to fix:\n"
                    "  1. Visit https://platform.openai.com/account/billing\n"
                    "  2. Add a payment method or purchase credits\n"
                    "  3. Verify your account has available quota\n"
                )
            else:
                msg += (
                    f"📋 Consider switching to a FREE provider:\n"
                    f"  • ollama - Install locally: https://ollama.ai\n"
                    f"  • gemini - Free tier: https://makersuite.google.com/app/apikey\n"
                    f"  • groq - Free tier: https://console.groq.com/keys\n"
                )
            if verbose:
                msg += f"\n💡 Details: {error_msg}"
            raise RuntimeError(msg)
        
        elif 'invalid_api_key' in error_msg or '401' in error_msg or 'authentication' in error_msg.lower():
            msg = (
                f"🔑 {provider_name.upper()} API Authentication Failed\n\n"
                f"Your API key is invalid or has been revoked.\n\n"
                f"📋 Steps to fix:\n"
                f"  1. Check your API key in: config/secrets.yaml\n"
                f"  2. Get a new API key from the provider's website\n"
                f"  3. Make sure there are no extra spaces or quotes around the key\n"
            )
            if verbose:
                msg += f"\n💡 Details: {error_msg}"
            raise RuntimeError(msg)
        
        elif 'rate_limit' in error_msg or ('429' in error_msg and 'rate' in error_msg.lower()):
            msg = (
                f"⏱️  {provider_name.upper()} API Rate Limit Exceeded\n\n"
                f"You're making requests too quickly. Please wait a moment and try again.\n"
            )
            if verbose:
                msg += f"\n💡 Details: {error_msg}"
            raise RuntimeError(msg)
        
        elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
            msg = (
                f"🌐 {provider_name.upper()} Connection Error\n\n"
                f"Unable to connect to {provider_name} servers.\n\n"
            )
            if provider_name == 'ollama':
                msg += (
                    "📋 Steps to fix:\n"
                    "  1. Make sure Ollama is installed: https://ollama.ai\n"
                    "  2. Start Ollama: ollama serve\n"
                    "  3. Pull the model: ollama pull llama3.2\n"
                )
            else:
                msg += (
                    "📋 Steps to fix:\n"
                    "  1. Check your internet connection\n"
                    "  2. Check the provider's status page\n"
                    "  3. Try again in a few minutes\n"
                )
            if verbose:
                msg += f"\n💡 Details: {error_msg}"
            raise RuntimeError(msg)
        
        else:
            msg = (
                f"❌ {provider_name.upper()} API Error\n\n"
                f"An error occurred while calling the {provider_name} API.\n\n"
            )
            if verbose:
                msg += f"💡 Details: {error_msg}\n\n"
            msg += (
                f"📋 Troubleshooting:\n"
                f"  1. Check your API key in config/secrets.yaml\n"
                f"  2. Verify the provider is set correctly in config/resume_config.yaml\n"
                f"  3. Try switching to a different provider\n"
            )
            raise RuntimeError(msg)

def save_outputs(optimized_resume, cover_letter, changelog, job_url, company=None):
    """Save optimized resume, cover letter, and update changelog."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save optimized resume using config pattern
    resume_filename = get_output_filename('optimized_resume', timestamp=timestamp)
    resume_out = OUTDIR / resume_filename
    resume_out.write_text(optimized_resume, encoding='utf-8')
    print(f"✓ Saved optimized resume: {resume_out}")
    
    # Save cover letter using config pattern
    cover_letter_filename = get_output_filename('optimized_cover_letter', timestamp=timestamp)
    cover_letter_out = OUTDIR / cover_letter_filename
    cover_letter_out.write_text(cover_letter, encoding='utf-8')
    print(f"✓ Saved cover letter: {cover_letter_out}")
    
    # Update changelog
    update_changelog(changelog, job_url, timestamp, company)
    
    return resume_out, cover_letter_out, timestamp

def update_changelog(changelog, job_url, timestamp, company=None):
    """Append changelog entry to CHANGELOG.md."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    company_info = f"\n**Company:** {company}" if company else ""
    
    entry = f"""
## {date_str} - Resume Optimization

**Job Posting:** {job_url}{company_info}
**Timestamp:** {timestamp}

### Changes Made:
{changelog}

---
"""
    
    # Append to changelog file
    if CHANGELOG_FILE.exists():
        current_content = CHANGELOG_FILE.read_text(encoding='utf-8')
    else:
        current_content = "# Resume Optimization Changelog\n\n"
    
    CHANGELOG_FILE.write_text(current_content + entry, encoding='utf-8')
    print(f"✓ Updated changelog: {CHANGELOG_FILE}")

def print_banner():
    """Print ASCII art banner for Resume Optimizer."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║                  RESUME OPTIMIZER                         ║
    ║                                                           ║
    ║         AI-Powered Resume Optimization Tool               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    import argparse
    
    # Print banner first
    print_banner()
    
    parser = argparse.ArgumentParser(description='Optimize resume for a specific job posting')
    parser.add_argument('job_url', help='URL to the job description')
    parser.add_argument('--company', '-c', help='Company name (for file naming)', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed error information')
    
    args = parser.parse_args()
    job_url = args.job_url
    company = args.company
    verbose = args.verbose
    
    print(f"\n🔍 Fetching job description from: {job_url}")
    try:
        job_description = fetch_job_description(job_url)
        print(f"✓ Fetched job description ({len(job_description)} characters)")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("📄 Loading current resume...")
    try:
        current_resume = read_resume()
        print(f"✓ Loaded resume ({len(current_resume)} characters)")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    provider_config = get_provider_config()
    provider_name = provider_config['provider']
    print(f"🤖 Calling {provider_name.upper()} API to optimize resume...")
    try:
        results = call_ai_provider(job_description, current_resume, verbose=verbose)
        print("✓ AI optimization complete")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("💾 Saving outputs...")
    try:
        resume_out, cover_letter_out, timestamp = save_outputs(
            results['optimized_resume'],
            results['cover_letter'],
            results['changelog'],
            job_url,
            company=company
        )
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("\n✅ Resume optimization complete!")
    print(f"\n📝 Review the optimized resume: {resume_out}")
    print(f"📧 Review the cover letter: {cover_letter_out}")
    print(f"📋 Changelog updated: {CHANGELOG_FILE}")

if __name__ == "__main__":
    main()
