import streamlit as st
import pandas as pd
from baseball_data import get_mlb_data, list_tables_mysql, load_from_mysql
from mlb_chat import get_gemini_response

# --- Page Configuration ---
st.set_page_config(page_title="MLB Player Stats", layout="wide")
st.title("⚾ MLB Player Stats Dashboard")

# --- Get API Key ---
api_key = st.secrets.get("BALLSTATZ_API_KEY")
if not api_key:
    st.error("BALLSTATZ_API_KEY not found in Streamlit secrets.")
    st.stop()

# --- NEW: Sidebar for Table Management ---
st.sidebar.title("Database Management")

# Button to refresh API data
if st.sidebar.button("Force Refresh Player Data from API"):
    with st.spinner("Fetching new data from Ballstatz API..."):
        get_mlb_data(api_key, force_refresh=True)
    st.sidebar.success("Player data has been refreshed!")

# NEW: Show all tables in the database
st.sidebar.header("Database Tables")
with st.spinner("Loading database tables..."):
    all_tables = list_tables_mysql()

if not all_tables:
    st.sidebar.error("Could not connect to or read tables from the database.")
    st.stop()

st.sidebar.write("Found the following tables:")
st.sidebar.dataframe(all_tables, use_container_width=True)

# NEW: Dropdown to select which table to view
st.sidebar.header("View Table Data")
selected_table = st.sidebar.selectbox(
    "Select a table to display:",
    options=all_tables,
    # Set default to mlb_players if it exists, otherwise first table
    index=all_tables.index("mlb_players") if "mlb_players" in all_tables else 0
)

# --- Main Page Content ---

# Load the data from the user-selected table
with st.spinner(f"Loading data from table '{selected_table}'..."):
    df = load_from_mysql(selected_table)

if df.empty:
    st.warning(f"No data found in table '{selected_table}' or table does not exist.")
    st.stop()

st.header(f"Displaying Data for: {selected_table}")
st.dataframe(df, use_container_width=True)

# --- Original Chatbot and Filtering Logic ---
# (This logic is tied to the 'mlb_players' table structure)

if selected_table == "mlb_players":
    st.header("Analyze Player Data")
    
    # Filtering (from your original file)
    teams = sorted(df['team'].unique())
    selected_team = st.selectbox("Filter by Team", ["All"] + teams)
    
    if selected_team != "All":
        df_filtered = df[df['team'] == selected_team]
    else:
        df_filtered = df
        
    # Group type selection
    group_type = st.radio("Select Stats Type", ["hitting", "pitching"], index=0)
    
    if group_type == "hitting":
        stats_cols = ['name', 'team', 'avg', 'homeRuns', 'rbi', 'hits', 'games']
        df_display = df_filtered[df_filtered['group_type'] == 'hitting'][stats_cols]
        st.subheader(f"{selected_team} Hitting Stats")
    else:
        stats_cols = ['name', 'team', 'era', 'wins', 'losses', 'strikeOuts', 'inningsPitched', 'games']
        df_display = df_filtered[df_filtered['group_type'] == 'pitching'][stats_cols]
        st.subheader(f"{selected_team} Pitching Stats")
        
    st.dataframe(df_display, use_container_width=True)

    # Gemini Chatbot (from your original file)
    st.header("Chat with Your Data")
    user_query = st.text_input("Ask a question about the player data:")
    
    if st.button("Get Answer"):
        if user_query:
            with st.spinner("Gemini is thinking..."):
                # Convert the relevant dataframe to CSV string for context
                csv_data = df_display.to_csv(index=False)
                prompt = f"""
                You are an expert MLB data analyst. Based on the following data in CSV format,
                answer the user's question.

                Data:
                {csv_data}

                Question:
                {user_query}
                """
                response = get_gemini_response(prompt)
                st.markdown(response)
        else:
            st.warning("Please enter a question.")
else:
    st.info(f"Analysis and Chat features are configured for the 'mlb_players' table. You are currently viewing '{selected_table}'.")