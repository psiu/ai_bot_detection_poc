import sqlite3
import random
from datetime import datetime, timedelta, timezone

DB_NAME = "social_media_logs.db"

def create_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS likes")
    c.execute("DROP TABLE IF EXISTS videos")
    c.execute("DROP TABLE IF EXISTS users")
    
    c.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        created_at TEXT, -- ISO format
        is_bot BOOLEAN
    )""")
    
    c.execute("""CREATE TABLE videos (
        id INTEGER PRIMARY KEY,
        title TEXT,
        upload_date TEXT,
        archetype TEXT -- 'viral', 'flop', 'steady', 'dead'
    )""")
    
    c.execute("""CREATE TABLE likes (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        video_id INTEGER,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(video_id) REFERENCES videos(id)
    )""")
    conn.commit()
    return conn

def generate_data():
    conn = create_db()
    cursor = conn.cursor()
    
    print("Generating Users...")
    users = []
    # 1000 Organic Users (Created over last 2 years)
    start_date = datetime.now(timezone.utc) - timedelta(days=730)
    for i in range(1000):
        created = start_date + timedelta(days=random.randint(0, 700))
        users.append((f"user_{random.randint(10000, 99999)}", created.isoformat(), False))
    
    # 300 Sleeper Bots (Old accounts, inactive until attack)
    for i in range(300):
        created = start_date + timedelta(days=random.randint(0, 365))
        # Anonymized: looks like normal user
        users.append((f"user_{random.randint(10000, 99999)}", created.isoformat(), True))

    # 200 Fresh Bots (Created very recently, < 48 hours ago)
    recent_start = datetime.now(timezone.utc) - timedelta(hours=48)
    for i in range(200):
        created = recent_start + timedelta(minutes=random.randint(0, 2800))
        # Anonymized
        users.append((f"user_{random.randint(10000, 99999)}", created.isoformat(), True))

    cursor.executemany("INSERT INTO users (username, created_at, is_bot) VALUES (?, ?, ?)", users)
    
    # Need to keep track of organic vs bot IDs for like generation?
    # IDs are auto-increment.
    # 1-1000: Organic
    # 1001-1300: Sleepers
    # 1301-1500: Fresh
    # This assumption holds because of insertion order.
    
    print("Generating Videos...")
    videos = []
    archetypes = ['viral', 'flop', 'steady', 'dead']
    # 50 Videos uploaded in last 6 months
    vid_start = datetime.now(timezone.utc) - timedelta(days=180)
    
    for i in range(50):
        upload = vid_start + timedelta(days=random.randint(0, 170))
        atype = random.choices(archetypes, weights=[10, 20, 40, 30])[0]
        # Make Video 20 specifically the attack target, steady usually
        if i == 20: atype = 'steady' 
        
        videos.append((i, f"Video Title {i} ({atype})", upload.isoformat(), atype))
        
    cursor.executemany("INSERT INTO videos (id, title, upload_date, archetype) VALUES (?, ?, ?, ?)", videos)

    print("Generating Likes (Attributes-based)...")
    likes = []
    
    # Simulation Window: Last 6 months
    # We iterate by hour? No, that's too slow.
    # We iterate by video and generate based on its curve.
    
    for vid_id, title, upload_str, atype in videos:
        upload_dt = datetime.fromisoformat(upload_str)
        now = datetime.now(timezone.utc)
        days_live = (now - upload_dt).days
        if days_live < 0: continue
        
        # Determine total organic likes based on archetype
        organic_volume = 0
        if atype == 'viral': organic_volume = random.randint(500, 2000)
        elif atype == 'steady': organic_volume = random.randint(100, 500)
        elif atype == 'flop': organic_volume = random.randint(50, 200)
        else: organic_volume = random.randint(0, 20)
        
        # Distribute likes
        for _ in range(organic_volume):
            # Choose a user (mostly organic)
            uid = random.randint(1, 1000) # Organic users are 1-1000
            
            # Time distribution
            delay_days = 0
            if atype == 'viral':
                # Viral: Slow start, huge spike, long tail
                # Simplified: Gamma-ish distribution
                delay_days = int(random.gammavariate(2, 5))
            elif atype == 'flop':
                # Flop: Huge start, effectively zero after 3 days
                delay_days = int(random.gammavariate(1, 1))
            elif atype == 'steady':
                # Steady: Uniform-ish over time
                delay_days = random.randint(0, days_live if days_live > 0 else 0)
            else:
                delay_days = random.randint(0, 10)

            if delay_days > days_live: delay_days = days_live
            
            # Add random hour
            like_time = upload_dt + timedelta(days=delay_days, hours=random.randint(0,23), minutes=random.randint(0,59))
            likes.append((uid, vid_id, like_time.isoformat()))

    # --- SIMULATE ATTACK ---
    # Target: Video 20
    # Time: Yesterday at 14:00
    target_vid = 20
    attack_time_base = datetime.now(timezone.utc) - timedelta(days=1)
    attack_time_base = attack_time_base.replace(hour=14, minute=0, second=0, microsecond=0)
    
    print(f"Injecting Bot Attack on Video {target_vid} at {attack_time_base.isoformat()}...")
    
    # Attackers: 200 Fresh Bots + 100 Sleepers
    # IDs: Fresh (1301-1500), Sleepers (1001-1300) -> Wait, user IDs are auto-assigned.
    # Organic: 1-1000. Sleepers: 1001-1300. Fresh: 1301-1500.
    
    attackers = list(range(1001, 1500)) # All bots
    random.shuffle(attackers)
    
    for uid in attackers:
        # Tightly clustered around 14:00 - 14:15
        offset = timedelta(minutes=random.randint(0, 15), seconds=random.randint(0, 59))
        ts = attack_time_base + offset
        likes.append((uid, target_vid, ts.isoformat()))
        
    print(f"Total Likes Generated: {len(likes)}")
    cursor.executemany("INSERT INTO likes (user_id, video_id, timestamp) VALUES (?, ?, ?)", likes)
    
    conn.commit()
    conn.close()
    print("Database generation complete.")

if __name__ == "__main__":
    generate_data()
