from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
import requests
import logging
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 設置日誌
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 獲取天氣資料（使用 OpenWeatherMap API）
def get_weather_data(lat=25.0330, lon=121.5654):
    api_key = '4cfc391b51a8690e97b30b16f7132aef'  # 你的 API Key，確認無誤
    url = f'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric'
    try:
        response = requests.get(url, timeout=10).json()  # 添加超時設定
        logger.debug(f"API Response: {response}")
        if 'weather' not in response or not response.get('weather') or 'main' not in response:
            raise KeyError("無效的 API 回應結構")
        return {
            'condition': response['weather'][0]['main'],
            'temperature': f"{response['main']['temp']}°C",
            'humidity': f"{response['main']['humidity']}%"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"網路錯誤: {e}")
        return {'condition': '未知', 'temperature': '未知', 'humidity': '未知'}
    except KeyError as e:
        logger.error(f"API 資料錯誤: {e}")
        return {'condition': '未知', 'temperature': '未知', 'humidity': '未知'}
    except Exception as e:
        logger.error(f"意外錯誤: {e}")
        return {'condition': '未知', 'temperature': '未知', 'humidity': '未知'}

# 初始化資料庫
from database import init_db
init_db()

# 首頁
@app.route('/')
def index():
    if 'username' in session:
        if session['role'] == 'farmer':
            weather = get_weather_data()  # 預設值，後續由前端動態更新
            return render_template('farmer_home.html', weather=weather)
        elif session['role'] == 'doctor':
            return render_template('doctor_home.html')
    return redirect(url_for('login'))

# 登入
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('agri_diagnosis.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            session['role'] = user[3]  # role 欄位
            return redirect(url_for('index'))
        flash('無效的憑證', 'error')
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.clear()
    flash('已成功登出！', 'success')
    return redirect(url_for('login'))

# 農民表單提交
@app.route('/submit_form', methods=['GET', 'POST'])
def submit_form():
    if 'username' not in session or session['role'] != 'farmer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        applicant = request.form.get('applicant', '').strip()
        phone = request.form.get('phone', '').strip()
        gps_lat = request.form.get('gps_lat', '')
        gps_lon = request.form.get('gps_lon', '')
        plant_name = request.form.get('plant_name', '').strip()
        problem_desc = request.form.get('problem_desc', '').strip()
        location = request.form.get('location', '').strip()
        username = session['username']
        submission_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 取得檔案
        photo_whole = request.files.get('photo_whole')
        photo_affected = request.files.get('photo_affected')
        photo_condition_file = request.files.get('photo_condition')

        if not all([photo_whole and photo_whole.filename,
                    photo_affected and photo_affected.filename,
                    photo_condition_file and photo_condition_file.filename]):
            flash('請上傳所有照片！', 'error')
            return redirect(url_for('submit_form'))

        try:
            # 確保上傳目錄存在
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # 產生唯一檔名，避免覆蓋
            def unique_name(f):
                return f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"

            photo_whole_filename     = unique_name(photo_whole)
            photo_affected_filename  = unique_name(photo_affected)
            photo_condition_filename = unique_name(photo_condition_file)

            # 儲存檔案
            photo_whole_path     = os.path.join(app.config['UPLOAD_FOLDER'], photo_whole_filename)
            photo_affected_path  = os.path.join(app.config['UPLOAD_FOLDER'], photo_affected_filename)
            photo_condition_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_condition_filename)

            photo_whole.save(photo_whole_path)
            photo_affected.save(photo_affected_path)
            photo_condition_file.save(photo_condition_path)

            # 寫入資料庫（含 problem_desc）
            conn = sqlite3.connect('agri_diagnosis.db')
            c = conn.cursor()
            c.execute(
                '''INSERT INTO farmer_submissions
                   (applicant, phone, gps_lat, gps_lon, plant_name, problem_desc, location,
                    photo_whole, photo_affected, photo_condition, username, submission_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (applicant, phone, gps_lat, gps_lon, plant_name, problem_desc, location,
                 photo_whole_filename, photo_affected_filename, photo_condition_filename,
                 username, submission_date)
            )
            conn.commit()
            conn.close()

            # 記錄一下實際檔名，方便你在 console 檢查
            app.logger.info({
                "whole": photo_whole_filename,
                "affected": photo_affected_filename,
                "condition": photo_condition_filename
            })

            flash('表單提交成功！', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            app.logger.exception(f"提交錯誤: {e}")
            flash('表單提交失敗，請檢查照片或網路！', 'error')
            return redirect(url_for('submit_form'))

    return render_template('submit_form.html')



# 農民或醫生查看診斷回報
@app.route('/diagnosis_report')
def diagnosis_report():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()
    if session['role'] == 'farmer':
        c.execute("SELECT * FROM farmer_submissions WHERE status='diagnosed' AND username=?", (session['username'],))
    elif session['role'] == 'doctor':
        c.execute("SELECT * FROM farmer_submissions WHERE status='diagnosed'")
    reports = c.fetchall()
    conn.close()
    return render_template('diagnosis_report.html', reports=reports)

# 植物醫生檢視表單
@app.route('/diagnosis_service')
def diagnosis_service():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()
    c.execute("SELECT * FROM farmer_submissions WHERE status='pending'")
    submissions = c.fetchall()
    conn.close()
    return render_template('diagnosis_service.html', submissions=submissions)

# 植物醫生提交診斷
@app.route('/submit_diagnosis/<int:submission_id>', methods=['GET', 'POST'])
def submit_diagnosis(submission_id):
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()
    c.execute("SELECT * FROM farmer_submissions WHERE id=?", (submission_id,))
    submission = c.fetchone()
    conn.close()

    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        doctor_username = session['username']  # 記錄提交診斷的醫生
        conn = sqlite3.connect('agri_diagnosis.db')
        c = conn.cursor()
        c.execute("UPDATE farmer_submissions SET diagnosis=?, status='diagnosed', doctor_username=? WHERE id=?", 
                  (diagnosis, doctor_username, submission_id))
        conn.commit()
        conn.close()
        flash('診斷提交成功！', 'success')
        return redirect(url_for('diagnosis_service'))
    
    return render_template('submit_diagnosis.html', submission=submission)

# 植物醫生查看診斷歷史
@app.route('/diagnosis_history')
def diagnosis_history():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('agri_diagnosis.db')
    c = conn.cursor()
    c.execute("SELECT * FROM farmer_submissions WHERE status='diagnosed' AND doctor_username=?", (session['username'],))
    diagnoses = c.fetchall()
    conn.close()
    return render_template('diagnosis_history.html', diagnoses=diagnoses)

@app.route('/delete_report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if 'username' not in session or session['role'] != 'farmer':
        return redirect(url_for('login'))

    try:
        conn = sqlite3.connect('agri_diagnosis.db')
        c = conn.cursor()

        # 確認報告屬於當前用戶
        c.execute("SELECT username FROM farmer_submissions WHERE id=?", (report_id,))
        report = c.fetchone()
        if not report or report[0] != session['username']:
            flash('無權刪除此報告', 'error')
            conn.close()
            return redirect(url_for('diagnosis_report'))

        # 取得要刪除的報告圖片檔名（先刪檔案）
        c.execute("SELECT photo_whole, photo_affected, photo_condition FROM farmer_submissions WHERE id=?", (report_id,))
        photos = c.fetchone()

        # 刪除檔案
        if photos:
            for filename in photos:
                if filename:
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(path):
                        os.remove(path)

        # 刪除報告
        c.execute("DELETE FROM farmer_submissions WHERE id=?", (report_id,))
        conn.commit()
        conn.close()
        flash('報告已刪除', 'success')
    except Exception as e:
        print(f"刪除錯誤: {e}")
        flash('刪除失敗', 'error')

    return redirect(url_for('diagnosis_report'))

# 新增天氣 API 路由
@app.route('/weather')
def get_weather():
    lat = request.args.get('lat', default=25.0330, type=float)
    lon = request.args.get('lon', default=121.5654, type=float)
    weather_data = get_weather_data(lat, lon)
    return {'condition': weather_data['condition'], 'temperature': weather_data['temperature'], 'humidity': weather_data['humidity']}
@app.route("/test")
def test():
    return "✅ Flask 運作正常，Cloudflare Tunnel 已成功連線！"

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', debug=True, port=port)
