import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error

# --- Aiven/MySQL Connection Details ---
DB_HOST = st.secrets.get("DB_HOST")
DB_USER = st.secrets.get("DB_USER")
DB_PASSWORD = st.secrets.get("DB_PASSWORD")
DB_NAME = st.secrets.get("DB_NAME")

# --- THIS IS THE FIX ---
# Get the port. If it's missing, use 3306 (default MySQL port)
DB_PORT_STR = st.secrets.get("DB_PORT")
if DB_PORT_STR is None:
    DB_PORT = 3306
else:
    try:
        DB_PORT = int(DB_PORT_STR) # Ensure it's an integer
    except ValueError:
        st.error(f"Invalid DB_PORT secret: '{DB_PORT_STR}'. Must be a number.")
        st.stop()
# --- END OF FIX ---


# --- Helper function to create a MySQL connection ---
def create_mysql_connection():
    """Creates and returns a MySQL connection object."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT, # Use the validated port
            database=DB_NAME
        )
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None, f"MySQL Error: {e}" # Return error
    return conn, None # Return connection and no error

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

# --- NEW: Function to get the entire database schema ---
@st.cache_data(ttl=3600)
def get_database_schema():
    """
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

# --- NEW: Function to run a read-only SQL query ---
def run_sql_query(query):
    """
    Runs a user-provided SQL query (read-only)
    and returns the result as a DataFrame.
    """
    conn, error = create_mysql_connection()
    if error:
        return pd.DataFrame(), error
    if conn is None:
        return pd.DataFrame(), "Error: Could not connect to database."
        
    # Basic security: Only allow SELECT statements
    if not query.strip().upper().startswith("SELECT"):
        return pd.DataFrame(), "Error: Only SELECT queries are allowed."
        
    try:
        # Use connection string for pandas
        # Note: SQLAlchemy must be installed (it is in your requirements.txt)
        connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        df = pd.read_sql_query(query, connection_string)
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error running query: {e}"
    finally:
        # pd.read_sql_query handles its own connection closing
        pass