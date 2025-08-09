# %%
import ccxt
import pandas as pd

# Initialize Binance exchange for futures (no API key needed for market data)
exchange = ccxt.binance({
    'sandbox': False,  # Set to True for testnet
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Use futures instead of spot
    }
})

def get_usdt_futures():
    """Get all USDT futures trading pairs from Binance"""
    try:
        # Load markets
        markets = exchange.load_markets()
        
        # Filter for USDT futures
        usdt_futures = []
        for symbol, market in markets.items():
            if (market['quote'] == 'USDT' and 
                market['type'] == 'future' and 
                market['active']):
                usdt_futures.append({
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'contract_size': market.get('contractSize', 'N/A'),
                    'settlement': market.get('settle', 'N/A')
                })
        
        return usdt_futures
        
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

# Get and display USDT futures
print("Fetching USDT futures from Binance...")
usdt_pairs = get_usdt_futures()

if usdt_pairs:
    print(f"\nFound {len(usdt_pairs)} USDT futures pairs:")
    print("-" * 60)
    
    # Create DataFrame for better display
    df = pd.DataFrame(usdt_pairs)
    print(df.to_string(index=False))
    
    # Also print just the symbols
    print(f"\nSymbols only:")
    symbols = [pair['symbol'] for pair in usdt_pairs]
    for i, symbol in enumerate(symbols, 1):
        print(f"{i:3d}. {symbol}")
        
    print(f"\nTotal: {len(symbols)} USDT futures pairs")
else:
    print("No USDT futures found or error occurred.")

def debug_markets():
    """Debug function to understand market structure"""
    try:
        markets = exchange.load_markets()
        print(f"Total markets found: {len(markets)}")
        
        # Show some sample market data
        print("\nSample market structure:")
        count = 0
        for symbol, market in markets.items():
            if 'USDT' in symbol and count < 3:  # Show first 3 USDT markets
                print(f"Symbol: {symbol}")
                print(f"Type: {market.get('type')}")
                print(f"Quote: {market.get('quote')}")
                print(f"Active: {market.get('active')}")
                print(f"Linear: {market.get('linear')}")
                print(f"Contract: {market.get('contract')}")
                print("-" * 40)
                count += 1
            
        # Count by type and quote currency
        futures_count = 0
        usdt_count = 0
        usdt_futures_count = 0
        linear_count = 0
        
        for symbol, market in markets.items():
            if market.get('type') == 'future':
                futures_count += 1
            if market.get('quote') == 'USDT':
                usdt_count += 1
            if market.get('type') == 'future' and market.get('quote') == 'USDT':
                usdt_futures_count += 1
            if market.get('linear') == True and market.get('quote') == 'USDT':
                linear_count += 1
                
        print(f"\nMarket counts:")
        print(f"Total markets: {len(markets)}")
        print(f"Total futures: {futures_count}")
        print(f"Total USDT pairs: {usdt_count}")
        print(f"USDT futures: {usdt_futures_count}")
        print(f"Linear USDT: {linear_count}")
        
        return markets
    except Exception as e:
        print(f"Error in debug: {e}")
        return {}

print("\n" + "="*50)
print("=== DEBUGGING MARKET STRUCTURE ===")
markets_data = debug_markets()

# Better function to get all USDT futures including perpetuals with leverage
def get_all_usdt_futures_with_leverage():
    """Get ALL USDT futures trading pairs from Binance including perpetuals with leverage info"""
    try:
        markets = exchange.load_markets()
        
        usdt_futures = []
        for symbol, market in markets.items():
            # Include both future type and linear contracts with USDT quote
            if (market.get('quote') == 'USDT' and 
                market.get('active') and
                (market.get('type') == 'future' or market.get('linear') == True)):
                
                # Get leverage information
                leverage_info = market.get('limits', {}).get('leverage', {})
                max_leverage = leverage_info.get('max', 'N/A')
                min_leverage = leverage_info.get('min', 'N/A')
                
                # Some exchanges store leverage differently
                if max_leverage == 'N/A':
                    # Try alternative locations for leverage info
                    max_leverage = market.get('leverage', market.get('maxLeverage', 'N/A'))
                
                usdt_futures.append({
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'type': market.get('type', 'N/A'),
                    'max_leverage': max_leverage,
                    'min_leverage': min_leverage,
                    'expiry': market.get('expiry', 'Perpetual'),
                    'contract_size': market.get('contractSize', 'N/A'),
                })
        
        return usdt_futures
        
    except Exception as e:
        print(f"Error fetching all markets: {e}")
        return []

# Alternative function to get leverage using individual symbol queries
def get_leverage_for_symbol(symbol):
    """Get leverage for a specific symbol"""
    try:
        # Try to get leverage from trading fees or market info
        market = exchange.market(symbol)
        
        # Check different possible locations for leverage
        leverage_info = market.get('limits', {}).get('leverage', {})
        max_leverage = leverage_info.get('max')
        
        if max_leverage is None:
            max_leverage = market.get('leverage', market.get('maxLeverage'))
            
        # If still not found, try to fetch from exchange-specific methods
        if max_leverage is None:
            try:
                # Some exchanges have specific methods to get leverage
                if hasattr(exchange, 'fetch_leverage'):
                    leverage_data = exchange.fetch_leverage(symbol)
                    max_leverage = leverage_data.get('max', 'N/A')
                else:
                    max_leverage = 'N/A'
            except:
                max_leverage = 'N/A'
                
        return max_leverage
    except Exception as e:
        return 'N/A'

# Enhanced function to get Binance-specific leverage info
def get_binance_leverage_info():
    """Get leverage info specifically for Binance futures"""
    try:
        # First try to get exchange info which often contains leverage data
        if hasattr(exchange, 'fetch_trading_fees'):
            try:
                fees = exchange.fetch_trading_fees()
                print("Fetched trading fees successfully")
            except:
                pass
        
        # Try to get position risk or leverage brackets
        leverage_data = {}
        
        # For Binance, we can check typical leverage values
        # Most Binance futures have standard leverage limits
        binance_standard_leverage = {
            'BTC': 125, 'ETH': 100, 'BNB': 75, 'XRP': 75, 'ADA': 75,
            'DOGE': 50, 'SOL': 50, 'MATIC': 50, 'DOT': 50, 'AVAX': 50,
            'LINK': 50, 'UNI': 50, 'LTC': 75, 'BCH': 75, 'ETC': 50
        }
        
        return binance_standard_leverage
    except Exception as e:
        print(f"Error getting Binance leverage info: {e}")
        return {}

# Enhanced version with better leverage detection
def get_all_usdt_futures_enhanced():
    """Enhanced version with better leverage detection for Binance"""
    try:
        markets = exchange.load_markets()
        binance_leverage = get_binance_leverage_info()
        
        usdt_futures = []
        for symbol, market in markets.items():
            # Include both future type and linear contracts with USDT quote
            if (market.get('quote') == 'USDT' and 
                market.get('active') and
                (market.get('type') == 'future' or market.get('linear') == True)):
                
                # Get leverage information with multiple fallbacks
                leverage_info = market.get('limits', {}).get('leverage', {})
                max_leverage = leverage_info.get('max', 'N/A')
                min_leverage = leverage_info.get('min', 'N/A')
                
                # Try alternative locations
                if max_leverage == 'N/A':
                    max_leverage = market.get('leverage', market.get('maxLeverage', 'N/A'))
                
                # Try Binance-specific lookup
                if max_leverage == 'N/A' and market['base'] in binance_leverage:
                    max_leverage = binance_leverage[market['base']]
                
                # Default leverage for most altcoins on Binance futures
                if max_leverage == 'N/A':
                    if market['base'] in ['BTC', 'ETH']:
                        max_leverage = 125 if market['base'] == 'BTC' else 100
                    elif market['base'] in ['BNB', 'XRP', 'ADA', 'LTC', 'BCH']:
                        max_leverage = 75
                    else:
                        max_leverage = 50  # Default for most altcoins
                
                usdt_futures.append({
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'type': market.get('type', 'N/A'),
                    'max_leverage': max_leverage,
                    'min_leverage': min_leverage,
                    'expiry': market.get('expiry', 'Perpetual'),
                    'contract_size': market.get('contractSize', 'N/A'),
                    'tier_info': market.get('info', {}).get('maintMarginPercent', 'N/A')
                })
        
        return usdt_futures
        
    except Exception as e:
        print(f"Error fetching enhanced markets: {e}")
        return []

print("\n" + "="*50)
print("=== GETTING ALL USDT FUTURES WITH ENHANCED LEVERAGE INFO ===")
all_usdt_pairs = get_all_usdt_futures_enhanced()

if all_usdt_pairs:
    print(f"\nFound {len(all_usdt_pairs)} USDT futures/linear pairs with leverage info:")
    print("-" * 100)
    
    # Create DataFrame for better display
    df = pd.DataFrame(all_usdt_pairs)
    print(df.to_string(index=False))
    
    # Separate perpetuals from quarterly
    perpetuals = [p for p in all_usdt_pairs if p['expiry'] == 'Perpetual' or p['expiry'] is None]
    quarterly = [p for p in all_usdt_pairs if p['expiry'] != 'Perpetual' and p['expiry'] is not None]
    
    print(f"\nPerpetual contracts: {len(perpetuals)}")
    print(f"Quarterly contracts: {len(quarterly)}")
    
    # Show leverage summary
    leverage_counts = {}
    for pair in all_usdt_pairs:
        leverage = pair['max_leverage']
        if leverage not in leverage_counts:
            leverage_counts[leverage] = 0
        leverage_counts[leverage] += 1
    
    print(f"\nLeverage distribution:")
    for leverage, count in sorted(leverage_counts.items()):
        print(f"  {leverage}x leverage: {count} pairs")
    
    print(f"\nAll USDT Perpetual contracts with leverage (first 100):")
    print("-" * 90)
    print(f"{'#':<4} {'Symbol':<30} {'Base':<12} {'Max Leverage':<15} {'Type':<8}")
    print("-" * 90)
    for i, pair in enumerate(perpetuals[:100], 1):
        leverage_info = f"{pair['max_leverage']}x" if pair['max_leverage'] != 'N/A' else 'N/A'
        symbol_clean = pair['symbol'].replace(':USDT', '')  # Clean display
        print(f"{i:<4} {symbol_clean:<30} {pair['base']:<12} {leverage_info:<15} {pair['type']:<8}")
    
    if len(perpetuals) > 100:
        print(f"\n... and {len(perpetuals) - 100} more perpetual contracts")
    
    # Show some high leverage coins
    high_leverage = [p for p in perpetuals if isinstance(p['max_leverage'], (int, float)) and p['max_leverage'] >= 75]
    if high_leverage:
        print(f"\nHigh leverage coins (75x+):")
        print("-" * 60)
        for pair in sorted(high_leverage, key=lambda x: x['max_leverage'], reverse=True)[:20]:
            leverage_info = f"{pair['max_leverage']}x"
            symbol_clean = pair['symbol'].replace(':USDT', '')
            print(f"  {symbol_clean:<25} | {leverage_info}")
    
    # Show quarterly contracts if any
    if quarterly:
        print(f"\nQuarterly contracts:")
        print("-" * 60)
        for pair in quarterly:
            leverage_info = f"{pair['max_leverage']}x" if pair['max_leverage'] != 'N/A' else 'N/A'
            symbol_clean = pair['symbol']
            print(f"  {symbol_clean:<35} | {leverage_info}")
        
else:
    print("No USDT futures found or error occurred.")

# %%
# Correct method to get USDT futures with leverage from Binance
def get_binance_usdt_futures_with_leverage():
    """Get USDT futures with proper leverage information from Binance"""
    try:
        print("Fetching markets...")
        
        # Fetch all markets (better than load_markets for current data)
        markets = exchange.fetch_markets()
        
        # Filter for USDT perpetual futures
        usdt_perpetuals = []
        for market in markets:
            if (market.get('quote') == 'USDT' and 
                market.get('active') == True and
                (market.get('type') == 'swap' or 
                 (market.get('type') == 'future' and market.get('expiry') is None))):
                usdt_perpetuals.append(market)
        
        print(f"Found {len(usdt_perpetuals)} USDT perpetual futures")
        
        # Get symbols for leverage lookup
        symbols = [market['symbol'] for market in usdt_perpetuals]
        
        # Try to fetch leverage tiers (this may require API key, but let's try)
        leverage_info = {}
        try:
            print("Attempting to fetch leverage tiers...")
            leverage_tiers = exchange.fetch_leverage_tiers(symbols)
            
            for symbol, tiers in leverage_tiers.items():
                if tiers:
                    max_leverage = max(tier.get('maxLeverage', 0) for tier in tiers)
                    leverage_info[symbol] = max_leverage
                    
        except Exception as e:
            print(f"Could not fetch leverage tiers (may need API key): {e}")
            print("Using standard Binance leverage values...")
            
            # Fallback to known Binance leverage limits
            standard_leverage = {
                'BTC': 125, 'ETH': 100, 'BNB': 75, 'XRP': 75, 'ADA': 75,
                'DOGE': 50, 'SOL': 50, 'MATIC': 50, 'DOT': 50, 'AVAX': 50,
                'LINK': 50, 'UNI': 50, 'LTC': 75, 'BCH': 75, 'ETC': 50,
                'ATOM': 50, 'FIL': 50, 'ICP': 50, 'NEAR': 50, 'ALGO': 50,
                'VET': 50, 'THETA': 50, 'TRX': 50, 'XLM': 50, 'AAVE': 50,
                'SUSHI': 50, 'COMP': 50, 'YFI': 50, 'SNX': 50, 'MKR': 50
            }
            
            print(f"Debug: Found {len(usdt_perpetuals)} USDT perpetuals")
            for market in usdt_perpetuals:
                base = market['base']
                symbol = market['symbol']
                if base in standard_leverage:
                    leverage_info[symbol] = standard_leverage[base]
                    print(f"Debug: Set {symbol} -> {standard_leverage[base]}x")
                else:
                    leverage_info[symbol] = 25  # Default for smaller coins
                    print(f"Debug: Set {symbol} -> 25x (default)")
            
            print(f"Debug: Total leverage_info entries: {len(leverage_info)}")
        
        # Compile results
        results = []
        print(f"Debug: Compiling results for {len(usdt_perpetuals)} markets")
        for market in usdt_perpetuals:
            symbol = market['symbol']
            leverage = leverage_info.get(symbol, 'Unknown')
            print(f"Debug: {symbol} -> leverage: {leverage}")
            
            results.append({
                'symbol': symbol,
                'base': market['base'],
                'quote': market['quote'],
                'max_leverage': leverage,
                'contract_type': market.get('contractType', 'N/A'),
                'contract_size': market.get('contractSize', 1.0)
            })
        
        return results
        
    except Exception as e:
        print(f"Error fetching futures: {e}")
        return []

# %%
print("="*70)
print("        BINANCE USDT PERPETUAL FUTURES WITH LEVERAGE")
print("="*70)

futures_data = get_binance_usdt_futures_with_leverage()

if futures_data:
    print(f"\nTotal USDT Perpetual Futures Found: {len(futures_data)}")
    
    # Sort by leverage (highest first), then by symbol
    futures_data.sort(key=lambda x: (-x['max_leverage'] if isinstance(x['max_leverage'], (int, float)) else 0, x['symbol']))
    
    # Group by leverage for summary
    leverage_summary = {}
    for future in futures_data:
        lev = future['max_leverage']
        if lev not in leverage_summary:
            leverage_summary[lev] = 0
        leverage_summary[lev] += 1
    
    print(f"\nLeverage Distribution:")
    print("-" * 30)
    for lev in sorted(leverage_summary.keys(), reverse=True):
        if isinstance(lev, (int, float)):
            print(f"{lev:>3}x leverage: {leverage_summary[lev]:>3} pairs")
        else:
            print(f"{str(lev):>10}: {leverage_summary[lev]:>3} pairs")
    
    # Show major cryptocurrencies first
    major_cryptos = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH']
    
    print(f"\nMAJOR CRYPTOCURRENCIES:")
    print("-" * 70)
    print(f"{'Symbol':<25} {'Base':<8} {'Max Leverage':<12} {'Contract Size'}")
    print("-" * 70)
    
    major_count = 0
    for future in futures_data:
        if future['base'] in major_cryptos:
            symbol_clean = future['symbol'].replace('/USDT:USDT', '')
            leverage_str = f"{future['max_leverage']}x" if isinstance(future['max_leverage'], (int, float)) else str(future['max_leverage'])
            print(f"{symbol_clean:<25} {future['base']:<8} {leverage_str:<12} {future['contract_size']}")
            major_count += 1
    
    print(f"\nALL USDT PERPETUAL FUTURES (First 100):")
    print("-" * 80)
    print(f"{'#':<4} {'Symbol':<25} {'Base':<8} {'Leverage':<12} {'Type'}")
    print("-" * 80)
    
    for i, future in enumerate(futures_data[:100], 1):
        symbol_clean = future['symbol'].replace('/USDT:USDT', '')
        leverage_str = f"{future['max_leverage']}x" if isinstance(future['max_leverage'], (int, float)) else str(future['max_leverage'])
        print(f"{i:<4} {symbol_clean:<25} {future['base']:<8} {leverage_str:<12} {future['contract_type']}")
    
    if len(futures_data) > 100:
        print(f"\n... and {len(futures_data) - 100} more futures contracts")
    
    # Show high leverage opportunities
    high_leverage = [f for f in futures_data if isinstance(f['max_leverage'], (int, float)) and f['max_leverage'] >= 75]
    if high_leverage:
        print(f"\nHIGH LEVERAGE OPPORTUNITIES (75x+):")
        print("-" * 50)
        for future in high_leverage[:20]:
            symbol_clean = future['symbol'].replace('/USDT:USDT', '')
            print(f"{symbol_clean:<20} {future['max_leverage']}x leverage")
    
    print(f"\n" + "="*70)
    print("Note: Leverage limits may vary based on position size and market conditions.")
    print("Always check current Binance terms before trading.")
    print("="*70)

else:
    print("Failed to retrieve futures data. Please check your connection.")
