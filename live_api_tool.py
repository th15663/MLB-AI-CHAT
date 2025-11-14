# live_api_tool.py
import mlb_statsapi
import datetime
import streamlit as st
import pandas as pd

# --- Tool 1: Get Scores ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def get_yesterdays_scores():
    """Fetches all game scores from yesterday."""
    try:
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        schedule = mlb_statsapi.get('schedule', {'sportId': 1, 'date': yesterday})

        if not schedule['dates']:
            return "No games were played yesterday."

        games = schedule['dates'][0]['games']
        game_summaries = []

        for game in games:
            if game['status']['detailedState'] != 'Final':
                continue

            home_team = game['teams']['home']['team']['name']
            home_score = game['teams']['home']['score']
            away_team = game['teams']['away']['team']['name']
            away_score = game['teams']['away']['score']
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

# --- Tool 2: Get Player Info & Stats ---
def get_player_info(player_name):
    """
    Finds a player, gets their bio, and gets their current season stats.
    Returns a single string of context.
    """
    try:
        # --- 1. Find the player ID ---
        search_results = mlb_statsapi.get('player', {'name': player_name})

        if not search_results or 'people' not in search_results or not search_results['people']:
            return f"Error: Could not find any player named '{player_name}'."

        player = search_results['people'][0]
        player_id = player['id']
        full_name = player['fullName']

        # --- 2. Get Player Bio (Person endpoint) ---
        bio = mlb_statsapi.get('person', {'personId': player_id})
        person = bio['people'][0]

        bio_summary = (
            f"Player: {person.get('fullName', 'N/A')}\n"
            f"Born: {person.get('birthDate', 'N/A')} in {person.get('birthCity', 'N/A')}\n"
            f"Team: {person.get('currentTeam', {}).get('name', 'N/A')}\n"
            f"Position: {person.get('primaryPosition', {}).get('name', 'N/A')}\n"
            f"Bio: Bats {person.get('bats', {}).get('code', 'N/A')}, "
            f"Throws {person.get('throws', {}).get('code', 'N/A')}, "
            f"Height {person.get('height', 'N/A')}, "
            f"Weight {person.get('weight', 'N/A')} lbs.\n"
        )

        # --- 3. Get Season Stats (person_stats endpoint) ---
        current_year = datetime.date.today().year
        stats = mlb_statsapi.get('person_stats', {
            'personId': player_id, 
            'stats': ['season'], 
            'group': 'hitting', # Check hitting first
            'season': current_year
        })

        stats_summary = ""
        if 'stats' in stats and stats['stats'] and 'splits' in stats['stats'][0] and stats['stats'][0]['splits']:
            hitting_stats = stats['stats'][0]['splits'][0]['stat']
            df = pd.DataFrame([hitting_stats])
            stats_summary += f"\n{current_year} Hitting Stats:\n{df.to_string()}\n"
        else:
            stats_summary += f"\nNo {current_year} hitting stats found.\n"

        # (You could add a check for pitching stats here too)

        # --- 4. Combine and return all context ---
        return bio_summary + stats_summary

    except Exception as e:
        return f"Error getting player info: {e}"