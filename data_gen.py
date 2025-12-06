import sqlite3
import random
import datetime
from datetime import timedelta

DB_NAME = "social_media_logs.db"

def create_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            is_bot BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            upload_date TIMESTAMP NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
    ''')
    conn.commit()

def generate_organic_data(conn):
    cursor = conn.cursor()
    
    # 1. Create Users (Organic)
    print("Generating organic users...")
    start_date = datetime.datetime.now() - timedelta(days=730) # 2 years ago
    users = []
    for i in range(100):
        created_at = start_date + timedelta(days=random.randint(0, 700))
        users.append((f"user_{i}", created_at, False))
    
    cursor.executemany("INSERT INTO users (username, created_at, is_bot) VALUES (?, ?, ?)", users)
    
    # 2. Create Videos
    print("Generating videos...")
    videos = []
    for i in range(50):
        upload_date = start_date + timedelta(days=random.randint(0, 600))
        videos.append((f"Video Title {i}", upload_date))
    
    cursor.executemany("INSERT INTO videos (title, upload_date) VALUES (?, ?)", videos)
    
    # 3. Generate Organic Likes
    print("Generating organic likes...")
    cursor.execute("SELECT id, created_at FROM users WHERE is_bot = 0")
    user_rows = cursor.fetchall()
    cursor.execute("SELECT id, upload_date FROM videos")
    video_rows = cursor.fetchall()
    
    likes = []
    for u_id, u_created in user_rows:
        # Each organic user likes 5-20 videos
        num_likes = random.randint(5, 20)
        u_created_dt = datetime.datetime.fromisoformat(str(u_created))
        
        for _ in range(num_likes):
            v_id, v_upload = random.choice(video_rows)
            v_upload_dt = datetime.datetime.fromisoformat(str(v_upload))
            
            # Like must be after user creation and video upload
            min_time = max(u_created_dt, v_upload_dt)
            if min_time > datetime.datetime.now(): continue
            
            # Simple random time between min_time and now
            delta_seconds = int((datetime.datetime.now() - min_time).total_seconds())
            if delta_seconds <= 0: continue
            
            like_time = min_time + timedelta(seconds=random.randint(0, delta_seconds))
            likes.append((u_id, v_id, like_time))
            
    cursor.executemany("INSERT INTO likes (user_id, video_id, timestamp) VALUES (?, ?, ?)", likes)
    conn.commit()

def generate_bot_attack(conn):
    cursor = conn.cursor()
    print("Generating bot attack...")
    
    target_video_id = 20
    # Attack time: Yesterday at 14:00
    yesterday_1400 = (datetime.datetime.now() - timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    
    # Ensure video 20 exists with a compatible upload date, or update it
    # We'll just update video 20 to exist and be uploaded before attack
    cursor.execute("INSERT OR IGNORE INTO videos (id, title, upload_date) VALUES (20, 'Target Video', ?)", 
                   (yesterday_1400 - timedelta(days=10),))
    # If it existed, update upload date to be safe
    cursor.execute("UPDATE videos SET upload_date = ? WHERE id = 20", (yesterday_1400 - timedelta(days=10),))

    bots = []
    bot_likes = []
    
    # 1. Fresh Bots (< 24h old)
    # Created shortly before attack
    for i in range(100): # 100 Fresh bots
        created_at = yesterday_1400 - timedelta(hours=random.randint(1, 12))
        bots.append((f"fresh_bot_{i}", created_at, True))
    
    # 2. Sleeper Bots (> 3 months old)
    for i in range(50): # 50 Sleeper bots
        created_at = yesterday_1400 - timedelta(days=random.randint(100, 300))
        bots.append((f"sleeper_bot_{i}", created_at, True))
        
    cursor.executemany("INSERT INTO users (username, created_at, is_bot) VALUES (?, ?, ?)", bots)
    
    # Get IDs of just inserted bots (assuming they are at the end)
    # A safer way is to select them back
    cursor.execute("SELECT id, created_at FROM users WHERE is_bot = 1")
    all_bots = cursor.fetchall()
    
    for b_id, b_created in all_bots:
        # All of them like the target video around 14:00 (+- 30 mins)
        offset_minutes = random.randint(-15, 45) # Skew slightly after 14:00
        like_time = yesterday_1400 + timedelta(minutes=offset_minutes)
        bot_likes.append((b_id, target_video_id, like_time))
        
    cursor.executemany("INSERT INTO likes (user_id, video_id, timestamp) VALUES (?, ?, ?)", bot_likes)
    conn.commit()

def main():
    conn = create_connection()
    create_tables(conn)
    generate_organic_data(conn)
    generate_bot_attack(conn)
    conn.close()
    print("Database generation complete.")

if __name__ == "__main__":
    main()
