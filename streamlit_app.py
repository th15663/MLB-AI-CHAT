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
            
            # --- 3. First AI Call: Generate SQL ---
            sql_prompt = f"""
            You are an expert MySQL data analyst. Based on the database schema below,
            write a single, valid MySQL query to answer the user's question.
            Only return the SQL query, wrapped in ```sql ... ```.

            Schema:
            {db_schema}

            Question:
            {user_query}
            """
            
            sql_response = get_gemini_response(sql_prompt)
            sql_query = extract_sql_query(sql_response)
            
            if not sql_query:
                st.error("The AI could not generate a valid SQL query for that question.")
                st.write("AI Response:", sql_response)
                st.stop()
                
            # --- SQL QUERY IS NOW HIDDEN ---
            # st.code(sql_query, language="sql") # No longer showing this to the user
            # --- ---

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
            st.markdown(final_answer) # This is the final, natural answer
            
            # Optionally show the data table
            with st.expander("View Raw Data"):
                st.dataframe(query_data)
                
    else:
        st.warning("Please enter a question.")