#!/usr/bin/env python3
"""
Simple test script to verify proxy connection to Google API.
Uses only Python standard library - no pip install required.
"""

import urllib.request
import urllib.error
import json
import sys
import os

def test_proxy_google_api(api_key=None, proxy_url=None):
    """
    Test if proxy can connect to Google API.
    
    Args:
        api_key: Optional Gemini API key (if not provided, will try to get from env)
        proxy_url: Optional proxy URL (if not provided, will try to get from env)
    """
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            print("❌ Error: GEMINI_API_KEY not found in environment")
            print("   Usage: GEMINI_API_KEY=your_key python3 test_proxy_google_api.py")
            print("   Or: python3 test_proxy_google_api.py --api-key your_key")
            return False
    
    # Get proxy from environment if not provided
    if not proxy_url:
        proxy_url = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('http_proxy') or os.getenv('https_proxy')
    
    # Setup proxy if provided
    if proxy_url:
        print(f"🔧 Using proxy: {proxy_url}")
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
    else:
        print("⚠️  No proxy configured (using direct connection)")
    
    # Test 1: Simple Google API endpoint (list models)
    print("\n📡 Test 1: Testing connection to Google API (list models)...")
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + api_key
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Python-Proxy-Test/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("✅ Connection successful!")
            print(f"   Status: {response.status}")
            if 'models' in data:
                print(f"   Found {len(data.get('models', []))} models")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        if e.code == 403:
            print("   ⚠️  403 Forbidden - API key might be invalid or proxy blocked")
        elif e.code == 407:
            print("   ⚠️  407 Proxy Authentication Required - proxy needs credentials")
        try:
            error_body = e.read().decode('utf-8')
            print(f"   Response: {error_body[:200]}")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e.reason}")
        if "proxy" in str(e.reason).lower() or "407" in str(e.reason):
            print("   ⚠️  Proxy connection failed - check proxy settings")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


def test_simple_google_connection():
    """Test basic connection to Google (no API key needed)."""
    print("\n📡 Test 2: Testing basic connection to Google.com...")
    try:
        url = "https://www.google.com"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Python-Proxy-Test/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"✅ Basic connection successful! Status: {response.status}")
            return True
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test proxy connection to Google API (no pip install required)"
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key (or set GEMINI_API_KEY env var)",
        default=None
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL (or set HTTP_PROXY/HTTPS_PROXY env var)",
        default=None
    )
    parser.add_argument(
        "--basic-only",
        action="store_true",
        help="Only test basic Google connection (no API key needed)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔍 Google API Proxy Test Script")
    print("=" * 60)
    
    # Test basic connection first
    basic_ok = test_simple_google_connection()
    
    if args.basic_only:
        sys.exit(0 if basic_ok else 1)
    
    # Test API connection
    if basic_ok:
        api_ok = test_proxy_google_api(api_key=args.api_key, proxy_url=args.proxy)
        sys.exit(0 if api_ok else 1)
    else:
        print("\n❌ Basic connection failed - cannot test API")
        sys.exit(1)

