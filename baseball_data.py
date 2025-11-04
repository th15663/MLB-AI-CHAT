import pandas as pd
import mysql.connector
from mysql.connector import Error

# --- Aiven/MySQL Connection Details ---
# (Pulls from Streamlit secrets)
DB_HOST = st.secrets.get("DB_HOST")
DB_USER = st.secrets.get("DB_USER")
DB_PASSWORD = st.secrets.get("DB_PASSWORD")
DB_PORT = st.secrets.get("DB_PORT")
DB_NAME = st.secrets.get("DB_NAME")

# --- Helper function to create a MySQL connection ---
def create_mysql_connection():
    """Creates and returns a MySQL connection object."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME
        )
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
    return conn

# --- Function to list all tables ---
def list_tables_mysql():
    """Returns a list of all table names in the database."""
    conn = create_mysql_connection()
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
@st.cache_data(ttl=3600)  # Cache the schema for 1 hour
def get_database_schema():
    """
    Fetches the schema (table and column names) for all tables.
    Returns a formatted string.
    """
    conn = create_mysql_connection()
    if conn is None:
        return "Could not connect to database."
        
    all_tables = list_tables_mysql()
    if not all_tables:
        return "No tables found in database."
        
    schema_string = ""
    try:
        cursor = conn.cursor()
        for table in all_tables:
            schema_string += f"Table: {table}\nColumns:\n"
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
    conn = create_mysql_connection()
    if conn is None:
        return pd.DataFrame(), "Error: Could not connect to database."
        
    # Basic security: Only allow SELECT statements
    if not query.strip().upper().startswith("SELECT"):
        return pd.DataFrame(), "Error: Only SELECT queries are allowed."
        
    try:
        df = pd.read_sql_query(query, conn)
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"Error running query: {e}"
    finally:
        if conn and conn.is_connected():
            conn.close()