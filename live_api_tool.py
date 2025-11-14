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

# --- Tool 2: Get Player Info & Stats (LEVEL 3 - Smart Fallback) ---
def get_player_info(player_name):
    """
    Finds a player, gets their bio, and gets their most recent
    completed season stats (handles off-season).
    """
    try:
        # --- 1. Find the player ID ---
        search_results = statsapi.lookup_player(player_name)
        
        if not search_results:
            return f"Error: Could not find any player named '{player_name}'."
        
        player_lookup = search_results[0]
        player_id = player_lookup['id']
        
        # --- 2. Get Bio ---
        # We'll get the bio first, as it's more reliable
        bio_data = statsapi.get('person', {'personId': player_id})
        person = bio_data['people'][0]

        bio_summary = (
            f"Player: {person.get('fullName', 'N/A')}\n"
            f"Born: {person.get('birthDate', 'N/A')}\n"
            f"Team: {person.get('currentTeam', {}).get('name', 'N/A')}\n"
            f"Position: {person.get('primaryPosition', {}).get('name', 'N/A')}\n"
            f"Bio: Bats {person.get('batSide', {}).get('code', 'N/A')}, "
            f"Throws {person.get('pitchHand', {}).get('code', 'N/A')}\n"
        )
        
        # --- 3. Get Stats (Smart Fallback) ---
        current_year = datetime.date.today().year # 2025
        stats_summary = ""
        
        # This is the function to get and format stats
        def get_stats_for_year(year):
            data = statsapi.get('people', {
                'personIds': player_id,
                'season': year,
                'hydrate': f'stats(group=[hitting,pitching,fielding],type=season,season={year})'
            })
            
            if not data or 'people' not in data or not data['people']:
                return None # Failed to get data
            
            player_data = data['people'][0]
            
            if 'stats' in player_data and player_data['stats']:
                for stat_group in player_data['stats']:
                    if stat_group['group']['displayName'] == 'hitting' and stat_group['type']['displayName'] == 'season':
                        if 'splits' in stat_group and stat_group['splits']:
                            
                            hitting_stats = stat_group['splits'][0]['stat']
                            season_label = stat_group['splits'][0].get('season', year)
                            
                            df = pd.DataFrame([hitting_stats])
                            return f"\n{season_label} Hitting Stats:\n{df.to_string()}\n"
            return None # No stats found
        
        # --- 4. The "Smart" Logic ---
        stats_summary = get_stats_for_year(current_year) # Try 2025 first
        
        if stats_summary is None:
            # If 2025 fails (it will in the off-season), try 2024
            stats_summary = get_stats_for_year(current_year - 1) 
        
        if stats_summary is None:
            # If both fail, just say so
            stats_summary = f"\nNo recent season stats found."
            
        # --- 5. Combine and return all context ---
        return bio_summary + stats_summary
        
    except Exception as e:
        return f"Error getting player info: {e}"