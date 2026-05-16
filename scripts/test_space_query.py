#!/usr/bin/env python3
"""
Test the deployed Hugging Face Space with a real query.

Usage:
    python scripts/test_space_query.py [--endpoint query|stream|all]
    
Examples:
    python scripts/test_space_query.py                    # Test both endpoints
    python scripts/test_space_query.py --endpoint query   # Test query only
    python scripts/test_space_query.py --endpoint stream  # Test stream only
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

import requests

__test__ = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Configuration
@dataclass
class Config:
    """Test configuration."""
    space_url: str = "https://AElKodsh-mushir-sharia-bot.hf.space"
    timeout: int = 60
    max_answer_preview: int = 200
    max_citation_preview: int = 80
    max_error_preview: int = 500
    max_citations_display: int = 3


@dataclass
class TestResult:
    """Test result container."""
    endpoint: str
    success: bool
    duration: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


# Utility functions
def create_payload(query: str) -> Dict[str, Any]:
    """Create a standard test payload."""
    return {
        "query": query,
        "context": {
            "disclaimer_acknowledged": True
        }
    }


def print_section(title: str, width: int = 60):
    """Print a formatted section header."""
    print("\n" + "=" * width)
    print(title)
    print("=" * width)
    print()


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text with ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def handle_request_error(error: Exception) -> str:
    """Convert request exception to user-friendly message."""
    if isinstance(error, requests.exceptions.Timeout):
        return "Request timeout - Space might be cold-starting or overloaded"
    elif isinstance(error, requests.exceptions.ConnectionError):
        return f"Connection error - Space might be down or restarting: {error}"
    elif isinstance(error, requests.exceptions.JSONDecodeError):
        return f"Invalid JSON response: {error}"
    else:
        return f"Unexpected error: {error}"


# Test functions
def test_query_endpoint(config: Config) -> TestResult:
    """Test the /api/v1/query endpoint."""
    endpoint = "/api/v1/query"
    print(f"🧪 Testing {endpoint}")
    print(f"   URL: {config.space_url}{endpoint}")
    print()
    
    payload = create_payload(
        "I want to invest in a company that produces halal food. Is this permissible?"
    )
    
    print(f"📤 Sending query: {payload['query']}")
    print()
    
    try:
        start = time.time()
        response = requests.post(
            f"{config.space_url}{endpoint}",
            json=payload,
            timeout=config.timeout
        )
        duration = time.time() - start
        
        print(f"⏱️  Response time: {duration:.2f}s")
        print(f"📊 Status code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            _print_query_success(data, config)
            return TestResult(
                endpoint=endpoint,
                success=True,
                duration=duration,
                status_code=response.status_code,
                response_data=data
            )
        else:
            _print_query_error(response, config)
            return TestResult(
                endpoint=endpoint,
                success=False,
                duration=duration,
                status_code=response.status_code,
                error=f"HTTP {response.status_code}"
            )
            
    except Exception as e:
        error_msg = handle_request_error(e)
        print(f"❌ {error_msg}")
        return TestResult(
            endpoint=endpoint,
            success=False,
            duration=0,
            error=error_msg
        )


def _print_query_success(data: Dict[str, Any], config: Config):
    """Print successful query response."""
    print("✅ Query successful!")
    print()
    print("📝 Response:")
    
    answer = data.get('answer', 'N/A')
    print(f"   Answer: {truncate_text(answer, config.max_answer_preview)}")
    print(f"   Status: {data.get('status', 'N/A')}")
    
    citations = data.get('citations', [])
    print(f"   Citations: {len(citations)} found")
    print()
    
    if citations:
        print("📚 Citations:")
        for i, citation in enumerate(citations[:config.max_citations_display], 1):
            doc_id = citation.get('document_id', 'N/A')
            text = citation.get('text', 'N/A')
            print(f"   {i}. {doc_id} - {truncate_text(text, config.max_citation_preview)}")
    
    print()
    print("🎯 Full response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _print_query_error(response: requests.Response, config: Config):
    """Print query error details."""
    if response.status_code == 500:
        print("❌ Internal server error")
        print(f"   Response: {truncate_text(response.text, config.max_error_preview)}")
        print()
        print("💡 This might indicate:")
        print("   - Missing or invalid OPENROUTER_API_KEY")
        print("   - Vector database not accessible")
        print("   - LLM client initialization failure")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
        print(f"   Response: {truncate_text(response.text, config.max_error_preview)}")


def test_stream_endpoint(config: Config) -> TestResult:
    """Test the /api/v1/query/stream endpoint."""
    endpoint = "/api/v1/query/stream"
    print_section(f"🧪 Testing {endpoint}")
    
    payload = create_payload("What are the requirements for Murabaha transactions?")
    
    print(f"📤 Sending query: {payload['query']}")
    print()
    
    try:
        start = time.time()
        response = requests.post(
            f"{config.space_url}{endpoint}",
            json=payload,
            stream=True,
            timeout=config.timeout
        )
        
        if response.status_code == 200:
            _process_stream_response(response, config)
            duration = time.time() - start
            
            print()
            print("✅ Stream completed successfully")
            return TestResult(
                endpoint=endpoint,
                success=True,
                duration=duration,
                status_code=response.status_code
            )
        else:
            print(f"❌ Stream failed: {response.status_code}")
            print(f"   Response: {truncate_text(response.text, config.max_error_preview)}")
            return TestResult(
                endpoint=endpoint,
                success=False,
                duration=0,
                status_code=response.status_code,
                error=f"HTTP {response.status_code}"
            )
            
    except Exception as e:
        error_msg = handle_request_error(e)
        print(f"❌ {error_msg}")
        return TestResult(
            endpoint=endpoint,
            success=False,
            duration=0,
            error=error_msg
        )


def _process_stream_response(response: requests.Response, config: Config):
    """Process and display streaming response."""
    print("✅ Stream started")
    print()
    print("📡 Events:")
    current_event = None
    
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('event:'):
                event_type = decoded.split(':', 1)[1].strip()
                current_event = event_type
                print(f"   • {event_type}")
            elif decoded.startswith('data:'):
                try:
                    data = json.loads(decoded.split(':', 1)[1].strip())
                    if current_event == "error":
                        raise RuntimeError(f"SSE error event: {data}")
                    if 'text' in data:
                        print(f"     Text: {truncate_text(data['text'], config.max_citation_preview)}")
                    elif 'confidence' in data:
                        print(f"     Confidence: {data['confidence']:.2f}")
                except json.JSONDecodeError:
                    print(f"     [Invalid JSON data]")


def print_summary(results: list[TestResult]):
    """Print test summary."""
    print_section("📊 Test Summary")
    
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print()
    
    if failed > 0:
        print("Failed tests:")
        for result in results:
            if not result.success:
                print(f"  • {result.endpoint}: {result.error}")
        print()
    
    # Return exit code
    return 0 if failed == 0 else 1


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Test Mushir Sharia Bot Hugging Face Space"
    )
    parser.add_argument(
        "--endpoint",
        choices=["query", "stream", "all"],
        default="all",
        help="Which endpoint to test (default: all)"
    )
    parser.add_argument(
        "--space-url",
        default=None,
        help="Override Space URL (default: from Config)"
    )
    
    args = parser.parse_args()
    
    # Create config
    config = Config()
    if args.space_url:
        config.space_url = args.space_url
    
    print_section("🚀 Mushir Sharia Bot - Space Testing")
    
    results = []
    
    # Run tests based on selection
    if args.endpoint in ["query", "all"]:
        results.append(test_query_endpoint(config))
    
    if args.endpoint in ["stream", "all"]:
        results.append(test_stream_endpoint(config))
    
    # Print summary and exit
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
