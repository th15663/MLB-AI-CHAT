# live_api_tool.py
import statsapi  # <-- THIS IS THE CORRECT IMPORT (not 'mlb_statsapi')
import datetime
import streamlit as st
import pandas as pd

# --- Tool 1: Get Scores ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_yesterdays_scores():
    """Fetches all game scores from yesterday."""
    try:
        # Get yesterday's date in YYYY-MM-DD format
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Use the high-level 'schedule' function
        games = statsapi.schedule(date=yesterday)
        
        if not games:
            return "No games were played yesterday."
            
        game_summaries = []
        
        # Process the game data
        for game in games:
            if game['status'] != 'Final':
                continue  # Skip games that weren't completed
            
            home_team = game['home_name']
            home_score = game['home_score']
            away_team = game['away_name']
            away_score = game['away_score']
            winner = home_team if home_score > away_score else away_team
            
            summary = (
                f"Game: {away_team} ({away_score}) at {home_team} ({home_score}). "
                f"Winner: {winner}."
            )
            game_summaries.append(summary)

        if not game_summaries:
            return "No completed games were found for yesterday."
        return "\n".join(game_summarIES)
    except Exception as e:
        return f"Error getting scores: {e}"

# --- Tool 2: Get Player Info & Stats ---
def get_player_info(player_name):
    """
    Finds a player, gets their bio, and gets their current season stats.
    Returns a single string of context.
    """
    try:
        # --- 1. Find the player ID ---
        # Use the 'lookup_player' function
        search_results = statsapi.lookup_player(player_name)
        
        if not search_results:
            return f"Error: Could not find any player named '{player_name}'."
        
        # Grab the first and most relevant match
        player = search_results[0]
        player_id = player['id']
        full_name = player['fullName']
        
        # --- 2. Get Player Bio & Stats ---
        # 'player_stat_data' is a great function that gets bio AND stats
        current_year = datetime.date.today().year
        data = statsapi.player_stat_data(player_id, group="hitting", type="season", season=current_year)
        
        # --- 3. Format the data into clean text context ---
        bio_summary = (
            f"Player: {full_name}\n"
            f"Born: {player.get('birthDate', 'N/A')}\n"
            f"Team: {player.get('currentTeam', {}).get('name', 'N/A')}\n"
            f"Position: {player.get('primaryPosition', {}).get('name', 'N/A')}\n"
            f"Bio: Bats {player.get('bats', {}).get('code', 'N/A')}, "
            f"Throws {player.get('throws', {}).get('code', 'N/A')}\n"
        )
        
        stats_summary = f"\nNo {current_year} hitting stats found."
        if data and 'stats' in data and data['stats']:
            hitting_stats = data['stats'][0]['stats']
            # Convert stats to a readable DataFrame, then to a string
            df = pd.DataFrame([hitting_stats])
            stats_summary = f"\n{current_year} Hitting Stats:\n{df.to_string()}\n"

        # (You could add a check for pitching stats here too)
        
        # --- 4. Combine and return all context ---
        return bio_summary + stats_summary
        
    except Exception as e:
        return f"Error getting player info: {e}"