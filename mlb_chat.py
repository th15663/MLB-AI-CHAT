import google.generativeai as genai
import os
import json
import pandas as pd
import streamlit as st # Keep streamlit import for accessing secrets

# --- Remove API Key configuration from the top level ---
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") # Don't get it here
# if not GEMINI_API_KEY:
#     try:
#         GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] # Don't get it here
#     except Exception:
#         st.error("Missing Gemini API Key!") # Error handling should be later
#         GEMINI_API_KEY = None
#
# if GEMINI_API_KEY:
#     genai.configure(api_key=GEMINI_API_KEY) # Don't configure here
#     model = genai.GenerativeModel("gemini-pro") # Don't initialize model here
# else:
#     model = None

# --- Interpret & Answer Queries ---
def chat_with_gemini(user_input, mlb_data):
    """Main chat logic using Gemini and merged MLB data."""

    # --- Configure Gemini *inside* the function ---
    model = None # Initialize model as None
    try:
        # Prioritize Streamlit secrets if available
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        else:
            # Fallback to environment variable
            api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            st.error("Missing Gemini API Key in Streamlit secrets or environment variables!")
            return "⚠️ Error: Gemini API Key not configured."
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-pro") # Or your preferred model
    except Exception as e:
        st.error(f"Error configuring Gemini: {e}")
        return f"⚠️ Error: Could not configure Gemini model. {e}"
    # --- End Gemini Configuration ---

    if model is None: # Double check model was initialized
        return "⚠️ Error: Gemini model not available after configuration attempt."
    if mlb_data is None or mlb_data.empty:
         return "⚠️ Error: MLB data not loaded."

    try:
        # Try to find a player name in the user input using the 'name' column
        player_matches = [
            name for name in mlb_data["name"].dropna().unique()
            if isinstance(name, str) and name.lower() in user_input.lower()
        ]

        if player_matches:
            player_name = player_matches[0]
            # Get all rows for the player (they might have multiple stints/years)
            player_rows = mlb_data[mlb_data["name"] == player_name].copy()
            if player_rows.empty:
                return f"Sorry, I couldn’t find any detailed stats for {player_name} in the loaded data."

            stats_list = []
            for _, row in player_rows.iterrows():
                 row_dict = row.dropna().to_dict()
                 stats_list.append({k.replace('_bat','').replace('_pitch',''): v for k, v in row_dict.items()})


            prompt = f"""
            You are a baseball expert assistant.
            The user asked: "{user_input}"

            Here are stats for {player_name} from the database (could be multiple seasons/teams):
            {json.dumps(stats_list, indent=2, default=str)}

            Use this info to answer clearly and conversationally. Summarize if multiple rows exist unless asked for specifics. Focus on relevant stats (batting or pitching based on the question).
            """
            response = model.generate_content(prompt)
            # Add basic check for response content
            if response and response.parts:
                 return response.text.strip()
            else:
                 # Handle cases where the model might return an empty response or safety block
                 print(f"Gemini response issue. Prompt: {prompt}, Response: {response}")
                 return "Sorry, I couldn't generate a response for that player."


        # No specific player — handle league-wide questions
        cols_to_sample = ['name', 'yearID', 'teamID', 'lgID', 'G_bat', 'AB', 'H_bat', 'HR_bat', 'RBI', 'SB', 'CS', 'BB_bat', 'SO_bat',
                          'W', 'L', 'ERA', 'G_pitch', 'SV', 'IPOuts', 'H_pitch', 'ER', 'HR_pitch', 'BB_pitch', 'SO_pitch']
        existing_cols = [col for col in cols_to_sample if col in mlb_data.columns]
        subset = mlb_data[existing_cols].dropna(how="all")

        if subset.empty:
            return "Could not find relevant league-wide data to sample."

        sample_size = min(50, len(subset))
        sample = subset.sample(n=sample_size, random_state=42)
        data_json = sample.to_dict(orient="records")

        prompt = f"""
        You are a professional baseball analytics assistant.
        The user asked: "{user_input}"

        Here’s a sample of MLB player data from the database (stats from various years):
        {json.dumps(data_json, indent=2, default=str)}

        Answer based ONLY on this provided sample data. Identify leaders, top players, or trends if asked within the sample.
        Be specific but concise. State that the answer is based on a sample.
        """
        response = model.generate_content(prompt)
        # Add basic check for response content
        if response and response.parts:
            return response.text.strip()
        else:
            print(f"Gemini response issue. Prompt: {prompt}, Response: {response}")
            return "Sorry, I couldn't generate a response for that league question."


    except Exception as e:
        print(f"Error during Gemini generation: {e}") # Print error for debugging
        st.error(f"⚠️ Error interpreting query: {e}") # Show error in Streamlit
        return f"⚠️ Error interpreting query: {e}"