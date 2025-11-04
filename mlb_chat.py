import google.generativeai as genai
import os
import streamlit as st # Import streamlit to access secrets

def get_gemini_response(prompt):
    """
    Initializes the Gemini model and gets a response for a given prompt.
    """
    model = None # Initialize model as None
    try:
        # Prioritize Streamlit secrets if available
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        else:
            # Fallback to environment variable
            api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            st.error("Missing Gemini API Key in Streamlit secrets or environment variables!")
            return "⚠️ Error: Gemini API Key not configured."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro") # Or your preferred model
    
    except Exception as e:
        st.error(f"Error configuring Gemini: {e}")
        return f"⚠️ Error: Could not configure Gemini model. {e}"

    # Generate the content
    try:
        response = model.generate_content(prompt)
        if response and response.parts:
             return response.text.strip()
        else:
             # Handle cases where the model might return an empty response or safety block
             print(f"Gemini response issue. Prompt: {prompt}, Response: {response}")
             return "Sorry, I couldn't generate a response for that."
             
    except Exception as e:
        print(f"Error during Gemini generation: {e}") # Print error for debugging
        st.error(f"⚠️ Error interpreting query: {e}") # Show error in Streamlit
        return f"⚠️ Error interpreting query: {e}"