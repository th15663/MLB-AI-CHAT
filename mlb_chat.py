import google.generativeai as genai
import json
import pandas as pd
import os

GEMINI_API_KEY = "AIzaSyBscRNAqx-pGu_93wKDWomk9GG-hdxGIM8"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro-latest")

def chat_with_gemini(user_input, mlb_data):
    try:
        player_matches = [
            name for name in mlb_data["name"].unique()
            if name.lower() in user_input.lower()
        ]

        if player_matches:
            player_name = player_matches[0]
            player_row = mlb_data[mlb_data["name"] == player_name]
            if player_row.empty:
                return f"Sorry, I couldn’t find any stats for {player_name}."
            stats_dict = player_row.iloc[0].dropna().to_dict()
            prompt = f"""
            You are a baseball expert assistant.
            The user asked: "{user_input}"
            Here are {player_name}'s 2025 MLB stats:
            {json.dumps(stats_dict, indent=2)}
            Answer conversationally and clearly.
            """
            return model.generate_content(prompt).text.strip()

        subset = mlb_data[["name", "team", "era", "avg", "wins", "strikeOuts", "homeRuns", "rbi"]].dropna(how="all")
        sample = subset.sample(min(800, len(subset)), random_state=42)
        data_json = sample.to_dict(orient="records")

        prompt = f"""
        You are a professional baseball analytics assistant.
        The user asked: "{user_input}"
        Here’s MLB 2025 player data (sampled from {len(subset)} players):
        {json.dumps(data_json[:200], indent=2)}
        Answer based on this data clearly and concisely.
        """
        return model.generate_content(prompt).text.strip()

    except Exception as e:
        return f"⚠️ Error interpreting query: {e}"
    

def chat_with_gemini(user_input, mlb_data):
    """Main chat logic using Gemini and merged MLB data."""
    if model is None:
        return "⚠️ Error: Gemini model not configured."
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

            # Select relevant columns and handle potential missing data (NaN)
            # Create a summary dictionary - this needs refinement based on expected stats
            stats_list = []
            for _, row in player_rows.iterrows():
                 # Example: create a dict per year/stint
                 row_dict = row.dropna().to_dict()
                 # Clean up potential suffix issues if needed, e.g. teamID_bat -> teamID
                 stats_list.append({k.replace('_bat','').replace('_pitch',''): v for k, v in row_dict.items()})


            prompt = f"""
            You are a baseball expert assistant.
            The user asked: "{user_input}"

            Here are stats for {player_name} from the database (could be multiple seasons/teams):
            {json.dumps(stats_list, indent=2, default=str)}

            Use this info to answer clearly and conversationally. Summarize if multiple rows exist unless asked for specifics. Focus on relevant stats (batting or pitching based on the question).
            """
            response = model.generate_content(prompt)
            return response.text.strip()

        # No specific player — handle league-wide questions
        # Select a broader range of potentially relevant columns
        cols_to_sample = ['name', 'yearID', 'teamID', 'lgID', 'G_bat', 'AB', 'H_bat', 'HR_bat', 'RBI', 'SB', 'CS', 'BB_bat', 'SO_bat',
                          'W', 'L', 'ERA', 'G_pitch', 'SV', 'IPOuts', 'H_pitch', 'ER', 'HR_pitch', 'BB_pitch', 'SO_pitch']
        # Filter columns that actually exist in the merged dataframe
        existing_cols = [col for col in cols_to_sample if col in mlb_data.columns]
        subset = mlb_data[existing_cols].dropna(how="all")

        if subset.empty:
            return "Could not find relevant league-wide data to sample."

        # Sample data, ensure sample size isn't larger than available data
        sample_size = min(50, len(subset)) # Reduced sample size for prompt
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
        return response.text.strip()

    except Exception as e:
        print(f"Error during Gemini generation: {e}") # Print error for debugging
        # st.error(f"⚠️ Error interpreting query: {e}") # Use if running in Streamlit
        return f"⚠️ Error interpreting query: {e}"

