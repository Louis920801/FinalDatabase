from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from sql_helper import *
from html_helper import *
from werkzeug.security import check_password_hash

from functools import wraps
from flask import abort

DEMO_KEY = "406"  # 你自己改成不容易猜的

def require_demo_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.args.get("key", "")
        if key != DEMO_KEY:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper

app = Flask(__name__)
app.secret_key = 'mango'
app.debug = True

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'tempuser'
app.config['MYSQL_PASSWORD'] = '123+Temppass'
app.config['MYSQL_DB'] = 'hospitalDB'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
print("== USING MySQL DB:", app.config['MYSQL_DB'], "on port", app.config['MYSQL_PORT'])

@app.route("/", methods=["GET"])
def index():
    return render_template('index.html')

print(">>> THIS IS web_app.py <<<")

@app.route('/', methods=['POST'])
def choose():
    if request.form.get("start"):
        return redirect(url_for('login'))
    else:
        return render_template('index.html')


# -----------------------------
# SQL 組字串用的小工具（修 None/NULL 問題）
# -----------------------------

def _escape_sql_string(s: str) -> str:
    # 最基本 escape：避免單引號炸掉 SQL
    # 你目前是用字串拼 SQL，所以至少要做這個
    return s.replace("\\", "\\\\").replace("'", "\\'")

def sql_value_literal(raw_val: str) -> str:
    """
    回傳可直接塞進 INSERT/UPDATE 的 value literal：
    - 空/None -> NULL（不加引號）
    - 純數字 -> 123
    - 其他 -> 'text'（會 escape）
    """
    val = (raw_val or "").strip()

    if val == "" or val.lower() == "none":
        return "NULL"
    if val.isnumeric():
        return val
    return "'" + _escape_sql_string(val) + "'"

def sql_where_predicate(col: str, raw_val: str) -> str:
    """
    回傳一個 WHERE 條件：
    - 空/None -> `col IS NULL`
    - 其他 -> `col = <literal>`
    """
    lit = sql_value_literal(raw_val)
    if lit == "NULL":
        return f"{col} IS NULL"
    return f"{col} = {lit}"


@app.route("/pick_table", methods=["GET", "POST"])
def pick_table():
    if not session.get('staff_logged_in'):
        return redirect(url_for('login'))

    DB_NAME = "hospitalDB"
    table_name = ""
    table_description = None

    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT DATABASE()")
        row = cur.fetchone()
        if isinstance(row, dict):
            db = next(iter(row.values()), None)
        else:
            db = row[0] if row else None

        if not db:
            cur.execute(f"USE `{DB_NAME}`")

        cur.execute(f"SHOW TABLES FROM `{DB_NAME}`")
        rows = cur.fetchall()
        cur.close()

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
        code = None
        msg = repr(e)
        if getattr(e, "args", None):
            code = e.args[0]
            if len(e.args) > 1 and e.args[1]:
                msg = e.args[1]
        return render_template("invalid.html", e=f"MySQL error code={code}, message={msg}")

    if request.method == "POST":
        selected_table = (request.form.get("table") or "").strip()
        table_name = selected_table

        if "describe" in request.form and selected_table:
            try:
                cur = mysql.connection.cursor()
                cur.execute(f"DESCRIBE `{DB_NAME}`.`{selected_table}`")
                desc_rows = cur.fetchall()
                cur.close()

                if desc_rows:
                    if isinstance(desc_rows[0], dict):
                        table_description = desc_rows
                    else:
                        keys = ["Field", "Type", "Null", "Key", "Default", "Extra"]
                        table_description = [dict(zip(keys, row)) for row in desc_rows]

                return render_template(
                    "pick_table.html",
                    tables=tables,
                    table_name=table_name,
                    table_description=table_description
                )
            except Exception as e:
                return render_template("invalid.html", e=f"DESCRIBE 失敗：{repr(e)}")

        if "pick" in request.form and selected_table:
            session["table_name"] = selected_table
            session.modified = True
            return redirect(url_for("edit"))

    return render_template(
        "pick_table.html",
        tables=tables,
        table_name=table_name,
        table_description=table_description
    )


@app.route("/sql_console", methods=["POST"])
def sql_console():
    if not session.get('staff_logged_in'):
        return jsonify({"error": "尚未登入，請先登入後再使用 SQL 終端機"})

    data = request.get_json() or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Empty query"})

    try:
        cur = mysql.connection.cursor()
        cur.execute(query)

        if cur.description:
            rows = cur.fetchall()
            if rows and isinstance(rows[0], dict):
                columns = list(rows[0].keys())
                row_list = [[r.get(col) for col in columns] for r in rows]
            else:
                columns = [col[0] for col in cur.description]
                row_list = [list(r) for r in rows]

            cur.close()
            return jsonify({"columns": columns, "rows": row_list})

        else:
            mysql.connection.commit()
            affected = cur.rowcount
            cur.close()
            return jsonify({"columns": ["info"], "rows": [[f"{affected} rows affected"]]})

    except Exception as e:
        return jsonify({"error": str(e)})


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

        # ✅ 修正：空值/None -> NULL，文字加引號，數字不加
        values = [sql_value_literal(request.form.get(col)) for col in columns]

        try:
            tables = insert_to_table(mysql, table_name, columns, values)
        except Exception as e:
            return render_template('invalid.html', e=str(e))

        tables = [nested_list_to_html_table(t) for t in tables]
        return render_template('insert_results.html', tables=tables, table_name=table_name)

    elif request.method == 'POST' and 'delete_button' in request.form:
        # delete_button 內是一整列的值，用逗號拆
        row_vals = request.form['delete_button'].split(',')
        columns = select_with_headers(mysql, table_name)[0]

        # ✅ 修正：遇到 None/空值 -> 用 IS NULL
        where_list = []
        for col, raw in zip(columns, row_vals):
            where_list.append(sql_where_predicate(col, raw))
        where = " AND ".join(where_list)

        try:
            tables = delete_from_table(mysql, table_name, where)
        except Exception as e:
            return render_template('invalid.html', e=str(e))

        tables = [nested_list_to_html_table(t) for t in tables]
        return render_template('delete_results.html', tables=tables, table_name=table_name)

    elif request.method == 'POST' and 'update_button' in request.form:
        operation = 'update'
        table = nested_list_to_html_table(select_with_headers(mysql, table_name), buttons=True)

        row_vals = request.form['update_button'].split(',')
        form_html = get_update_form(select_with_headers(mysql, table_name)[0], row_vals)

        columns = select_with_headers(mysql, table_name)[0]

        # ✅ 修正：update 的 WHERE 也要支援 NULL（IS NULL）
        where_list = []
        for col, raw in zip(columns, row_vals):
            where_list.append(sql_where_predicate(col, raw))
        where = " AND ".join(where_list)

        session['update_where'] = where
        return render_template('edit.html', table=table, table_name=table_name, operation=operation, form_html=form_html)

    elif request.method == 'POST' and 'update_execute' in request.form:
        columns = select_with_headers(mysql, table_name)[0]

        # ✅ 修正：SET 的值也要支援 NULL
        values = [sql_value_literal(request.form.get(col)) for col in columns]

        set_statement = []
        for col, lit in zip(columns, values):
            set_statement.append(f"{col} = {lit}")
        set_statement = ", ".join(set_statement)

        try:
            tables = update_table(mysql, table_name, set_statement, session.get('update_where', ''))
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
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        if not username or not password:
            return render_template('login.html', error='請輸入使用者名稱與密碼')

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT password_hash FROM admin WHERE username = %s", (username,))
            row = cur.fetchone()
            cur.close()

            if not row:
                return render_template('login.html', error='使用者不存在')

            pwd_hash = row.get('password_hash') if isinstance(row, dict) else row[0]

            if pwd_hash and check_password_hash(pwd_hash, password):
                session['staff_logged_in'] = True
                session['staff_user'] = username
                session.permanent = True
                app.permanent_session_lifetime = 3600
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
    row = cur.fetchone()
    dbname = row.get(next(iter(row.keys()))) if isinstance(row, dict) else row[0]
    cur.close()
    return {"ok": True, "db": dbname}


@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        patient_input = (request.form.get('patientID') or '').strip()
        patient_name = (request.form.get('patientName') or '').strip()
        staff_id = (request.form.get('staffID') or '').strip()
        atime = (request.form.get('appointmentTime') or '').strip()

        try:
            cur = mysql.connection.cursor()

            patient_id = None
            nid = patient_input
            import re
            nid_re = re.compile(r'^[A-Z][0-9]{9}$')
            if not nid or not nid_re.match(nid):
                cur.close()
                return render_template('appointment.html', submitted=True, error='病患身份證格式錯誤', patient=patient_input, staff=staff_id, atime=atime)

            try:
                cur.execute("SELECT patientID FROM patient WHERE national_id = %s", (nid,))
                row = cur.fetchone()
            except Exception as e:
                msg = str(e)
                if 'Unknown column' in msg or '1054' in msg:
                    try:
                        cur.execute("ALTER TABLE patient ADD COLUMN national_id VARCHAR(20)")
                        mysql.connection.commit()
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT patientID FROM patient WHERE national_id = %s", (nid,))
                        row = cur.fetchone()
                    except Exception:
                        row = None
                else:
                    raise

            if row:
                patient_id = row.get('patientID') if isinstance(row, dict) else row[0]
            else:
                cur.execute("INSERT INTO patient (name, national_id) VALUES (%s, %s)", (patient_name or None, nid))
                mysql.connection.commit()
                patient_id = cur.lastrowid

            staff_id_int = int(staff_id) if staff_id.isnumeric() else None

            if not patient_id or not staff_id_int or not atime:
                cur.close()
                return render_template('appointment.html', submitted=True, error='請提供有效的病患、醫師與時間.', patient=patient_input, staff=staff_id, atime=atime)

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
            for s, e in SESSIONS:
                if time_part == s:
                    session_start = f"{date_part} {s}"
                    session_end = f"{date_part} {e}"
                    break

            if session_start and session_end:
                cur.execute(
                    "SELECT COUNT(*) FROM appointment WHERE patientID = %s AND appointmentTime >= %s AND appointmentTime < %s",
                    (patient_id, session_start, session_end)
                )
                dup_row = cur.fetchone()
                dup_count = next(iter(dup_row.values())) if isinstance(dup_row, dict) else (dup_row[0] if dup_row else 0)
                if dup_count > 0:
                    cur.close()
                    return render_template('appointment.html', submitted=True, error='同一身分證已在此時段預約過', patient=patient_input, staff=staff_id, atime=atime)

            CAPACITY = 60
            cur.execute("SELECT COUNT(*) FROM appointment WHERE staffID = %s AND appointmentTime = %s", (staff_id_int, atime))
            cnt_row = cur.fetchone()
            cur_count = next(iter(cnt_row.values())) if isinstance(cnt_row, dict) else (cnt_row[0] if cnt_row else 0)

            if cur_count >= CAPACITY:
                cur.close()
                return render_template('appointment.html', submitted=True, error=f'此時段已額滿（{cur_count}/{CAPACITY}）', patient=patient_input, staff=staff_id, atime=atime)

            cur.execute(
                "INSERT INTO appointment (patientID, staffID, appointmentTime, status) VALUES (%s,%s,%s,%s)",
                (patient_id, staff_id_int, atime, 'booked')
            )
            mysql.connection.commit()
            cur.close()
            return render_template('appointment.html', submitted=True, patient=patient_id, staff=staff_id_int, atime=atime, success=True)

        except Exception as e:
            return render_template('appointment.html', submitted=True, error=str(e), patient=patient_input, staff=staff_id, atime=atime)

    return render_template('appointment.html', submitted=False)


@app.route('/api/appointments')
def api_appointments():
    start = request.args.get('start')
    end = request.args.get('end')
    try:
        cur = mysql.connection.cursor()
        if start and end:
            cur.execute(
                "SELECT appointmentID, patientID, staffID, appointmentTime, status FROM appointment WHERE appointmentTime >= %s AND appointmentTime < %s",
                (start, end)
            )
        else:
            cur.execute("SELECT appointmentID, patientID, staffID, appointmentTime, status FROM appointment")

        rows = cur.fetchall()
        cur.close()

        appts = []
        for r in rows:
            if isinstance(r, dict):
                item = dict(r)
                if 'appointmentTime' in item and item['appointmentTime'] is not None:
                    item['appointmentTime'] = str(item['appointmentTime'])
                appts.append(item)
            else:
                appts.append({
                    'appointmentID': r[0], 'patientID': r[1], 'staffID': r[2],
                    'appointmentTime': str(r[3]), 'status': r[4]
                })
        return {'appointments': appts}
    except Exception as e:
        return {'error': str(e)}


@app.route('/api/staff')
@require_demo_key
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
    try:
        cur = mysql.connection.cursor()
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
        return {'created': created}
    except Exception as e:
        return {'error': str(e)}


@app.route("/debug/tables")
def debug_tables():
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES;")
    rows = cur.fetchall()
    cur.close()
    if rows and isinstance(rows[0], dict):
        tables = [list(r.values())[0] for r in rows]
    else:
        tables = [r[0] for r in rows]
    return {"tables": tables}


print("=== URL MAP ===")
print(app.url_map)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
