# streamlit_app.py
import streamlit as st
import os
import time
from datetime import datetime

# --- import your modularized code ---
# Put your get_mlb_data/load_from_sqlite/save_to_sqlite in baseball_data.py
# Put your chat_with_gemini(...) in mlb_chat.py
# If you didn't split files, you can paste those functions here directly.

from baseball_data import load_from_mysql # Keep get_mlb_data if you still use it for API fetching elsewhere
from mlb_chat import chat_with_gemini

# --- basic config ---
st.set_page_config(page_title="⚾ MLB AI Chat", page_icon="⚾", layout="centered")
st.title("MLB Metrics")
st.write("Ask Anything")

# --- sidebar controls ---
st.sidebar.header("Settings")
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None

if st.sidebar.button("Refresh data (fetch from MLB API)"):
    # when pressed, fetch and overwrite cache (danger: slow)
    with st.spinner("Fetching MLB data (may take several minutes)..."):
        df = get_mlb_data(resume=False)   # set resume=False if you want a full refresh
        save_to_sqlite(df)
        st.session_state.last_updated = datetime.now().isoformat()
    st.experimental_rerun()

st.sidebar.markdown("**Cache file:**")
st.sidebar.write(DB_PATH)
if st.session_state.last_updated:
    st.sidebar.markdown(f"**Last refreshed:** {st.session_state.last_updated}")

# --- load data (fast from sqlite) ---
with st.spinner("Loading cached MLB data..."):
    if os.path.exists(DB_PATH):
        mlb_data = load_from_sqlite()
    else:
        st.info("No cached data found. Click **Refresh data** (sidebar) to fetch from MLB API.")
        mlb_data = None

# --- chat UI ---
st.subheader("What do you want to know?")
if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.text_input("Ask a question")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Send"):
        if not user_input:
            st.warning("Type a question first.")
        else:
            if mlb_data is None:
                st.error("No MLB data loaded. Refresh data first.")
            else:
                with st.spinner("Thinking..."):
                    # call your chat function (returns a text reply)
                    reply = chat_with_gemini(user_input, mlb_data)
                st.session_state.history.append(("You", user_input))
                st.session_state.history.append(("AI", reply))
                # optionally persist chat to a small local file or DB
                st.rerun()


with col2:
    if st.button("Clear chat"):
        st.session_state.history = []
        st.experimental_rerun()

# --- show chat history nicely ---
st.markdown("---")
for role, text in st.session_state.history[::-1]:  # show newest first
    if role == "You":
        st.markdown(f"**Q:** {text}")
    else:
        st.markdown(f"**A:** {text}")
    st.write("")

# optional: show sample of the DB
if st.checkbox("Show cached sample data (10 rows)"):
    if mlb_data is not None:
        st.dataframe(mlb_data.head(10))
    else:
        st.write("No data loaded.")
