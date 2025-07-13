# TradingView Session ID Validator (Improved)
# Session ID: z8nqrjhcbxhsmemof1zewvuy9wsojv8l

import requests
import json
from typing import Dict, Any, Optional


def validate_tradingview_session(session_id: str) -> Dict[str, Any]:
    """
    Validate a TradingView session ID using multiple authentication-required endpoints
    
    Args:
        session_id (str): The TradingView session ID to validate
        
    Returns:
        Dict[str, Any]: Dictionary containing validation results
    """
    
    # TradingView session cookies
    cookies = {
        'sessionid': session_id
    }
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.tradingview.com/',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    results = {
        'session_id': session_id,
        'valid': False,
        'error': None,
        'tests_passed': 0,
        'total_tests': 0,
        'detailed_results': {}
    }
    
    # Test 1: User account endpoint (requires authentication)
    print("🔍 Test 1: User Account Endpoint...")
    try:
        account_url = 'https://www.tradingview.com/accounts/settings/'
        response = requests.get(account_url, cookies=cookies, headers=headers, timeout=10)
        results['total_tests'] += 1
        
        if response.status_code == 200 and 'settings' in response.text.lower():
            results['tests_passed'] += 1
            results['detailed_results']['account_access'] = True
            print("  ✅ Account settings accessible")
        else:
            results['detailed_results']['account_access'] = False
            print(f"  ❌ Account settings inaccessible ({response.status_code})")
            
    except Exception as e:
        results['detailed_results']['account_access'] = False
        print(f"  ❌ Account test failed: {e}")
    
    # Test 2: Watchlist endpoint (requires authentication)
    print("🔍 Test 2: Watchlist Endpoint...")
    try:
        watchlist_url = 'https://www.tradingview.com/api/v1/watchlists/'
        response = requests.get(watchlist_url, cookies=cookies, headers=headers, timeout=10)
        results['total_tests'] += 1
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) or 'watchlists' in str(data):
                    results['tests_passed'] += 1
                    results['detailed_results']['watchlist_access'] = True
                    print("  ✅ Watchlist accessible")
                else:
                    results['detailed_results']['watchlist_access'] = False
                    print("  ❌ Watchlist response unexpected")
            except:
                results['detailed_results']['watchlist_access'] = False
                print("  ❌ Watchlist response not JSON")
        else:
            results['detailed_results']['watchlist_access'] = False
            print(f"  ❌ Watchlist inaccessible ({response.status_code})")
            
    except Exception as e:
        results['detailed_results']['watchlist_access'] = False
        print(f"  ❌ Watchlist test failed: {e}")
    
    # Test 3: Private screener endpoint that requires auth
    print("🔍 Test 3: Private Screener Features...")
    try:
        # Test with a query that should require authentication for full features
        screener_url = 'https://scanner.tradingview.com/america/scan'
        
        # Query for pro features that require authentication
        payload = {
            "filter": [],
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name", "close", "update_mode", "market_cap_basic", "pe_ratio"],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [0, 10]
        }
        
        response = requests.post(screener_url, json=payload, cookies=cookies, headers=headers, timeout=10)
        results['total_tests'] += 1
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                sample_row = data['data'][0]
                update_mode = sample_row.get('d', [None, None, None])[2] if len(sample_row.get('d', [])) > 2 else None
                
                # Real-time data indicates valid premium session
                if update_mode == 'streaming':
                    results['tests_passed'] += 1
                    results['detailed_results']['realtime_data'] = True
                    print(f"  ✅ Real-time data access (streaming)")
                else:
                    results['detailed_results']['realtime_data'] = False
                    print(f"  ⏰ Only delayed data access ({update_mode})")
            else:
                results['detailed_results']['realtime_data'] = False
                print("  ❌ No screener data returned")
        else:
            results['detailed_results']['realtime_data'] = False
            print(f"  ❌ Screener failed ({response.status_code})")
            
    except Exception as e:
        results['detailed_results']['realtime_data'] = False
        print(f"  ❌ Screener test failed: {e}")
    
    # Test 4: Check if user is authenticated in any page
    print("🔍 Test 4: Authentication Status Check...")
    try:
        main_url = 'https://www.tradingview.com/'
        response = requests.get(main_url, cookies=cookies, headers=headers, timeout=10)
        results['total_tests'] += 1
        
        # Look for authentication indicators in the HTML
        if 'is-authenticated' in response.text or '"isAuthenticated":true' in response.text:
            results['tests_passed'] += 1
            results['detailed_results']['authenticated_status'] = True
            print("  ✅ Authenticated status detected")
        else:
            results['detailed_results']['authenticated_status'] = False
            print("  ❌ Not authenticated")
            
    except Exception as e:
        results['detailed_results']['authenticated_status'] = False
        print(f"  ❌ Authentication check failed: {e}")
    
    # Determine overall validity
    if results['tests_passed'] >= 2:  # At least 2 tests must pass
        results['valid'] = True
    else:
        results['valid'] = False
        results['error'] = f"Only {results['tests_passed']}/{results['total_tests']} authentication tests passed"
    
    return results


def test_session_comparison(session_id: str) -> Dict[str, Any]:
    """
    Compare the session with a definitely invalid session to see differences
    """
    print("\n🔍 Comparison Test: Valid vs Invalid Session...")
    
    # Test with obviously invalid session
    invalid_session = "invalid_session_12345"
    
    cookies_valid = {'sessionid': session_id}
    cookies_invalid = {'sessionid': invalid_session}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.tradingview.com/'
    }
    
    screener_url = 'https://scanner.tradingview.com/america/scan'
    payload = {
        "filter": [],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "close", "update_mode"],
        "sort": {"sortBy": "name", "sortOrder": "asc"},
        "range": [0, 5]
    }
    
    try:
        # Test with provided session
        response_valid = requests.post(screener_url, json=payload, cookies=cookies_valid, headers=headers, timeout=10)
        
        # Test with invalid session  
        response_invalid = requests.post(screener_url, json=payload, cookies=cookies_invalid, headers=headers, timeout=10)
        
        print(f"Your session response: {response_valid.status_code}")
        print(f"Invalid session response: {response_invalid.status_code}")
        
        if response_valid.status_code == 200 and response_invalid.status_code == 200:
            data_valid = response_valid.json()
            data_invalid = response_invalid.json()
            
            # Compare update modes
            update_mode_valid = None
            update_mode_invalid = None
            
            if 'data' in data_valid and len(data_valid['data']) > 0:
                sample = data_valid['data'][0]
                update_mode_valid = sample.get('d', [None, None, None])[2] if len(sample.get('d', [])) > 2 else None
                
            if 'data' in data_invalid and len(data_invalid['data']) > 0:
                sample = data_invalid['data'][0]
                update_mode_invalid = sample.get('d', [None, None, None])[2] if len(sample.get('d', [])) > 2 else None
            
            print(f"Your session update mode: {update_mode_valid}")
            print(f"Invalid session update mode: {update_mode_invalid}")
            
            # If they're different, that's a good sign
            if update_mode_valid != update_mode_invalid:
                print("✅ Sessions produce different results - validation is working")
                return {
                    'comparison_valid': True,
                    'your_update_mode': update_mode_valid,
                    'invalid_update_mode': update_mode_invalid,
                    'session_matters': True
                }
            else:
                print("⚠️ Both sessions produce same results - screener may not require auth")
                return {
                    'comparison_valid': False,
                    'your_update_mode': update_mode_valid,
                    'invalid_update_mode': update_mode_invalid,
                    'session_matters': False
                }
        
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return {'comparison_valid': False, 'error': str(e)}
    
    return {'comparison_valid': False}


if __name__ == "__main__":
    # The session ID from your file
    session_id = "tkfi0exuv4mkvd8izlp1ev798qx1zdv3"
    
    print(f"🔍 IMPROVED TradingView Session ID Validation")
    print(f"Session ID: {session_id}")
    print("=" * 80)
    
    # Run comprehensive validation tests
    results = validate_tradingview_session(session_id)
    
    # Run comparison test
    comparison_results = test_session_comparison(session_id)
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE VALIDATION RESULTS:")
    print("=" * 80)
    
    print(f"Session ID: {results['session_id']}")
    print(f"Tests Passed: {results['tests_passed']}/{results['total_tests']}")
    print(f"Overall Valid: {results['valid']}")
    
    if results['error']:
        print(f"Error: {results['error']}")
    
    print("\nDetailed Test Results:")
    for test, result in results['detailed_results'].items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test}: {status}")
    
    print(f"\nComparison Test Results:")
    for key, value in comparison_results.items():
        print(f"  {key}: {value}")
    
    print("\n🎯 FINAL VERDICT:")
    if results['valid'] and results['tests_passed'] >= 2:
        print("✅ Session ID is VALID and AUTHENTICATED!")
        if results['detailed_results'].get('realtime_data'):
            print("🚀 You have REAL-TIME data access!")
        else:
            print("⏰ You have basic/delayed data access")
    else:
        print("❌ Session ID is INVALID or NOT PROPERLY AUTHENTICATED")
        print("   - The session may provide some public data access")
        print("   - But it's not a valid authenticated session")