# live_api_tool.py
import statsapi  # <-- Correct import
import datetime
import streamlit as st
import pandas as pd

# --- Tool 1: Get Scores (No changes needed here) ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_yesterdays_scores():
    """Fetches all game scores from yesterday."""
    try:
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        games = statsapi.schedule(date=yesterday)
        
        if not games:
            return "No games were played yesterday."
        
        game_summaries = []
        for game in games:
            if game['status'] != 'Final':
                continue
            
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
        return "\n".join(game_summaries)
    except Exception as e:
        return f"Error getting scores: {e}"

# --- Tool 2: Get Player Info & Stats (IMPROVED) ---
def get_player_info(player_name):
    """
    Finds a player, gets their bio, and gets their current season stats.
    Returns a single string of context.
    """
    try:
        # --- 1. Find the player ID (Same as before) ---
        search_results = statsapi.lookup_player(player_name)
        
        if not search_results:
            return f"Error: Could not find any player named '{player_name}'."
        
        player_lookup = search_results[0]
        player_id = player_lookup['id']
        full_name = player_lookup['fullName']
        
        # --- 2. Get Bio & Stats (NEW, more robust method) ---
        current_year = datetime.date.today().year # This will be 2025
        
        # This is a more direct and reliable way to get stats for a *specific* season
        data = statsapi.get('people', {
            'personIds': player_id,
            'season': current_year,
            'hydrate': f'stats(group=[hitting,pitching,fielding],type=season,season={current_year})'
        })

        if not data or 'people' not in data or not data['people']:
             return f"Error: Could not get data for player ID {player_id}."

        player_data = data['people'][0]

        # --- 3. Format Bio ---
        bio_summary = (
            f"Player: {player_data.get('fullName', 'N/A')}\n"
            f"Born: {player_data.get('birthDate', 'N/A')}\n"
            f"Team: {player_data.get('currentTeam', {}).get('name', 'N/A')}\n"
            f"Position: {player_data.get('primaryPosition', {}).get('name', 'N/A')}\n"
            f"Bio: Bats {player_data.get('batSide', {}).get('code', 'N/A')}, "
            f"Throws {player_data.get('pitchHand', {}).get('code', 'N/A')}\n"
        )
        
        # --- 4. Format Stats ---
        stats_summary = f"\nNo stats found for {current_year}."
        
        if 'stats' in player_data and player_data['stats']:
            # Find the "season" stats
            for stat_group in player_data['stats']:
                if stat_group['group']['displayName'] == 'hitting' and stat_group['type']['displayName'] == 'season':
                    if 'splits' in stat_group and stat_group['splits']:
                        
                        hitting_stats = stat_group['splits'][0]['stat']
                        
                        # THIS IS KEY: We get the season from the data itself
                        season_label = stat_group['splits'][0].get('season', current_year)
                        
                        df = pd.DataFrame([hitting_stats])
                        stats_summary = f"\n{season_label} Hitting Stats:\n{df.to_string()}\n"
                        break # Found it, exit loop
        
        # --- 5. Combine and return all context ---
        return bio_summary + stats_summary
        
    except Exception as e:
        return f"Error getting player info: {e}"