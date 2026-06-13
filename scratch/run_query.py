import sys
sys.path.append('backend')
import db

query1 = "SELECT status, COUNT(*) FROM predictions_history GROUP BY status;"
query2 = "SELECT * FROM predictions_history LIMIT 1;"

def run():
    print("--- Query 1 ---")
    try:
        with db.DBConnection() as dbc:
            dbc.execute(query1)
            rows = dbc.fetchall()
            if rows:
                import pandas as pd
                df1 = pd.DataFrame([dict(r) for r in rows])
                print(df1.to_markdown(index=False))
            else:
                print("No results for Q1")
                
            print("\n--- Query 2 ---")
            dbc.execute(query2)
            rows2 = dbc.fetchall()
            if rows2:
                df2 = pd.DataFrame([dict(r) for r in rows2])
                print(df2.to_markdown(index=False))
            else:
                print("No results for Q2")
    except Exception as e:
        print("Error running queries:", e)

if __name__ == "__main__":
    run()
