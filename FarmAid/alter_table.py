# ---- put this near init_db(), run once at startup ----
import sqlite3

def ensure_columns():
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()

    # 取得現有欄位
    c.execute("PRAGMA table_info(farmer_submissions);")
    cols = {row[1] for row in c.fetchall()}

    # 需要的欄位
    needed = {
        'username':      "ALTER TABLE farmer_submissions ADD COLUMN username TEXT;",
        'submission_date': "ALTER TABLE farmer_submissions ADD COLUMN submission_date TEXT;"
    }

    # 逐一補欄位（不存在才新增）
    for col, alter_sql in needed.items():
        if col not in cols:
            c.execute(alter_sql)

    conn.commit()
    conn.close()

# 在 init_db() 之後呼叫
ensure_columns()