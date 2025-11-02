import streamlit as st
import mysql.connector
import pandas as pd

# Removed DB_PATH, it's not needed for MySQL
MLB_SEASON = 2025 # Keep if needed elsewhere

#
# MySQL Connection
#
def get_mysql_connection():
    """Establishes a connection to the MySQL database using secrets."""
    
    # Define the path to your CA certificate
    # This assumes ca.pem is in the same directory as your script
    ssl_ca_path = "ca.pem" 
    
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            database=st.secrets["mysql"]["database"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            
            # --- Add these SSL arguments ---
            ssl_verify_cert=True,
            ssl_ca=ssl_ca_path
            # --------------------------------
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error connecting to MySQL: {err}") 
        print(f"Error connecting to MySQL: {err}") 
        return None
    except Exception as e: 
        st.error(f"Could not connect to MySQL. Ensure secrets are configured. Error: {e}")
        print(f"Could not connect to MySQL. Ensure secrets are configured. Error: {e}")
        return None

#
# Load Data From MySQL
#
@st.cache_data(ttl=3600)
def load_from_mysql():
    """Load and merge People, Batting, Pitching data from MySQL."""
    conn = get_mysql_connection()
    if conn is None:
        return None # Return None if connection failed

    print("📂 Loading data from MySQL...")
    try:
        # Load People table (only necessary columns)
        # --- FIX 1: 'People' changed to 'people' ---
        people_df = pd.read_sql("SELECT playerID, nameFirst, nameLast FROM people", conn)
        print(f"  - Loaded {len(people_df)} records from people.")
        # Create a 'name' column for easier matching with old code
        people_df['name'] = people_df['nameFirst'] + ' ' + people_df['nameLast']

        # Load Batting table
        # Rename ambiguous columns like G, H, R, HR before merge
        # --- FIX 2: 'Batting' changed to 'batting' ---
        batting_df = pd.read_sql("SELECT * FROM batting", conn).rename(columns={
            'G': 'G_bat', 'H': 'H_bat', 'R': 'R_bat', 'HR': 'HR_bat', 'SO': 'SO_bat',
            'BB': 'BB_bat', 'IBB': 'IBB_bat', 'HBP': 'HBP_bat', 'SH': 'SH_bat',
            'SF': 'SF_bat', 'GIDP': 'GIDP_bat'
        })
        print(f"  - Loaded {len(batting_df)} records from batting.")

        # Load Pitching table
        # Rename ambiguous columns
        # --- FIX 3: 'Pitching' changed to 'pitching' ---
        pitching_df = pd.read_sql("SELECT * FROM pitching", conn).rename(columns={
            'G': 'G_pitch', 'H': 'H_pitch', 'R': 'R_pitch', 'HR': 'HR_pitch', 'SO': 'SO_pitch',
            'BB': 'BB_pitch', 'IBB': 'IBB_pitch', 'HBP': 'HBP_pitch', 'SH': 'SH_pitch',
            'SF': 'SF_pitch', 'GIDP': 'GIDP_pitch'
        })
        print(f"  - Loaded {len(pitching_df)} records from pitching.")

        # Close the connection
        conn.close()

        # Merge dataframes: (People + Batting) + Pitching
        # Merge People with Batting
        merged_df = pd.merge(people_df, batting_df, on='playerID', how='outer')
        
        # Merge the result with Pitching
        # We need to handle playerID/yearID/stint duplicates. 
        # A simple outer merge is fine if we aggregate stats later.
        final_df = pd.merge(merged_df, pitching_df, on=['playerID', 'yearID', 'stint', 'teamID', 'lgID'], how='outer')

        # Drop the now-redundant nameFirst, nameLast
        final_df.drop(columns=['nameFirst', 'nameLast'], inplace=True)
        
        print(f"✅ Data loaded and merged successfully. Total records: {len(final_df)}")
        return final_df

    except Exception as e:
        st.error(f"Failed to load data from MySQL. Check tables and schema. Error: {e}")
        print(f"Failed to load data from MySQL. Check tables and schema. Error: {e}")
        if conn:
            conn.close()
        return None