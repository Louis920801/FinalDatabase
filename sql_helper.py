import MySQLdb

def convert(raw_out, type):
    """
    Converts the format returned by cursor.fetchall() to something more palatable for the user
    """
    res = []

    if type == "col_names":
        res.append(['Columns in the table'])
        for col_name in raw_out:
            res.append([col_name['COLUMN_NAME']])

    if type == "show":
        res.append(['Tables in the database'])
        for t in raw_out:
            res.append(list(t.values()))

    if type == "desc":
        # ✅ 避免空表時 raw_out[0] 噴錯
        if not raw_out:
            return [['Field', 'Type', 'Null', 'Key', 'Default', 'Extra']]
        res.append(list(raw_out[0].keys()))
        for t in raw_out:
            res.append(list(t.values()))

    if type == "select":
        # ✅ 避免空表時 raw_out[0] 噴錯
        if not raw_out:
            return [[]]
        res.append(list(raw_out[0].keys()))
        for t in raw_out:
            res.append(list(t.values()))

    return res


def col_names(mysql, tablename, db_name="hospitalDB"):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s",
        (db_name, tablename,)
    )
    res = cursor.fetchall()
    res = convert(res, "col_names")
    cursor.close()
    return res


def list_to_string(list_):
    corr_str = ",".join(str(x) for x in list_)
    corr_str = "(" + corr_str + ")"
    return corr_str


def use_database(mysql, db_name='hospitalDB'):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("USE %s", (db_name,))
    cursor.fetchall()
    cursor.close()


def show_tables(mysql):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SHOW TABLES;")
    rows = cursor.fetchall()
    cursor.close()
    return [list(r.values())[0] for r in rows]


def desc_table(mysql, tablename):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DESC " + tablename)
    res = cursor.fetchall()
    res = convert(res, "desc")
    cursor.close()
    return res


def select_with_headers(mysql, table_name, limit=100):
    """
    讀取 table 資料並回傳 [headers] + rows
    ✅ patient 表：預設隱藏 is_deleted = 1 的資料（若欄位存在）
    """
    cur = mysql.connection.cursor()

    # 先拿欄位資訊
    cur.execute(f"SELECT * FROM `{table_name}` LIMIT 0")
    desc = cur.description or []
    headers = [d[0] for d in desc]

    out = [headers]

    # patient 表：若有 is_deleted 欄位，就只顯示 is_deleted=0
    if table_name == "patient" and "is_deleted" in headers:
        sql = f"SELECT * FROM `{table_name}` WHERE is_deleted = 0 LIMIT %s"
        cur.execute(sql, (limit,))
    else:
        sql = f"SELECT * FROM `{table_name}` LIMIT %s"
        cur.execute(sql, (limit,))

    rows = cur.fetchall()

    if rows:
        first = rows[0]
        if isinstance(first, dict):
            for r in rows:
                out.append([r.get(h) for h in headers])
        else:
            for r in rows:
                out.append(list(r))

    cur.close()
    return out


def insert_to_table(mysql, tablename, columnlist, val_list):
    res1 = select_with_headers(mysql, tablename)  # before
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cols_string = list_to_string(columnlist)
    vals_string = list_to_string(val_list)

    cursor.execute("INSERT INTO " + tablename + " " + cols_string + " VALUES " + vals_string)
    mysql.connection.commit()
    cursor.fetchall()
    cursor.close()

    res2 = select_with_headers(mysql, tablename)  # after
    return res1, res2


def delete_from_table(mysql, tablename, where_condition):
    """
    ✅ 其他表：真的 DELETE
    ✅ patient 表：soft delete -> UPDATE patient SET is_deleted=1
       （避免 appointment 外鍵 RESTRICT 擋住）
    """
    res1 = select_with_headers(mysql, tablename)  # before
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 確保 patient 有 is_deleted 欄位（沒有就自動補上）
    if tablename == "patient":
        try:
            cursor.execute("SHOW COLUMNS FROM patient LIKE 'is_deleted';")
            has_col = cursor.fetchone()
            if not has_col:
                cursor.execute("ALTER TABLE patient ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;")
                mysql.connection.commit()
        except Exception:
            # 如果 ALTER 失敗就算了（可能權限不足）
            pass

        sql = "UPDATE patient SET is_deleted = 1 WHERE " + where_condition
    else:
        sql = "DELETE FROM " + tablename + " WHERE " + where_condition

    cursor.execute(sql)
    mysql.connection.commit()
    cursor.fetchall()
    cursor.close()

    res2 = select_with_headers(mysql, tablename)  # after
    return res1, res2


def update_table(mysql, tablename, set_statement, where_condition):
    res1 = select_with_headers(mysql, tablename)  # before
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("UPDATE " + tablename + " SET " + set_statement + " WHERE " + where_condition)
    mysql.connection.commit()
    cursor.fetchall()
    cursor.close()

    res2 = select_with_headers(mysql, tablename)  # after
    return res1, res2
