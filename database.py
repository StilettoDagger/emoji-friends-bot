import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # User emojis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_emojis (
            user_id INTEGER PRIMARY KEY,
            emoji TEXT NOT NULL
        )
    ''')
    
    # VC settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vc_settings (
            channel_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def set_user_emoji(user_id, emoji):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if emoji is None:
        cursor.execute('DELETE FROM user_emojis WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('INSERT OR REPLACE INTO user_emojis (user_id, emoji) VALUES (?, ?)', (user_id, emoji))
    conn.commit()
    conn.close()

def get_user_emoji(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT emoji FROM user_emojis WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_user_ids():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM user_emojis')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def toggle_vc_status(channel_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT enabled FROM vc_settings WHERE channel_id = ?', (channel_id,))
    row = cursor.fetchone()
    
    new_status = 0 if row and row[0] == 1 else 1
    cursor.execute('INSERT OR REPLACE INTO vc_settings (channel_id, enabled) VALUES (?, ?)', (channel_id, new_status))
    
    conn.commit()
    conn.close()
    return bool(new_status)

def is_vc_enabled(channel_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT enabled FROM vc_settings WHERE channel_id = ?', (channel_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else False
