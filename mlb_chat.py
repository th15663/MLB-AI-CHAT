import google.generativeai as genai
import json
import pandas as pd
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
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
