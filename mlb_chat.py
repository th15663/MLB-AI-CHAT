import streamlit as st
import google.generativeai as genai
import re

# --- Configure Gemini API ---
def configure_gemini():
    """Configures the Gemini API with the key from Streamlit secrets."""
    gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    if not gemini_api_key:
        st.error("GEMINI_API_KEY not found in Streamlit secrets.")
        st.stop()
    genai.configure(api_key=gemini_api_key)

# --- Get Gemini Response ---
def get_gemini_response(prompt):
    """
    Sends a prompt to the Gemini model and returns the text response.
    """
    try:
        model = genai.GenerativeModel('gemini-1.0-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error communicating with Gemini: {e}"

# --- Helper to extract SQL from AI response ---
def extract_sql_query(text):
    """
    Extracts a SQL query from a markdown code block.
    """
    match = re.search(r'```sql\n(.*?)\n```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback for simple query string
    match = re.search(r'SELECT\s.*?;', text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(0).strip()
        
    return None