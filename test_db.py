import psycopg2

try:
    conn = psycopg2.connect(
        dbname="girlfriend_rating",
        user="postgres",
        password="0000",
        host="localhost",
        port="5432",
    )
    print("Connection successful!")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    tables = cursor.fetchall()
    print("Tables in database:", tables)
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
