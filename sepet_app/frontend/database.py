import os
import pickle

def load_pickled_data():
    """
    Loads the pickled data file into memory.
    """
    base_downloads_path = os.path.join('sepet_app', 'frontend', 'database')
    pickled_db_file = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.pkl')]

    if len(pickled_db_file) >= 1:
        pickled_db_file = sorted(pickled_db_file)[-1]
    else:
        print(f"Warning: Pickle file not found at '{pickled_db_file}'. Returning empty data.")
        return {}

    print("Loading pickled data from disk...")
    try:
        with open(pickled_db_file, 'rb') as f:
            data = pickle.load(f)
        print(f"Pickled data loaded successfully from '{pickled_db_file}'.")
        return data
    except Exception as e:
        print(f"ERROR: Failed to load pickle file. Reason: {e}")
        return {}
