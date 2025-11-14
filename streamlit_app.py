import streamlit as st
import pandas as pd
import json

# --- Notice these imports ---
# We are ONLY importing our chat functions and our NEW live tool.
# We are IGNORING baseball_data.py and rag_tool.py.
from mlb_chat import configure_gemini, get_gemini_response
from live_api_tool import get_yesterdays_scores, get_player_info 

# --- Page Configuration ---
st.set_page_config(page_title="MLB AI Analyst", layout="wide")
st.title("⚾ MLB Metrics ⚾")
st.subheader("Ask me anything about current MLB stats!")

# --- Configure API ---
configure_gemini()

# --- 2. Chat Interface ---
user_query = st.text_input("Your question:", placeholder="e.g., Tell me about Shohei Ohtani")

if st.button("Get Answer"):
    if user_query:

        # --- 3. AI Router Call ---
        # This "brain" will only route between our LIVE API tools.
        with st.spinner("AI is analyzing your question..."):

            router_prompt = f"""
            You are an AI router. Your job is to analyze a user's question
            and identify the correct tool and any needed entities (like player names).

            You must respond in a JSON format with two keys: "tool" and "entity".

            The available tools are:
            - "scores": For questions about yesterday's scores.
            - "player_info": For questions about a specific player's bio or stats.
            - "general": For any other question.

            The "entity" key should be the full player name if "tool" is "player_info",
            otherwise it should be an empty string.

            Examples:
            User: "What were the scores yesterday?"
            {{"tool": "scores", "entity": ""}}

            User: "Tell me about Shohei Ohtani"
            {{"tool": "player_info", "entity": "Shohei Ohtani"}}

            User: "Who won the Yankees game?"
            {{"tool": "scores", "entity": ""}}

            User: "how many hits does bobby witt jr have?"
            {{"tool": "player_info", "entity": "Bobby Witt Jr."}}

            User Question:
            "{user_query}"
            """

            router_response = get_gemini_response(router_prompt)

        # --- 4. Parse Router Response ---
        try:
            cleaned_response = router_response.strip().replace("```json", "").replace("```", "")
            decision = json.loads(cleaned_response)
            tool = decision.get("tool", "general")
            entity = decision.get("entity", "")
        except Exception as e:
            st.error(f"AI Router Error: Could not understand AI decision. {e}")
            st.write("Raw AI Response:", router_response)
            st.stop()

        # --- 5. Run the Correct Tool ---
        context = ""
        if tool == "scores":
            st.info("Tool chosen: Getting Yesterday's Scores")
            with st.spinner("Calling MLB-StatsAPI for scores..."):
                context = get_yesterdays_scores()

        elif tool == "player_info":
            if not entity:
                st.error("AI Router Error: 'player_info' tool chosen, but no player name was found.")
                st.stop()
            st.info(f"Tool chosen: Getting info for {entity}")
            with st.spinner(f"Calling MLB-StatsAPI for {entity}...") :
                context = get_player_info(entity)

        elif tool == "general":
            st.info("Tool chosen: General Question")
            pass

        # --- 6. Generate Final Answer (using the context) ---
        with st.spinner("AI is generating your answer..."):

            if context:
                answer_prompt = f"""
                You are a helpful MLB expert. Answer the user's question 
                based *only* on the context provided below.

                Context:
                {context}

                User Question:
                {user_query}

                Your Answer:
                """
            else:
                answer_prompt = f"""
                You are a helpful MLB expert. 
                Answer the user's general question: "{user_query}"
                """

            final_answer = get_gemini_response(answer_prompt)
            st.markdown(final_answer)

            if context:
                with st.expander("View Raw Data from API"):
                    st.text(context)