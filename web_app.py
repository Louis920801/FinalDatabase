from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from sql_helper import *
from html_helper import *

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
        return redirect(url_for('pick_table'))
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
    DB_NAME = "hospitalDB"

    try:
        cur = mysql.connection.cursor()

        # 目前連到哪個 DB（相容 tuple / dict）
        cur.execute("SELECT DATABASE()")
        row = cur.fetchone()
        if isinstance(row, dict):
            db = next(iter(row.values()), None)
        else:
            db = row[0] if row else None

        if not db:
            cur.execute(f"USE `{DB_NAME}`")

        # 用 FROM 指定 DB，避免預設庫問題
        cur.execute(f"SHOW TABLES FROM `{DB_NAME}`")
        rows = cur.fetchall()
        cur.close()

        # rows 可能是 [("patient",), ...] 或 [{"Tables_in_hospitalDB":"patient"}, ...]
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
        # 把真正錯誤丟到 invalid.html
        code = None
        msg = repr(e)
        if getattr(e, "args", None):
            code = e.args[0]
            if len(e.args) > 1 and e.args[1]:
                msg = e.args[1]
        return render_template("invalid.html", e=f"MySQL error code={code}, message={msg}")

    # POST：Describe / Pick
    if request.method == "POST":
        table_name = (request.form.get("table") or "").strip()

        if "describe" in request.form and table_name:
            try:
                cur = mysql.connection.cursor()
                cur.execute(f"DESCRIBE `{DB_NAME}`.`{table_name}`")
                desc_rows = cur.fetchall()
                cur.close()

                # 規格化成 list[tuple] 給模板畫表
                normalized = []
                for r in desc_rows:
                    if isinstance(r, dict):
                        normalized.append((
                            r.get("Field"), r.get("Type"), r.get("Null"),
                            r.get("Key"), r.get("Default"), r.get("Extra")
                        ))
                    else:
                        normalized.append(tuple(r))
                return render_template(
                    "pick_table.html",
                    tables=tables,
                    table_name=table_name,
                    table=normalized
                )
            except Exception as e:
                return render_template("invalid.html", e=f"DESCRIBE 失敗：{repr(e)}")

        if "pick" in request.form and table_name:
            session["table_name"] = table_name   # 正確賦值
            session.modified = True
            return redirect(url_for("edit"))

    # GET 初始頁
    return render_template(
        "pick_table.html",
        tables=tables,
        table_name="",
        table=None
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

@app.route("/ping")
def ping():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DATABASE();")
    dbname = cur.fetchone()[0]
    cur.close()
    return {"ok": True, "db": dbname}

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