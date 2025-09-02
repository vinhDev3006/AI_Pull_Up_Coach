#!/usr/bin/env python3
"""
Test script for backend connection
Tests if the backend server is running and responding correctly
"""

import requests
import json

def test_backend_connection():
    """Test connection to the backend server"""
    print("=== Testing Backend Connection ===")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test status endpoint
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is online")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend - make sure it's running on port 8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Connection timeout - backend may be slow to respond")
        return False
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")
        return False
    
    return True

def test_backend_endpoints():
    """Test various backend endpoints"""
    print("\n=== Testing Backend Endpoints ===")
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/status",
        "/health",
        "/docs",  # FastAPI auto docs
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            elif response.status_code == 404:
                print(f"⚠️  {endpoint} - Not found (may not be implemented)")
            else:
                print(f"❌ {endpoint} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")

def test_cors_headers():
    """Test if CORS headers are properly set"""
    print("\n=== Testing CORS Headers ===")
    
    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        headers = response.headers
        
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        print("CORS Headers:")
        for header in cors_headers:
            value = headers.get(header, "Not set")
            print(f"   {header}: {value}")
            
    except Exception as e:
        print(f"❌ Error checking CORS headers: {e}")

if __name__ == "__main__":
    print("🔗 AI Pull-Up Coach - Backend Connection Test")
    print("=" * 50)
    
    try:
        # Test 1: Basic connection
        if test_backend_connection():
            print("\n🔄 Backend is responding, testing additional endpoints...")
            
            # Test 2: Additional endpoints
            test_backend_endpoints()
            
            # Test 3: CORS headers
            test_cors_headers()
            
        print("\n✅ Backend connection test complete!")
        
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
    
    print("\n💡 To start the backend server, run:")
    print("   python -m uvicorn main:app --reload --port 8000")