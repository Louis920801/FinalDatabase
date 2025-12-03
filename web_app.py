from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from sql_helper import *
from html_helper import *
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.debug = True

app.secret_key = 'mango'

# print("== USING SQL Server connection ==")

# Enter your database connection details below
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'tempuser'
# app.config['MYSQL_PASSWORD'] = '123+Temppass'
# app.config['MYSQL_DB'] = 'hospitalDB'
# app.config['MYSQL_PORT'] = 3306
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'tempuser'
app.config['MYSQL_PASSWORD'] = '123+Temppass'
app.config['MYSQL_DB'] = 'hospitalDB'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Intialize MySQL
mysql = MySQL(app)
print("== USING MySQL DB:", app.config['MYSQL_DB'], "on port", app.config['MYSQL_PORT'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def choose():
    if request.form.get("start"):
        # redirect staff login attempts to the login page first
        return redirect(url_for('login'))
    else:
        return render_template('index.html')

@app.route('/pick_table', methods=['POST', 'GET'])
# def pick_table():
#     table_name = ''
#     if session.get('table_name'):
#         session.pop('table_name', None)
#     options = nested_list_to_html_select(show_tables(mysql))
#     if request.method == 'POST' and 'table' in request.form:
#         if 'describe' in request.form:
#             table_name = request.form['table']
#             table = nested_list_to_html_table(desc_table(mysql, table_name))
#             return render_template('pick_table.html', table=table, table_name=table_name, options=options)
#         elif 'pick' in request.form:
#             session['table_name'] = request.form['table']
#             return redirect(url_for('edit'))

#     table = nested_list_to_html_table(show_tables(mysql)) # Warring 
#     return render_template('pick_table.html', table=table, table_name=table_name, options=options)

@app.route("/pick_table", methods=["GET", "POST"])
def pick_table():
    # --- [保留] 登入檢查 ---
    if not session.get('staff_logged_in'):
        return redirect(url_for('login'))

    DB_NAME = "hospitalDB"
    
    # 初始化變數，用於模板渲染
    table_name = ""             # 當前選取的資料表名稱 (用於選單選中)
    table_description = None    # 資料表結構描述 (用於右側描述表格)

    try:
        cur = mysql.connection.cursor()

        # --- [保留] 目前連到哪個 DB 檢查與切換 ---
        cur.execute("SELECT DATABASE()")
        row = cur.fetchone()
        if isinstance(row, dict):
            db = next(iter(row.values()), None)
        else:
            db = row[0] if row else None

        if not db:
            cur.execute(f"USE `{DB_NAME}`")

        # --- [保留] 獲取所有資料表名稱 ---
        cur.execute(f"SHOW TABLES FROM `{DB_NAME}`")
        rows = cur.fetchall()
        cur.close()

        # --- [保留] 資料表名稱標準化與排序 ---
        tables = []
        for r in rows:
            if isinstance(r, dict):
                name = next(iter(r.values()), None)
            else:
                name = r[0] if r else None
            if isinstance(name, (bytes, bytearray)):
                name = name.decode()
            if name:
                tables.append(name)
        tables.sort()

    except Exception as e:
        # --- [保留] 錯誤處理 ---
        code = None
        msg = repr(e)
        if getattr(e, "args", None):
            code = e.args[0]
            if len(e.args) > 1 and e.args[1]:
                msg = e.args[1]
        return render_template("invalid.html", e=f"MySQL error code={code}, message={msg}")

    # POST：Describe / Pick
    if request.method == "POST":
        selected_table = (request.form.get("table") or "").strip()
        
        # 將選取的資料表名稱賦值給 template 變數，保持下拉選單選中狀態
        table_name = selected_table 

        # --- [修改] 處理 DESCRIBE 按鈕邏輯 ---
        if "describe" in request.form and selected_table:
            try:
                cur = mysql.connection.cursor()
                # 執行 DESCRIBE 查詢
                cur.execute(f"DESCRIBE `{DB_NAME}`.`{selected_table}`")
                desc_rows = cur.fetchall()
                cur.close()
                
                # 標準化資料格式：轉換成字典列表，方便模板存取 (Field, Type, Null, Key, Default, Extra)
                if desc_rows:
                    if isinstance(desc_rows[0], dict):
                        # 如果是 DictCursor，直接使用
                        table_description = desc_rows
                    else:
                        # 如果是 TupleCursor，進行轉換
                        keys = ["Field", "Type", "Null", "Key", "Default", "Extra"]
                        table_description = [dict(zip(keys, row)) for row in desc_rows]
                
                # DESCRIBE 成功後，渲染模板並傳遞 table_description
                return render_template(
                    "pick_table.html",
                    tables=tables,
                    table_name=table_name,             # 保留選中的 table_name
                    table_description=table_description # 傳遞結構描述資料
                )
            except Exception as e:
                # --- [保留] DESCRIBE 錯誤處理 ---
                return render_template("invalid.html", e=f"DESCRIBE 失敗：{repr(e)}")

        # --- [保留] 處理 PICK 按鈕邏輯 ---
        if "pick" in request.form and selected_table:
            session["table_name"] = selected_table 
            session.modified = True
            return redirect(url_for("edit"))

    # GET 初始頁 或 POST 但沒有動作
    # --- [保留] GET 初始頁渲染邏輯 ---
    return render_template(
        "pick_table.html",
        tables=tables,
        table_name=table_name, # POST 失敗時，這裡的 table_name 依然是選中的那個
        table_description=table_description # 初始為 None
    )


@app.route('/edit', methods=['POST', 'GET'])
def edit():
    table_name = session.get('table_name')
    if not table_name:
        return redirect(url_for('pick_table'))
    
    operation = None
    form_html = ''
    if request.method == 'POST' and 'insert_form' in request.form:
        operation = 'insert'
        table = nested_list_to_html_table(select_with_headers(mysql, table_name), buttons=True)
        form_html = get_insert_form(select_with_headers(mysql, table_name)[0])
        return render_template('edit.html', table=table, table_name=table_name, operation=operation, form_html=form_html)
    elif request.method == 'POST' and 'insert_execute' in request.form:
        columns = select_with_headers(mysql, table_name)[0]
        values = []
        for col in columns:
            val = request.form[col]
            if val.isnumeric():
                values.append(val)
            else:
                values.append("\'" + val + "\'")
        try:
            tables = insert_to_table(mysql, table_name, columns, values)
        except Exception as e:
            return render_template('invalid.html', e=str(e))
        tables = [nested_list_to_html_table(t) for t in tables]
        return render_template('insert_results.html', tables=tables, table_name=table_name)
    elif request.method == 'POST' and 'delete_button' in request.form:
        values = request.form['delete_button'].split(',')
        values = [val if val.isnumeric() else "\'" + val + "\'" for val in values]
        columns = select_with_headers(mysql, table_name)[0]
        where = []
        for col, val in zip(columns, values):
            where.append(col + " = " + val)
        where = " AND ".join(where)
        try:
            tables = delete_from_table(mysql, table_name, where)
        except Exception as e:
            return render_template('invalid.html', e=str(e))
        tables = [nested_list_to_html_table(t) for t in tables]
        return render_template('delete_results.html', tables=tables, table_name=table_name)
    elif request.method == 'POST' and 'update_button' in request.form:
        operation = 'update'
        table = nested_list_to_html_table(select_with_headers(mysql, table_name), buttons=True)
        values = request.form['update_button'].split(',')
        form_html = get_update_form(select_with_headers(mysql, table_name)[0], values)
        values = [val if val.isnumeric() else "\'" + val + "\'" for val in values]
        columns = select_with_headers(mysql, table_name)[0]
        where = []
        for col, val in zip(columns, values):
            where.append(col + " = " + val)
        where = " AND ".join(where)
        session['update_where'] = where
        return render_template('edit.html', table=table, table_name=table_name, operation=operation, form_html=form_html)
    elif request.method == 'POST' and 'update_execute' in request.form:
        columns = select_with_headers(mysql, table_name)[0]
        values = []
        for col in columns:
            val = request.form[col]
            if val.isnumeric():
                values.append(val)
            else:
                values.append("\'" + val + "\'")
        
        set_statement = []
        for col, val in zip(columns, values):
            set_statement.append(col + " = " + val)
        set_statement = ", ".join(set_statement)

        try:
            tables = update_table(mysql, table_name, set_statement, session['update_where'])
        except Exception as e:
            return render_template('invalid.html', e=str(e))
        tables = [nested_list_to_html_table(t) for t in tables]
        if session.get('update_where'):
            session.pop('update_where', None)
        return render_template('update_results.html', tables=tables, table_name=table_name)


    table = nested_list_to_html_table(select_with_headers(mysql, table_name), buttons=True)
    return render_template('edit.html', table=table, table_name=table_name, operation=operation, form_html=form_html)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Secure admin login: verify username/password against admin table using
    # parameterized queries and password hashing to prevent SQL injection.
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        if not username or not password:
            return render_template('login.html', error='請輸入使用者名稱與密碼')

        try:
            cur = mysql.connection.cursor()
            # parameterized query prevents SQL injection
            cur.execute("SELECT password_hash FROM admin WHERE username = %s", (username,))
            row = cur.fetchone()
            cur.close()

            if not row:
                return render_template('login.html', error='使用者不存在')

            # row may be a dict (DictCursor) or tuple
            pwd_hash = None
            if isinstance(row, dict):
                pwd_hash = row.get('password_hash')
            else:
                pwd_hash = row[0]

            if pwd_hash and check_password_hash(pwd_hash, password):
                session['staff_logged_in'] = True
                session['staff_user'] = username
                session.permanent = True
                app.permanent_session_lifetime = 3600  # 1小時（3600秒）= 可自行調整
                return redirect(url_for('pick_table'))
            else:
                return render_template('login.html', error='帳號或密碼錯誤')

        except Exception as e:
            return render_template('login.html', error=f'登入失敗：{repr(e)}')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/ping")
def ping():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DATABASE();")
    dbname = cur.fetchone()[0]
    cur.close()
    return {"ok": True, "db": dbname}


@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    # Appointment page: on POST create appointment (create patient if name given)
    if request.method == 'POST':
        patient_input = (request.form.get('patientID') or '').strip()
        patient_name = (request.form.get('patientName') or '').strip()
        staff_id = (request.form.get('staffID') or '').strip()
        atime = (request.form.get('appointmentTime') or '').strip()

        try:
            cur = mysql.connection.cursor()

            # Resolve patient: patient_input is expected to be national ID (e.g. F123456789)
            # Ensure patient table has a national_id column (create if missing)
            patient_id = None
            nid = patient_input
            # basic server-side validation for national id format
            import re
            nid_re = re.compile(r'^[A-Z][0-9]{9}$')
            if not nid or not nid_re.match(nid):
                cur.close()
                return render_template('appointment.html', submitted=True, error='病患身份證格式錯誤', patient=patient_input, staff=staff_id, atime=atime)

            try:
                cur.execute("SELECT patientID FROM patient WHERE national_id = %s", (nid,))
                row = cur.fetchone()
            except Exception as e:
                # If the column doesn't exist, add it (non-unique to avoid ALTER failures)
                msg = str(e)
                if 'Unknown column' in msg or '1054' in msg:
                    try:
                        cur.execute("ALTER TABLE patient ADD COLUMN national_id VARCHAR(20)")
                        mysql.connection.commit()
                    except Exception:
                        pass
                    # retry select
                    try:
                        cur.execute("SELECT patientID FROM patient WHERE national_id = %s", (nid,))
                        row = cur.fetchone()
                    except Exception:
                        row = None
                else:
                    raise

            if row:
                # dict cursor or tuple
                if isinstance(row, dict):
                    patient_id = row.get('patientID')
                else:
                    patient_id = row[0]
            else:
                # create new patient with name + national id
                cur.execute("INSERT INTO patient (name, national_id) VALUES (%s, %s)", (patient_name or None, nid))
                mysql.connection.commit()
                patient_id = cur.lastrowid

            # staff_id must be numeric
            staff_id_int = int(staff_id) if staff_id.isnumeric() else None

            if not patient_id or not staff_id_int or not atime:
                cur.close()
                return render_template('appointment.html', submitted=True, error='請提供有效的病患、醫師與時間.', patient=patient_input, staff=staff_id, atime=atime)

            # Prevent duplicate booking: same patient (national id) cannot book the same session twice
            # Determine session window based on appointment time
            try:
                parts = atime.split(' ')
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else ''
            except Exception:
                date_part = ''
                time_part = ''

            SESSIONS = [
                ('09:00:00','12:00:00'),
                ('15:00:00','18:00:00'),
                ('19:00:00','21:00:00')
            ]
            session_start = None
            session_end = None
            for s,e in SESSIONS:
                if time_part == s:
                    session_start = f"{date_part} {s}"
                    session_end = f"{date_part} {e}"
                    break

            if session_start and session_end:
                cur.execute("SELECT COUNT(*) FROM appointment WHERE patientID = %s AND appointmentTime >= %s AND appointmentTime < %s", (patient_id, session_start, session_end))
                dup_row = cur.fetchone()
                dup_count = 0
                if isinstance(dup_row, dict):
                    dup_count = next(iter(dup_row.values()))
                else:
                    dup_count = dup_row[0] if dup_row else 0
                if dup_count > 0:
                    cur.close()
                    return render_template('appointment.html', submitted=True, error='同一身分證已在此時段預約過', patient=patient_input, staff=staff_id, atime=atime)

            # Reservation capacity check (prevent exceeding per-slot capacity)
            CAPACITY = 60
            cur.execute("SELECT COUNT(*) FROM appointment WHERE staffID = %s AND appointmentTime = %s", (staff_id_int, atime))
            cnt_row = cur.fetchone()
            # support dict or tuple result
            cur_count = None
            if isinstance(cnt_row, dict):
                cur_count = next(iter(cnt_row.values()))
            else:
                cur_count = cnt_row[0] if cnt_row else 0

            if cur_count >= CAPACITY:
                cur.close()
                return render_template('appointment.html', submitted=True, error=f'此時段已額滿（{cur_count}/{CAPACITY}）', patient=patient_input, staff=staff_id, atime=atime)

            # Insert appointment
            cur.execute("INSERT INTO appointment (patientID, staffID, appointmentTime, status) VALUES (%s,%s,%s,%s)",
                        (patient_id, staff_id_int, atime, 'booked'))
            mysql.connection.commit()
            cur.close()
            return render_template('appointment.html', submitted=True, patient=patient_id, staff=staff_id_int, atime=atime, success=True)
        except Exception as e:
            return render_template('appointment.html', submitted=True, error=str(e), patient=patient_input, staff=staff_id, atime=atime)

    return render_template('appointment.html', submitted=False)


@app.route('/api/appointments')
def api_appointments():
    # Expects start and end query params (YYYY-MM-DD)
    start = request.args.get('start')
    end = request.args.get('end')
    try:
        cur = mysql.connection.cursor()
        if start and end:
            cur.execute("SELECT appointmentID, patientID, staffID, appointmentTime, status FROM appointment WHERE appointmentTime >= %s AND appointmentTime < %s", (start, end))
        else:
            cur.execute("SELECT appointmentID, patientID, staffID, appointmentTime, status FROM appointment")
        rows = cur.fetchall()
        cur.close()

        # Convert rows to list of dicts (handles dictcursor or tuple)
        appts = []
        for r in rows:
            if isinstance(r, dict):
                # ensure appointmentTime is a string
                item = dict(r)
                if 'appointmentTime' in item and item['appointmentTime'] is not None:
                    item['appointmentTime'] = str(item['appointmentTime'])
                appts.append(item)
            else:
                appts.append({
                    'appointmentID': r[0], 'patientID': r[1], 'staffID': r[2], 'appointmentTime': str(r[3]), 'status': r[4]
                })
        return { 'appointments': appts }
    except Exception as e:
        return { 'error': str(e) }


@app.route('/api/staff')
def api_staff():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT staffID, name, role FROM staff")
        rows = cur.fetchall()
        cur.close()
        staff = []
        for r in rows:
            if isinstance(r, dict):
                staff.append(r)
            else:
                staff.append({'staffID': r[0], 'name': r[1], 'role': r[2]})
        return {'staff': staff}
    except Exception as e:
        return {'error': str(e)}


@app.route('/init_staff')
def init_staff():
    """Create two sample doctors if they don't exist. Safe to call multiple times."""
    try:
        cur = mysql.connection.cursor()
        # check by name
        names = ['Dr. Chen', 'Dr. Lin']
        created = []
        for n in names:
            cur.execute("SELECT staffID FROM staff WHERE name = %s", (n,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO staff (name, role) VALUES (%s,%s)", (n, 'Physician'))
                mysql.connection.commit()
                created.append(n)
        cur.close()
        return { 'created': created }
    except Exception as e:
        return { 'error': str(e) }

@app.route("/debug/tables")
def debug_tables():
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES;")
    rows = cur.fetchall()
    cur.close()
    # rows 可能是 [{'Tables_in_hospitalDB':'patients'}, ...] 或 [('patients',), ...]
    if rows and isinstance(rows[0], dict):
        tables = [list(r.values())[0] for r in rows]
    else:
        tables = [r[0] for r in rows]
    return {"tables": tables}

# def ping():
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT DATABASE();")
#     dbname = cur.fetchone()[0]
#     cur.close()
#     return {"ok": True, "db": dbname}



if __name__ == '__main__':
    app.run()