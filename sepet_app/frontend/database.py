import os
import sqlite3
import pandas as pd

def load_data():
    """
    Loads the data from the latest sqlite database file into memory.
    Returns a dictionary of pandas DataFrames, with shop names as keys.
    """
    base_downloads_path = os.path.join('database')

    if not os.path.isdir(base_downloads_path):
        print(f"Error: Downloads directory not found at '{base_downloads_path}'")
        return {}

    db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.db')]

    if not db_files:
        print(f"Warning: No database files found in '{base_downloads_path}'. Returning empty data.")
        return {}

    # Sort by name to get the latest file, assuming YYYY-MM-DD format
    latest_db_file = sorted(db_files)[-1]
    
    print(f"Loading data from database: {latest_db_file}")
    
    data = {}
    try:
        # Connect to the database in read-only mode if possible, to prevent accidental writes.
        # URI syntax is needed for read-only mode.
        db_uri = f"file:{latest_db_file}?mode=ro"
        con = sqlite3.connect(db_uri, uri=True)
        
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            # Using f-string for table name is generally discouraged due to SQL injection,
            # but here table names are coming from the database schema itself, so it's safe.
            df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', con)
            data[table_name] = df
            print(f"  - Loaded table '{table_name}' with {len(df)} rows.")
            
        con.close()
        print(f"Data loaded successfully from '{latest_db_file}'.")
        return data

    except sqlite3.OperationalError as e:
        # This can happen if the file is not a database or if there's a problem opening it.
        print(f"ERROR: Failed to connect to database '{latest_db_file}'. Reason: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading data from the database. Reason: {e}")
        return {}