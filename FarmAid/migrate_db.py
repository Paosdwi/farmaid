import sqlite3

conn = sqlite3.connect("agri_diagnosis.db")
c = conn.cursor()

# 在 farmer_submissions 加一個 problem_desc 欄位
c.execute("ALTER TABLE farmer_submissions ADD COLUMN problem_desc TEXT;")

conn.commit()
conn.close()

print("已新增 problem_desc 欄位")
