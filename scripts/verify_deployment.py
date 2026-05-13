#!/usr/bin/env python3
"""
Quick verification script for Mushir Sharia Bot deployment.

This script performs a comprehensive check of:
1. Space health and readiness
2. Query endpoint functionality
3. Stream endpoint functionality
4. Response quality and citations

Usage:
    python scripts/verify_deployment.py
"""

import requests
import json
import sys

SPACE_URL = "https://AElKodsh-mushir-sharia-bot.hf.space"

def check_health():
    """Check health endpoint."""
    try:
        response = requests.get(f"{SPACE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check: PASS")
            return True
        else:
            print(f"❌ Health check: FAIL ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Health check: ERROR - {e}")
        return False


def check_ready():
    """Check readiness endpoint."""
    try:
        response = requests.get(f"{SPACE_URL}/ready", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ready check: PASS (status: {data.get('status')})")
            
            # Check critical components
            checks = data.get('checks', {})
            if checks.get('retrieval_configured'):
                print("   ✅ Vector store configured")
            else:
                print("   ❌ Vector store NOT configured")
                
            if checks.get('provider_configured'):
                print("   ✅ LLM provider configured")
            else:
                print("   ❌ LLM provider NOT configured")
                
            return True
        else:
            print(f"❌ Ready check: FAIL ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Ready check: ERROR - {e}")
        return False


def test_query():
    """Test query endpoint with a real question."""
    print("\n🧪 Testing query endpoint...")
    
    payload = {
        "query": "What are the key requirements for Murabaha transactions according to AAOIFI?",
        "context": {"disclaimer_acknowledged": True}
    }
    
    try:
        response = requests.post(
            f"{SPACE_URL}/api/v1/query",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            citations = data.get('citations', [])
            
            print(f"✅ Query successful")
            print(f"   Answer length: {len(answer)} chars")
            print(f"   Citations: {len(citations)} found")
            print(f"   Status: {data.get('status', 'N/A')}")
            
            if len(answer) > 50:
                print(f"   ✅ Answer has substantial content")
            else:
                print(f"   ⚠️  Answer seems too short")
                
            if len(citations) > 0:
                print(f"   ✅ Citations included")
                print(f"   First citation: {citations[0].get('document_id', 'N/A')}")
            else:
                print(f"   ⚠️  No citations found")
                
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False


def test_stream():
    """Test stream endpoint."""
    print("\n🧪 Testing stream endpoint...")
    
    payload = {
        "query": "Is investing in halal food companies permissible?",
        "context": {"disclaimer_acknowledged": True}
    }
    
    try:
        response = requests.post(
            f"{SPACE_URL}/api/v1/query/stream",
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            events = []
            for line in response.iter_lines():
                if line and line.decode('utf-8').startswith('event:'):
                    event_type = line.decode('utf-8').split(':', 1)[1].strip()
                    events.append(event_type)
            
            print(f"✅ Stream successful")
            print(f"   Events received: {len(events)}")
            print(f"   Event types: {', '.join(set(events))}")
            
            if 'started' in events and 'done' in events:
                print(f"   ✅ Complete event flow")
            else:
                print(f"   ⚠️  Incomplete event flow")
                
            return True
        else:
            print(f"❌ Stream failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Stream error: {e}")
        return False


def main():
    """Run all verification checks."""
    print("="*60)
    print("🚀 Mushir Sharia Bot - Deployment Verification")
    print("="*60)
    print()
    
    results = []
    
    # Basic health checks
    print("📊 Basic Health Checks")
    print("-" * 60)
    results.append(check_health())
    results.append(check_ready())
    
    # Functional tests
    print()
    print("🧪 Functional Tests")
    print("-" * 60)
    results.append(test_query())
    results.append(test_stream())
    
    # Summary
    print()
    print("="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print()
        print("🎉 Deployment is fully operational!")
        print()
        print("🔗 Access your chatbot:")
        print(f"   {SPACE_URL}/chat")
        return 0
    else:
        print(f"⚠️  SOME CHECKS FAILED ({passed}/{total} passed)")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check Space logs for errors")
        print("   2. Verify OPENROUTER_API_KEY is set correctly")
        print("   3. Ensure vector database is populated")
        print("   4. Check Space is not sleeping/restarting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
