import sqlite3

con = sqlite3.connect("dummy_db.db")
cursor = con.cursor()

cursor.execute("SELECT Username, Password FROM users WHERE Username='H598278G8k1l9nu6x4b4' AND Password = 'M6ZCK3999AYAvQ0Z3245'")
fetched_credentials = cursor.fetchone()

print(fetched_credentials)
