import mysql.connector

db = mysql.connector.connect(
  host="localhost",
  user="root",
  password="Chopda@1322",
  database="idmp"
)

cursor = db.cursor()

def select_query(query, data=None):
    """Select Operation."""
    cursor.reset()
    try:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        res = cursor.fetchall()
        return res
    except Exception as e:
        print("Failed select query: %s", e)
        return None

def insert_query(query, data = None):
    """insert Operation."""
    cursor.reset()
    try:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        db.commit() 
    except Exception as e:
        print("Failed insert_query: %s", e)
        return None

def proc_query(query, data = None):
    try:
        if data:
            cursor.callproc(query, data)
        else:
            cursor.callproc(query)
        db.commit()
    except Exception as e:
        print("Failed procedure call: %s", e)
