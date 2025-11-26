"""
create_admin.py

Small helper script to create the `admin` table (if missing) and insert one admin user
with a hashed password. Uses parameterized queries to avoid SQL injection.

Usage:
  python create_admin.py

It will prompt for DB credentials (press Enter to use defaults from web_app.py),
then prompt for username and password.

Requires: pymysql
  pip install pymysql
"""
import getpass
import pymysql
from werkzeug.security import generate_password_hash

# Defaults mirror web_app.py
DEFAULTS = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'tempuser',
    'password': '123+Temppass',
    'db': 'hospitalDB'
}

def prompt(prompt_text, default=None):
    v = input(f"{prompt_text} [{default}]: ")
    return v.strip() or default


def main():
    host = prompt('MySQL host', DEFAULTS['host'])
    port = int(prompt('MySQL port', DEFAULTS['port']))
    user = prompt('MySQL user', DEFAULTS['user'])
    pwd = getpass.getpass('MySQL password (leave blank to use default): ') or DEFAULTS['password']
    db = prompt('Database name', DEFAULTS['db'])

    print('\nNow enter the admin account to create:')
    admin_user = input('admin username: ').strip()
    if not admin_user:
        print('username required, aborting')
        return
    admin_pwd = getpass.getpass('admin password: ').strip()
    if not admin_pwd:
        print('password required, aborting')
        return

    pwd_hash = generate_password_hash(admin_pwd)

    conn = pymysql.connect(host=host, port=port, user=user, password=pwd, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # create admin table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    adminID INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # insert or replace admin user
            cur.execute("SELECT adminID FROM admin WHERE username = %s", (admin_user,))
            existing = cur.fetchone()
            if existing:
                print('A user with that username already exists. Updating password...')
                cur.execute("UPDATE admin SET password_hash = %s WHERE username = %s", (pwd_hash, admin_user))
            else:
                cur.execute("INSERT INTO admin (username, password_hash) VALUES (%s, %s)", (admin_user, pwd_hash))

        conn.commit()
        print('Admin user created/updated successfully.')
    finally:
        conn.close()

if __name__ == '__main__':
    main()
