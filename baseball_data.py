import pandas as pd
import requests
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine
import os
import streamlit as st # <-- IMPORT STREAMLIT

# --- NEW: Aiven/MySQL Connection Details from Streamlit Secrets ---
try:
    DB_HOST = st.secrets["DB_HOST"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    DB_PORT = st.secrets["DB_PORT"]
    DB_NAME = st.secrets["DB_NAME"]
except KeyError:
    st.error("Database secrets (DB_HOST, DB_USER, etc.) not found in Streamlit secrets.")
    st.stop()
except Exception:
    # This handles the case where the app is run locally without secrets
    # You could fall back to os.environ.get() here if you wanted
    print("Streamlit secrets not found. Are you running locally?")
    st.stop()


# --- Helper function to create a MySQL connection ---
def create_mysql_connection():
    """Creates and returns a MySQL connection object."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME
        )
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        st.error(f"Error connecting to MySQL database: {e}") # Show in app
    return conn

# --- NEW: Helper function to create a SQLAlchemy engine ---
def create_mysql_engine():
    """Creates and returns a SQLAlchemy engine for pandas."""
    try:
        connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"Error creating SQLAlchemy engine: {e}")
        st.error(f"Error creating SQLAlchemy engine: {e}") # Show in app
        return None

# --- The rest of your baseball_data.py file remains the same ---
# (list_tables_mysql, load_from_mysql, save_to_mysql, get_mlb_data)
# ... (rest of file) ...
# --- NEW: Generic function to list all tables ---
def list_tables_mysql():
    """Returns a list of all table names in the database."""
    conn = create_mysql_connection()
    if conn is None:
        return []
        
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        return tables
    except Error as e:
        print(f"Error listing tables: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- MODIFIED: Now generic, requires a table_name ---
def load_from_mysql(table_name):
    """Loads data from a specific table in the MySQL database."""
    conn = create_mysql_connection()
    if conn is None:
        print("Could not connect to database.")
        return pd.DataFrame()
        
    try:
        # Check if table exists
        all_tables = list_tables_mysql()
        if table_name not in all_tables:
            print(f"Table '{table_name}' does not exist. Returning empty DataFrame.")
            return pd.DataFrame()
            
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        return df
    except Exception as e:
        print(f"Error reading from MySQL table '{table_name}': {e}")
        return pd.DataFrame()
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- MODIFIED: Now generic, requires a df and table_name ---
def save_to_mysql(df, table_name):
    """Saves the DataFrame to a specific table, replacing existing data."""
    if df.empty:
        print(f"Dataframe is empty, nothing to save to '{table_name}'.")
        return
        
    engine = create_mysql_engine()
    if engine is None:
        print("Could not create connection engine. Data not saved.")
        return
        
    try:
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        print(f"Data saved to MySQL table '{table_name}' successfully.")
    except Exception as e:
        print(f"Error saving data to MySQL table '{table_name}': {e}")

# --- This function stays mostly the same, but calls the new generic functions ---
def get_mlb_data(api_key, force_refresh=False):
    """
    Fetches MLB player data, either from cache (MySQL) or by calling the API.
    This function specifically manages the 'mlb_players' table.
    """
    player_table = "mlb_players" # Define the specific table for this function
    
    if not force_refresh:
        # MODIFIED: Call generic load function with specific table
        df = load_from_mysql(player_table)
        if not df.empty:
            print(f"Loaded data from MySQL cache ('{player_table}').")
            return df
    
    print("Fetching new data from API...")
    # The original API fetching logic
    base_url = "https://api.ballstatz.com/v1/mlb/stats"
    teams_url = "https://api.ballstatz.com/v1/mlb/teams"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        teams_response = requests.get(teams_url, headers=headers)
        teams_response.raise_for_status()
        teams = teams_response.json().get('data', [])
        
        all_players_data = []
        
        for team in teams:
            team_id = team.get('id')
            team_name = team.get('name')
            if not team_id:
                continue
            
            # Fetch hitting stats
            hitting_params = {'teamId': team_id, 'group': 'hitting'}
            hitting_response = requests.get(base_url, headers=headers, params=hitting_params)
            if hitting_response.status_code == 200:
                hitting_data = hitting_response.json().get('data', [])
                for player in hitting_data:
                    player['team'] = team_name
                    player['group_type'] = 'hitting'
                all_players_data.extend(hitting_data)
            
            # Fetch pitching stats
            pitching_params = {'teamId': team_id, 'group': 'pitching'}
            pitching_response = requests.get(base_url, headers=headers, params=pitching_params)
            if pitching_response.status_code == 200:
                pitching_data = pitching_response.json().get('data', [])
                for player in pitching_data:
                    player['team'] = team_name
                    player['group_type'] = 'pitching'
                all_players_data.extend(pitching_data)
        
        if not all_players_data:
            print("No data fetched from API.")
            return pd.DataFrame()
            
        df = pd.DataFrame(all_players_data)
        
        # Data cleaning
        df.drop_duplicates(subset=['name', 'team', 'group_type'], inplace=True)
        numeric_cols = ['avg', 'era', 'hits', 'homeRuns', 'rbi', 'strikeOuts', 'wins', 'losses', 'games', 'inningsPitched']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.fillna(0, inplace=True)
        
        # MODIFIED: Call generic save function with specific table
        save_to_mysql(df, player_table)
        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return pd.DataFrame()