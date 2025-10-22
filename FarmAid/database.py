import sqlite3

def init_db():
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()
    
    # 建立 users 表格
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT NOT NULL UNIQUE,
                 password TEXT NOT NULL,
                 role TEXT NOT NULL
                 )''')
    
    # 建立 farmer_submissions 表格，包含 username、submission_date 和 doctor_username
    c.execute('''CREATE TABLE IF NOT EXISTS farmer_submissions (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             applicant TEXT NOT NULL,
             phone TEXT NOT NULL,
             gps_lat TEXT,
             gps_lon TEXT,
             plant_name TEXT NOT NULL,
             problem_desc TEXT,        -- ✅ 新增：問題描述
             location TEXT NOT NULL,
             plant_condition TEXT,
             photo_whole TEXT,
             photo_affected TEXT,
             photo_condition TEXT,
             diagnosis TEXT,
             status TEXT DEFAULT 'pending',
             username TEXT NOT NULL,
             submission_date TEXT NOT NULL
             )''')
    conn.commit()
    conn.close()