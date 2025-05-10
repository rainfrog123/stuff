#!/usr/bin/env python3
"""
Simple script to view the contents of the trades.db database.
"""

import sqlite3
import pandas as pd
import argparse
import sys
from datetime import datetime, timedelta
import os

# Default database path
TRADES_DB_PATH = "/allah/data/trades.db"

def connect_to_db(db_path):
    """Connect to the database and return the connection"""
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def get_table_info(conn):
    """Get information about the database tables"""
    cursor = conn.cursor()
    
    try:
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return
        
        print("Tables in the database:")
        for table in tables:
            table_name = table['name']
            print(f"\n=== Table: {table_name} ===")
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                print(f"  {col['name']} ({col['type']})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']
            print(f"Total rows: {count}")
    
    except sqlite3.Error as e:
        print(f"Error getting table info: {e}")

def get_trades(conn, symbol=None, limit=10, minutes=60, offset=0):
    """Get trades from the database with filtering options"""
    cursor = conn.cursor()
    
    query = "SELECT * FROM trades"
    params = []
    
    if symbol:
        query += " WHERE symbol = ?"
        params.append(symbol)
    
    if minutes > 0:
        # Calculate cutoff time
        cutoff_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
        
        if symbol:
            query += " AND timestamp >= ?"
        else:
            query += " WHERE timestamp >= ?"
        
        params.append(cutoff_time)
    
    query += " ORDER BY timestamp DESC"
    
    if limit > 0:
        query += f" LIMIT {limit}"
    
    if offset > 0:
        query += f" OFFSET {offset}"
    
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            print("No trades found with the specified criteria.")
            return None
        
        # Convert to pandas DataFrame for nice display
        trades_data = []
        for row in rows:
            trade = dict(row)
            trades_data.append(trade)
        
        return pd.DataFrame(trades_data)
    
    except sqlite3.Error as e:
        print(f"Error querying trades: {e}")
        return None

def display_trades(df):
    """Display trades in a readable format"""
    if df is None or df.empty:
        return
    
    # Convert timestamp to datetime for better readability
    df['datetime_local'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Select columns to display
    display_cols = ['id', 'symbol', 'datetime_local', 'price', 'amount', 'side']
    
    # Display trades
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    print("\n=== Latest Trades ===")
    print(df[display_cols])

def get_symbols(conn):
    """Get list of symbols in the database"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT symbol FROM trades ORDER BY symbol")
        symbols = cursor.fetchall()
        
        if not symbols:
            print("No symbols found in the database.")
            return []
        
        return [symbol['symbol'] for symbol in symbols]
    
    except sqlite3.Error as e:
        print(f"Error getting symbols: {e}")
        return []

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="View trades from the database")
    parser.add_argument("--db", default=TRADES_DB_PATH, help="Path to trades.db file")
    parser.add_argument("--info", action="store_true", help="Show database information")
    parser.add_argument("--symbol", help="Filter by symbol")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of trades (default: 10)")
    parser.add_argument("--minutes", type=int, default=60, help="Show trades from the last N minutes (default: 60)")
    parser.add_argument("--offset", type=int, default=0, help="Result offset for pagination")
    parser.add_argument("--list-symbols", action="store_true", help="List all symbols in the database")
    
    args = parser.parse_args()
    
    # Connect to database
    conn = connect_to_db(args.db)
    
    try:
        # Show database info if requested
        if args.info:
            get_table_info(conn)
        
        # List symbols if requested
        if args.list_symbols:
            symbols = get_symbols(conn)
            if symbols:
                print("\n=== Symbols in the database ===")
                for symbol in symbols:
                    print(f"  {symbol}")
        
        # Get and display trades
        if not args.info or not args.list_symbols:
            df = get_trades(conn, args.symbol, args.limit, args.minutes, args.offset)
            display_trades(df)
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 