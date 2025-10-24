import sqlite3
import google.generativeai as genai
import requests
import pandas as pd
import time
import json
import re
import os

# -------------------------------
# ⚙️ Setup
# -------------------------------
DB_PATH = "mlb_data.sqlite"
MLB_SEASON = 2025
GEMINI_API_KEY = "AIzaSyBscRNAqx-pGu_93wKDWomk9GG-hdxGIM8"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro-latest")


# -------------------------------
# ⚾ Fetch MLB Data (with resume & skip)
# -------------------------------
def get_mlb_data(resume=True):
    """
    Fetch all MLB player hitting + pitching stats and save incrementally to SQLite.
    Can resume from where it left off and skip already saved players.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mlb_players (
        name TEXT,
        team TEXT,
        group_type TEXT,
        avg REAL,
        era REAL,
        hits INTEGER,
        homeRuns INTEGER,
        rbi INTEGER,
        strikeOuts INTEGER,
        wins INTEGER,
        losses INTEGER,
        games INTEGER,
        inningsPitched REAL
    )
    """)
    conn.commit()

    # Get list of teams
    teams_url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    teams = requests.get(teams_url).json()["teams"]

    # 💡 Step 1: Load already-saved players (not just teams)
    saved_players = set()
    if resume:
        cursor.execute("SELECT DISTINCT name FROM mlb_players")
        saved_players = set(row[0] for row in cursor.fetchall())
        print(f"💾 Found {len(saved_players)} saved players already in database.\n")

    for idx, team in enumerate(teams, start=1):
        team_id = team["id"]
        team_name = team["name"]

        print(f"⚾ Fetching roster for {team_name} ({idx}/{len(teams)})...")
        roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
        roster = requests.get(roster_url).json().get("roster", [])

        team_players = []

        for player in roster:
            pid = player["person"]["id"]
            name = player["person"]["fullName"]

            # 💡 Step 2: Skip individual players already saved
            if name in saved_players:
                continue

            # Get both hitting and pitching stats
            for group in ["hitting", "pitching"]:
                stats_url = (
                    f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?"
                    f"stats=season&season={MLB_SEASON}&group={group}"
                )
                try:
                    resp = requests.get(stats_url, timeout=10).json()
                except Exception as e:
                    print(f"⚠️ Failed to fetch stats for {name}: {e}")
                    continue

                stats_list = resp.get("stats", [])
                if not stats_list:
                    continue
                splits = stats_list[0].get("splits", [])
                if not splits:
                    continue

                stat = splits[0].get("stat", {})
                team_players.append((
                    name,
                    team_name,
                    group,
                    stat.get("avg"),
                    stat.get("era"),
                    stat.get("hits"),
                    stat.get("homeRuns"),
                    stat.get("rbi"),
                    stat.get("strikeOuts"),
                    stat.get("wins"),
                    stat.get("losses"),
                    stat.get("gamesPlayed"),
                    stat.get("inningsPitched")
                ))

        # 💡 Step 3: Only save if new players were found
        if team_players:
            cursor.executemany("""
                INSERT INTO mlb_players (
                    name, team, group_type, avg, era, hits, homeRuns, rbi, strikeOuts,
                    wins, losses, games, inningsPitched
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, team_players)
            conn.commit()
            print(f"✅ Saved {len(team_players)} new players for {team_name}\n")
        else:
            print(f"⏭ No new players for {team_name}, skipped saving.\n")

        time.sleep(0.3)  # avoid rate limits

    conn.close()
    print("🎉 Finished fetching all MLB data.")

    # Load full data as DataFrame
    return pd.read_sql("SELECT * FROM mlb_players", sqlite3.connect(DB_PATH))


# -------------------------------
# 💾 SQLite Caching
# -------------------------------
def save_to_sqlite(df):
    """Save full MLB data to local SQLite cache."""
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("mlb_players", conn, if_exists="replace", index=False)
    print(f"💾 Saved {len(df)} records to {DB_PATH}.")


def load_from_sqlite():
    """Load cached MLB data."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM mlb_players", conn)
    print(f"📂 Loaded {len(df)} cached player records from {DB_PATH}.")
    return df


# -------------------------------
# 🧠 Interpret & Answer Queries
# -------------------------------
def chat_with_gemini(user_input, mlb_data):
    """Main chat logic using Gemini and local MLB data."""
    try:
        # Try to find a player name in the user input
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

            Use this info to answer clearly and conversationally.
            """
            return model.generate_content(prompt).text.strip()

        # No specific player — handle league-wide questions
        subset = mlb_data[["name", "team", "era", "avg", "wins", "strikeOuts", "homeRuns", "rbi"]].dropna(how="all")
        sample = subset.sample(min(800, len(subset)), random_state=42)
        data_json = sample.to_dict(orient="records")

        prompt = f"""
        You are a professional baseball analytics assistant.
        The user asked: "{user_input}"

        Here’s MLB 2025 player data (sampled from {len(subset)} players):
        {json.dumps(data_json[:200], indent=2)}

        Answer based on this data — clearly identify leaders, top players, or trends if asked.
        Be specific but concise.
        """
        return model.generate_content(prompt).text.strip()

    except Exception as e:
        return f"⚠️ Error interpreting query: {e}"


# -------------------------------
# 💬 Chat Loop
# -------------------------------
if __name__ == "__main__":
    print("⚾ MLB AI Baseball Chatbot")
    print("🔹 Type your question (e.g. 'How many home runs does Shohei Ohtani have?')")
    print("🔹 Type 'quit' to exit.\n")

    # Load or fetch data
    if os.path.exists(DB_PATH):
        mlb_data = load_from_sqlite()
    else:
        mlb_data = get_mlb_data()
        save_to_sqlite(mlb_data)

    # Chat
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit"]:
            print("👋 Goodbye!")
            break
        ai_reply = chat_with_gemini(user_input, mlb_data)
        print(f"\nAI: {ai_reply}\n")
        time.sleep(1)
