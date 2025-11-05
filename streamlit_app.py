import streamlit as st
import pandas as pd
from baseball_data import get_database_schema, run_sql_query
from mlb_chat import configure_gemini, get_gemini_response, extract_sql_query

# --- Page Configuration ---
st.set_page_config(page_title="MLB AI Analyst", layout="wide")
st.title("⚾ MLB Metrics ⚾")
st.subheader("Ask me anything about Baseball!")

# --- Configure API ---
configure_gemini()

# --- 1. Get Database Schema ---
with st.spinner("Loading database schema..."):
    db_schema = get_database_schema()

if "Error" in db_schema:
    st.error(db_schema)
    st.stop()

# Show schema in an expander for debugging/info
with st.expander("View Database Schema"):
    st.code(db_schema)

# --- 2. Chat Interface ---
user_query = st.text_input("Your question:", placeholder="e.g., Who had the most home runs in 1998?")

if st.button("Get Answer"):
    if user_query:
        with st.spinner("AI is thinking... (Step 1: Generating SQL)"):
            
            # --- THIS IS THE FIX ---
            # We are making the SQL prompt much more specific
            # to guide the AI correctly.
            sql_prompt = f"""
            You are an expert MySQL data analyst. Based on the database schema below,
            write a single, valid MySQL query to answer the user's question.
            
            **Key Information:**
            - The `batting` table contains player statistics (like HR, H, AB) and is linked by `playerID` and `yearID`.
            - The `people` table contains player names and is linked by `playerID`.
            - To get a player's name and their stats, you MUST join `batting` and `people` ON `batting.playerID = people.playerID`.
            - Pay close attention to the `yearID` when the question specifies a year.
            - When asked for "most" or "leader", always order by the statistic in question (e.g., HR) in descending order (DESC) and take the top (LIMIT 1).

            **Schema:**
            {db_schema}

            **Question:**
            {user_query}

            Only return the SQL query, wrapped in ```sql ... ```.
            """
            # --- END OF FIX ---
            
            sql_response = get_gemini_response(sql_prompt)
            sql_query = extract_sql_query(sql_response)
            
            if not sql_query:
                st.error("The AI could not generate a valid SQL query for that question.")
                st.write("AI Response:", sql_response)
                st.stop()
                
            # st.code(sql_query, language="sql") # We'll keep this hidden

        with st.spinner("Running query on database... (Step 2: Getting Data)"):
            
            # --- 4. Run the SQL Query ---
            query_data, error = run_sql_query(sql_query)
            
            if error:
                st.error(f"Database error: {error}")
                st.stop()
                
            if query_data.empty:
                st.warning("The query ran successfully, but returned no data.")
                st.stop()

        with st.spinner("AI is thinking... (Step 3: Generating Answer)"):
            
            # --- 5. Second AI Call: Generate Natural Language Answer ---
            answer_prompt = f"""
            You are a helpful MLB data analyst.
            Based on the user's question and the data returned from the database,
            provide a clear, natural language answer.

            User Question:
            {user_query}

            Data (in CSV format):
            {query_data.to_csv(index=False)}
            """
            
            final_answer = get_gemini_response(answer_prompt)
            st.markdown(final_answer)
            
            # Optionally show the data table
            with st.expander("View Raw Data"):
                st.dataframe(query_data)
                
    else:
        st.warning("Please enter a question.")