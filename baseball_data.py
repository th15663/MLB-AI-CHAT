import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os # We need this to find the certificate file

# --- Aiven/MySQL Connection Details ---
DB_HOST = st.secrets.get("DB_HOST")
DB_USER = st.secrets.get("DB_USER")
DB_PASSWORD = st.secrets.get("DB_PASSWORD")
DB_NAME = st.secrets.get("DB_NAME")
DB_PORT_STR = st.secrets.get("DB_PORT")

if DB_PORT_STR is None:
    DB_PORT = 3306
else:
    try:
        DB_PORT = int(DB_PORT_STR)
    except ValueError:
        st.error(f"Invalid DB_PORT secret: '{DB_PORT_STR}'. Must be a number.")
        st.stop()
        
# --- THIS IS THE FIX ---
# Define the path to the SSL certificate
# This assumes 'ca.pem' is in the same folder as your app
CERT_PATH = os.path.join(os.path.dirname(__file__), 'ca.pem')

# Check if the certificate file exists
if not os.path.exists(CERT_PATH):
    st.error("Database Error: 'ca.pem' file not found.")
    st.write(f"Looked for file at: {CERT_PATH}")
    st.write("Please download the 'CA Certificate' from Aiven and upload it to your GitHub repository.")
    st.stop()
    
# Create the SSL argument dictionary
SSL_ARGS = {
    'ssl_ca': CERT_PATH,
    'ssl_verify_cert': True
}
# --- END OF FIX ---


# --- Helper function to create a MySQL connection ---
def create_mysql_connection():
    """Creates and returns a MySQL connection object."""
    conn = None
    try:
        # Pass the SSL_ARGS to the connect function
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME,
            **SSL_ARGS # This applies the SSL settings
        )
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None, f"MySQL Error: {e}"
    return conn, None

# --- Function to list all tables ---
def list_tables_mysql():
    """Returns a list of all table names in the database."""
    conn, error = create_mysql_connection()
    if error:
        print(error)
        return []
        
    if conn is None:
        return []
        
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        return tables
    except Error as e:
        print(f"Error listing tables: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- Function to get the entire database schema ---
@st.cache_data(ttl=3600)
def get_database_schema():
    """
Signature: get_database_schema()
    Fetches the schema (table and column names) for all tables.
    Returns a formatted string.
    """
    conn, error = create_mysql_connection()
    if error:
        return f"Error: {error}"
    if conn is None:
        return "Could not connect to database."
        
    all_tables = list_tables_mysql()
    if not all_tables:
        return "No tables found in database."
        
    schema_string = ""
    try:
        cursor = conn.cursor()
        for table in all_tables:
            schema_string += f"Table: {table}\n"
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            for col in columns:
                schema_string += f"  - {col[0]} ({col[1]})\n"
            schema_string += "\n"
        return schema_string
    except Error as e:
        return f"Error fetching schema: {e}"
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- Function to run a read-only SQL query ---
def run_sql_query(query):
    """
    Runs a user-provided SQL query (read-only)
    and returns the result as a DataFrame.
    """
    # Basic security: Only allow SELECT statements
    if not query.strip().upper().startswith("SELECT"):
        return pd.DataFrame(), "Error: Only SELECT queries are allowed."
        
    try:
        # Use SQLAlchemy engine for pandas, as it handles SSL args well
        # Note: SQLAlchemy must be installed (it is in your requirements.txt)
        connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        engine_args = {
            'connect_args': SSL_ARGS
        }
        
        # Need to import this
        from sqlalchemy import create_engine
        engine = create_engine(connection_string, **engine_args)
        
        df = pd.read_sql_query(query, engine)
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error running query: {e}"