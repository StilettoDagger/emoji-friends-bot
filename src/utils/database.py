import sqlite3

def init_db():
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    
    # User emojis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_emojis (
            user_id INTEGER PRIMARY KEY,
            emoji TEXT NOT NULL,
            text TEXT
        )
    ''')

    # Migration: Add 'text' column if it doesn't exist
    cursor.execute("PRAGMA table_info(user_emojis)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'text' not in columns:
        cursor.execute("ALTER TABLE user_emojis ADD COLUMN text TEXT")
        
    # Migration: Add 'preferred_theme' column if it doesn't exist
    if 'preferred_theme' not in columns:
        cursor.execute("ALTER TABLE user_emojis ADD COLUMN preferred_theme TEXT DEFAULT 'default'")
    
    # VC settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vc_settings (
            channel_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def set_user_status(user_id, emoji, text):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    if emoji is None:
        cursor.execute('DELETE FROM user_emojis WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('''
            INSERT INTO user_emojis (user_id, emoji, text) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                emoji=excluded.emoji,
                text=excluded.text
        ''', (user_id, emoji, text))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT emoji, text FROM user_emojis WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else (None, None)

def set_user_theme(user_id, theme_name):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_emojis (user_id, emoji, text, preferred_theme) 
        VALUES (?, '❓', NULL, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            preferred_theme=excluded.preferred_theme
    ''', (user_id, theme_name))
    conn.commit()
    conn.close()

def get_user_theme(user_id):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT preferred_theme FROM user_emojis WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else 'default'

def get_all_user_ids():
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM user_emojis')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def toggle_vc_status(channel_id):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT enabled FROM vc_settings WHERE channel_id = ?', (channel_id,))
    row = cursor.fetchone()
    
    new_status = 0 if row and row[0] == 1 else 1
    cursor.execute('INSERT OR REPLACE INTO vc_settings (channel_id, enabled) VALUES (?, ?)', (channel_id, new_status))
    
    conn.commit()
    conn.close()
    return bool(new_status)

def is_vc_enabled(channel_id):
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT enabled FROM vc_settings WHERE channel_id = ?', (channel_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else False
