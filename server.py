from mcp.server.fastmcp import FastMCP
import sqlite3
import datetime
from datetime import timedelta

# Initialize FastMCP server
mcp = FastMCP("Social Media Forensics")
DB_NAME = "social_media_logs.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def get_video_stats(video_id: int) -> str:
    """Returns metadata for a given video ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        video = cursor.fetchone()
        
        if not video:
            return f"Error: Video ID {video_id} not found."
            
        cursor.execute("SELECT COUNT(*) FROM likes WHERE video_id = ?", (video_id,))
        like_count = cursor.fetchone()[0]
        
        return f"ID: {video['id']}, Title: {video['title']}, Uploaded: {video['upload_date']}, Total Likes: {like_count}"
    finally:
        conn.close()

@mcp.tool()
def analyze_hourly_spike(video_id: int, target_hour: str) -> str:
    """
    Calculates like counts for the target hour, previous hour, and next hour to detect local peaks.
    target_hour format: 'YYYY-MM-DD HH' (e.g., '2023-10-27 14')
    """
    conn = get_db_connection()
    try:
        # Parse target hour
        try:
            target_dt = datetime.datetime.strptime(target_hour, "%Y-%m-%d %H")
        except ValueError:
            return "Error: Invalid date format. Use 'YYYY-MM-DD HH'."
            
        prev_hour_dt = target_dt - timedelta(hours=1)
        next_hour_dt = target_dt + timedelta(hours=1)
        
        def count_likes_in_hour(dt):
            start = dt.strftime("%Y-%m-%d %H:00:00")
            end = (dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM likes WHERE video_id = ? AND timestamp >= ? AND timestamp < ?",
                (video_id, start, end)
            )
            return cursor.fetchone()[0]

        target_count = count_likes_in_hour(target_dt)
        prev_count = count_likes_in_hour(prev_hour_dt)
        next_count = count_likes_in_hour(next_hour_dt)
        
        return (f"Analysis for {target_hour}:00\n"
                f"Previous Hour ({prev_hour_dt.strftime('%H:00')}): {prev_count} likes\n"
                f"Target Hour ({target_dt.strftime('%H:00')}): {target_count} likes\n"
                f"Next Hour ({next_hour_dt.strftime('%H:00')}): {next_count} likes")
    finally:
        conn.close()

@mcp.tool()
def fetch_suspicious_users(video_id: int, target_hour: str) -> str:
    """
    Returns a list of users who liked the video in that hour and flags them if they meet bot criteria.
    Criteria:
    - Fresh Bot: Account created < 24 hours before the like.
    - Sleeper Bot: Account created > 90 days ago but has low activity (mocked check here as simple Flag).
    target_hour: 'YYYY-MM-DD HH'
    """
    conn = get_db_connection()
    try:
        try:
            target_dt = datetime.datetime.strptime(target_hour, "%Y-%m-%d %H")
        except ValueError:
            return "Error: Invalid date format. Use 'YYYY-MM-DD HH'."
            
        start = target_dt.strftime("%Y-%m-%d %H:00:00")
        end = (target_dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")
        
        cursor = conn.cursor()
        query = """
            SELECT u.id, u.username, u.created_at, l.timestamp as like_time
            FROM likes l
            JOIN users u ON l.user_id = u.id
            WHERE l.video_id = ? AND l.timestamp >= ? AND l.timestamp < ?
        """
        cursor.execute(query, (video_id, start, end))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            # We need to parse dates carefully. 
            # SQLite format is usually ISO8601 strings.
            try:
                created_at = datetime.datetime.fromisoformat(str(row['created_at']))
                like_time = datetime.datetime.fromisoformat(str(row['like_time']))
            except ValueError:
                # Handle cases where microsecond might be missing or different format
                # Fallback to simple split or ignore for POC
                results.append(f"User: {row['username']} (Error parsing dates)")
                continue

            age_at_like = like_time - created_at
            
            flag = ""
            if age_at_like < timedelta(hours=24):
                flag = "[FRESH BOT]"
            elif age_at_like > timedelta(days=90):
                 # For "low activity", in a real system we'd check their total likes.
                 # Here we know our generation logic: Sleeper bots are > 3 months.
                 # Organic users are also > 3 months potentially.
                 # The prompt asked "flag them IF they meet bot criteria".
                 # The generation logic defined Sleeper Bots as: created > 3 months ago.
                 # The user request said "created > 3 months ago but with low activity".
                 # Since we didn't strictly implement "low activity" stores for organic vs bot distinction 
                 # (organic users also like things), we need a heuristic.
                 # However, we DO have an `is_bot` column in the DB!
                 # BUT, a forensics tool shouldn't cheat by looking at `is_bot`.
                 # It should deduce it.
                 # Let's stick to the prompt requirement: "created > 3 months ago".
                 # Wait, organic users are also > 3 months.
                 # The prompt says: "low activity".
                 # Let's look up how many total likes this user has.
                 
                 cursor_check = conn.cursor()
                 cursor_check.execute("SELECT COUNT(*) FROM likes WHERE user_id = ?", (row['id'],))
                 total_likes = cursor_check.fetchone()[0]
                 
                 # Heuristic: If total likes < 5 over 3 months, maybe sleeper?
                 # Our organic users have 5-20 likes. Be careful.
                 # Let's flag if total_likes <= 2 ? Or just label it as "POTENTIAL SLEEPER"
                 
                 # Actually, let's just output the metadata and let the Agent decide based on "Low Activity" text?
                 # Or just flag it. Use: "Old Account (Potential Sleeper? Total Likes: N)"
                 flag = f"[SLEEPER? Check Activity: {total_likes} likes]"

            results.append(f"User: {row['username']}, Created: {row['created_at']} {flag}")
            
        return "\n".join(results) if results else "No likes found in this hour."
        
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run()
