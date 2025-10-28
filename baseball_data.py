# baseball_data.py
# Removed sqlite3 import
import streamlit as st # Need streamlit for secrets
import mysql.connector # Added MySQL connector
import pandas as pd
import time
import json
import re
import os
import google.generativeai as genai # Keep genai if chat_with_gemini uses it directly

# -------------------------------
# ⚙️ Setup
# -------------------------------
# Removed DB_PATH
MLB_SEASON = 2025 # Keep if needed elsewhere
# Removed GEMINI_API_KEY and model setup (should be in mlb_chat.py)

# -------------------------------
# 🔗 MySQL Connection
# -------------------------------
def get_mysql_connection():
    """Establishes a connection to the MySQL database using secrets."""
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            database=st.secrets["mysql"]["database"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"]
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error connecting to MySQL: {err}") # Use st.error for Streamlit display
        print(f"Error connecting to MySQL: {err}") # Also print for command-line
        return None
    except Exception as e: # Catch if secrets aren't configured yet
        st.error(f"Could not connect to MySQL. Ensure secrets are configured. Error: {e}")
        print(f"Could not connect to MySQL. Ensure secrets are configured. Error: {e}")
        return None

# -------------------------------
# 💾 Load Data from MySQL
# -------------------------------
# @st.cache_data # Optional: Cache for performance in Streamlit
def load_from_mysql():
    """Load and merge People, Batting, Pitching data from MySQL."""
    conn = get_mysql_connection()
    if conn is None:
        return None # Return None if connection failed

    print("📂 Loading data from MySQL...")
    try:
        # Load People table (only necessary columns)
        people_df = pd.read_sql("SELECT playerID, nameFirst, nameLast FROM People", conn)
        print(f"  - Loaded {len(people_df)} records from People.")
        # Create a 'name' column for easier matching with old code
        people_df['name'] = people_df['nameFirst'] + ' ' + people_df['nameLast']

        # Load Batting table
        # Rename ambiguous columns like G, H, R, HR before merge
        batting_df = pd.read_sql("SELECT * FROM Batting", conn).rename(columns={
            'G': 'G_bat', 'H': 'H_bat', 'R': 'R_bat', 'HR': 'HR_bat', 'SO': 'SO_bat',
            'BB': 'BB_bat', 'IBB': 'IBB_bat', 'HBP': 'HBP_bat', 'SH': 'SH_bat',
            'SF': 'SF_bat', 'GIDP': 'GIDP_bat'
        })
        print(f"  - Loaded {len(batting_df)} records from Batting.")

        # Load Pitching table
        # Rename ambiguous columns
        pitching_df = pd.read_sql("SELECT * FROM Pitching", conn).rename(columns={
            'G': 'G_pitch', 'H': 'H_pitch', 'R': 'R_pitch', 'HR': 'HR_pitch', 'SO': 'SO_pitch',
            'BB': 'BB_pitch', 'IBB': 'IBB_pitch', 'HBP': 'HBP_pitch', 'SH': 'SH_pitch',
            'SF': 'SF_pitch', 'GIDP': 'GIDP_pitch'
        })
        print(f"  - Loaded {len(pitching_df)} records from Pitching.")

        # --- Merge DataFrames ---
        # 1. Merge Batting with People
        merged_df = pd.merge(batting_df, people_df[['playerID', 'name']], on='playerID', how='left')

        # 2. Merge Pitching onto the result
        # Use outer join to keep players who only batted or only pitched in a year/stint
        # Use common keys: playerID, yearID, stint
        merged_df = pd.merge(merged_df, pitching_df, on=['playerID', 'yearID', 'stint'], how='outer', suffixes=('_bat', '_pitch'))

        # Add teamID and lgID back if they were dropped due to suffixes (take from _bat or _pitch)
        merged_df['teamID'] = merged_df['teamID_bat'].fillna(merged_df['teamID_pitch'])
        merged_df['lgID'] = merged_df['lgID_bat'].fillna(merged_df['lgID_pitch'])
        # Add player name again if missing due to outer join
        merged_df['name'] = merged_df['name'].fillna(merged_df['playerID'].map(people_df.set_index('playerID')['name']))


        print(f"📊 Merged data has {len(merged_df)} rows.")
        return merged_df # Return the single, merged DataFrame

    except pd.io.sql.DatabaseError as err:
        # st.error(f"Error reading data from MySQL: {err}") # Use if running in Streamlit
        print(f"Error reading data from MySQL: {err}")
        return None
    except Exception as e:
        # st.error(f"An unexpected error occurred during data loading: {e}") # Use if running in Streamlit
        print(f"An unexpected error occurred during data loading: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("  - MySQL connection closed.")


# -------------------------------
# 🧠 Interpret & Answer Queries (Keep chat function)
# -------------------------------
# Make sure GEMINI_API_KEY setup is handled (ideally in mlb_chat.py or main app)
# If not, add it back here:
if "GEMINI_API_KEY" not in os.environ:
     print("Warning: GEMINI_API_KEY environment variable not set.")
     # Fallback or error handling needed if key isn't set via secrets or env var
     # For local testing only, you could uncomment:
     # genai.configure(api_key="YOUR_KEY_HERE_BUT_DO_NOT_COMMIT")
else:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Ensure the model is configured if needed here
try:
    model = genai.GenerativeModel("gemini-pro") # Or your preferred model
except Exception as e:
    print(f"Error configuring Gemini model: {e}")
    model = None



# -------------------------------
# 💬 Chat Loop (for command-line testing)
# -------------------------------
if __name__ == "__main__":
    print("⚾ MLB AI Baseball Chatbot (MySQL Version)")
    print("🔹 Type your question (e.g. 'How many home runs did Shohei Ohtani have?')")
    print("🔹 Type 'quit' to exit.\n")

    # Load data directly from MySQL when script runs
    mlb_data = load_from_mysql()

    if mlb_data is None:
        print("❌ Failed to load data from MySQL. Exiting.")
    else:
        print(f"✅ Data loaded successfully ({len(mlb_data)} rows). Ready for questions.")
        # Chat loop
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit"]:
                print("👋 Goodbye!")
                break
            if not user_input:
                continue

            ai_reply = chat_with_gemini(user_input, mlb_data)
            print(f"\nAI: {ai_reply}\n")
            time.sleep(1)