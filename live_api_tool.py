# live_api_tool.py
import mlb_statsapi
import datetime
import streamlit as st

@st.cache_data(ttl=3600) # Cache this for 1 hour
def get_yesterdays_scores():
    """
    Fetches all game scores from yesterday and returns 
    a simplified, easy-to-read summary string.
    """
    try:
        # Get yesterday's date in YYYY-MM-DD format
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Call the API
        schedule = mlb_statsapi.get('schedule', {'sportId': 1, 'date': yesterday})
        
        if not schedule['dates']:
            return "No games were played yesterday."
            
        games = schedule['dates'][0]['games']
        game_summaries = []
        
        # Process the complex JSON into simple strings
        for game in games:
            home_team = game['teams']['home']['team']['name']
            home_score = game['teams']['home']['score']
            away_team = game['teams']['away']['team']['name']
            away_score = game['teams']['away']['score']
            
            # Determine winner
            if game['status']['detailedState'] != 'Final':
                continue # Skip games that weren't completed
            
            winner = home_team if home_score > away_score else away_team
            
            summary = (
                f"Game: {away_team} ({away_score}) at {home_team} ({home_score}). "
                f"Winner: {winner}."
            )
            game_summaries.append(summary)

        if not game_summaries:
            return "No completed games were found for yesterday."

        # Join all summaries into one big block of text
        return "\n".join(game_summaries)

    except Exception as e:
        return f"Error calling MLB-StatsAPI: {e}"

# --- You can add more functions here later ---
# (e.g., get_player_stats, get_team_standings)