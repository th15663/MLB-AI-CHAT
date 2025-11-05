import streamlit as st
import pandas as pd
# We no longer need 'baseball_data' or 'extract_sql_query'
from mlb_chat import configure_gemini, get_gemini_response

# --- Page Configuration ---
st.set_page_config(page_title="MLB AI Analyst", layout="wide")
st.title("⚾ MLB Metrics ⚾")
st.subheader("Ask me anything about Baseball!")

# --- Configure API ---
configure_gemini()

# --- Chat Interface ---
user_query = st.text_input("Your question:", placeholder="e.g., Who had the most home runs in 1998?")

if st.button("Get Answer"):
    if user_query:
        with st.spinner("AI is thinking..."):
            
            # --- This is the new, single AI call ---
            answer_prompt = f"""
            You are a helpful and knowledgeable MLB data analyst and historian.
            A user has a question about baseball. Please provide a clear, 
            natural language answer based on your general knowledge.

            User Question:
            {user_query}
            """
            
            final_answer = get_gemini_response(answer_prompt)
            st.markdown(final_answer)
            
    else:
        st.warning("Please enter a question.")