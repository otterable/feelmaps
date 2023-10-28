import sqlite3
import shutil

# Function to fetch the schema (CREATE TABLE statements) of all tables in a SQLite database
def fetch_all_table_schemas(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [table[0] for table in cursor.fetchall()]
    table_schemas = {}
    for table in table_names:
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
        table_schemas[table] = cursor.fetchone()[0]
    conn.close()
    return table_schemas

# Function to recreate all tables in a new SQLite database
def recreate_all_tables(original_db_path, new_db_path, table_schemas):
    # Copy the original database to create a new one
    shutil.copy2(original_db_path, new_db_path)
    
    conn = sqlite3.connect(new_db_path)
    cursor = conn.cursor()
    
    for table, schema in table_schemas.items():
        if table == 'sqlite_sequence':
            continue
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
        cursor.execute(schema)
    
    conn.commit()
    conn.close()

# Specify the paths for the original and new databases
original_db_path = 'C:\\Users\\ottr\\Desktop\\Webseiten\\feelmaps\\instance\\pins.db'
new_db_path = 'C:\\Users\\ottr\\Desktop\\Webseiten\\feelmaps\\instance\\pinsX.db'

# Fetch the schemas of all tables in the original database
all_table_schemas = fetch_all_table_schemas(original_db_path)

# Recreate all tables in the new database
recreate_all_tables(original_db_path, new_db_path, all_table_schemas)
