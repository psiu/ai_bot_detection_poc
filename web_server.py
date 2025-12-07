from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import datetime
from datetime import timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

app = FastAPI(title="Social Media Fraud Detection API")

# Enable CORS for React frontend (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "social_media_logs.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- User Risk Analysis Endpoint ---

@app.get("/api/users/risk")
def get_user_risk(limit: int = 20, search: str = None): # Default limit 20
    """
    Calculate and return users sorted by Risk Score.
    Includes 'alert_reason'.
    """
    conn = get_db_connection()
    try:
        params = []
        where_clause = ""
        if search:
            where_clause = "WHERE u.username LIKE ?"
            params.append(f"%{search}%")
            
        # Critical attack pattern (Yesterday 14:00)
        yesterday = (datetime.datetime.now(datetime.timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        attack_pattern = f"{yesterday}%14:%"
        
        # SQL Logic:
        # High Risk = Fresh Bot OR (Sleeper Bot AND Active in Spike)
        # Alert Reason = Text description
        query = f"""
            WITH UserStats AS (
                SELECT 
                    u.id, u.username, u.created_at, u.is_bot,
                    EXISTS (
                        SELECT 1 FROM likes l WHERE l.user_id = u.id 
                        AND l.video_id = 20 AND l.timestamp LIKE ?
                    ) as in_attack,
                    (SELECT COUNT(*) FROM likes WHERE user_id = u.id) as total_likes
                FROM users u
                {where_clause}
            )
            SELECT *,
                CASE 
                    WHEN (julianday('now') - julianday(created_at)) * 24 < 48 THEN 50
                    WHEN (julianday('now') - julianday(created_at)) > 90 AND in_attack THEN 40
                    ELSE 0 
                END + (CASE WHEN in_attack THEN 50 ELSE 0 END) as risk_score,
                
                CASE
                    WHEN (julianday('now') - julianday(created_at)) * 24 < 48 THEN 'New Account Velocity'
                    WHEN in_attack AND (julianday('now') - julianday(created_at)) > 90 THEN 'Sleeper Activation'
                    WHEN in_attack THEN 'Spike Participation'
                    ELSE 'Normal'
                END as alert_reason
                
            FROM UserStats
            ORDER BY risk_score DESC, total_likes DESC
            LIMIT ?
        """
        params.insert(0, attack_pattern) # Prepend attack_pattern
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/users/{username}")
def get_user_details_api(username: str):
    """Fetch details for a specific user (Account age, activity)."""
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user: raise HTTPException(status_code=404, detail="User not found")
        
        stats = conn.execute("SELECT COUNT(*) as count, MAX(timestamp) as last_active FROM likes WHERE user_id = ?", (user['id'],)).fetchone()
        recent = conn.execute("""
            SELECT v.title, l.timestamp 
            FROM likes l JOIN videos v ON l.video_id = v.id 
            WHERE l.user_id = ? ORDER BY l.timestamp DESC LIMIT 5
        """, (user['id'],)).fetchall()
        
        # --- Mock Profile Generation (Deterministic) ---
        import hashlib
        h = int(hashlib.md5(username.encode()).hexdigest(), 16)
        
        locations = ["New York, USA", "London, UK", "Toronto, Canada", "Berlin, Germany", "Sydney, Australia", "Unknown Proxy", "Data Center (AWS-East)"]
        bios = [
            "Just here for the vibes.", "Crypto enthusiast 🚀", "Travel | Food | Tech", 
            "Digital Nomad.", "Official Account.", "DM for collab.", "Automation script (DEBUG)", "..."
        ]
        
        profile = {
            "followers": (h % 5000) + 12,
            "following": (h % 500) + 50,
            "posts": (h % 100),
            "location": locations[h % len(locations)],
            "bio": bios[h % len(bios)],
            "avatar": f"https://api.dicebear.com/7.x/identicon/svg?seed={username}"
        }
        
        # --- Risk Narrative Generation ---
        created = datetime.datetime.fromisoformat(user['created_at'])
        if created.tzinfo: created = created.replace(tzinfo=None) # Make naive
        now = datetime.datetime.utcnow() # Naive UTC
        age_hours = (now - created).total_seconds() / 3600
        total_likes = stats['count']
        
        narrative = []
        if age_hours < 48:
             narrative.append(f"Account is extremely fresh (created {int(age_hours)} hours ago). High velocity activity immediately after creation suggests automated scripting.")
        
        if total_likes > 50: # Arbitrary high threshold for POC
             narrative.append(f"Abnormally high engagement volume ({total_likes} likes) detected, exceeding human click-rate benchmarks.")
             
        if user['is_bot']:
             narrative.append(f"Pattern matches known botnet signature 'Spike-Walker-V2'. User was dormant until activation event.")
        
        if not narrative:
             narrative.append("User exhibits generally organic behavior, though minor anomalies in timing were flagged.")
             
        risk_narrative = " ".join(narrative)
        
        return {
            "id": user['id'],
            "username": user['username'],
            "created_at": user['created_at'],
            "is_bot": user['is_bot'],
            "total_likes": stats['count'],
            "last_active": stats['last_active'],
            "recent_activity": [dict(r) for r in recent],
            "profile": profile,
            "risk_narrative": risk_narrative
        }
    finally:
        conn.close()

# --- Data Endpoints ---

@app.get("/api/videos")
def list_videos():
    """Get list of all videos for the dropdown."""
    conn = get_db_connection()
    try:
        videos = conn.execute("SELECT * FROM videos ORDER BY id ASC").fetchall()
        return [dict(v) for v in videos]
    finally:
        conn.close()

@app.get("/api/likes/{video_id}")
def get_video_likes_series(video_id: int):
    """
    Get hourly like counts for a video to plot on a chart.
    Returns: { "labels": [...dates], "data": [...counts] }
    """
    conn = get_db_connection()
    try:
        # Get video range to limit query efficiency
        # For this POC, we just aggregate all likes for the video by hour
        query = """
            SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour_bucket, COUNT(*) as count
            FROM likes
            WHERE video_id = ?
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        """
        rows = conn.execute(query, (video_id,)).fetchall()
        
        # Format for Chart.js
        labels = [row["hour_bucket"] for row in rows]
        data = [row["count"] for row in rows]
        
        return {"labels": labels, "data": data}
    finally:
        conn.close()

@app.get("/api/activity")
def get_video_activity(video_id: int, hour: str):
    """
    Get all users who liked a video during a specific hour.
    Query param hour format: 'YYYY-MM-DD HH'
    """
    conn = get_db_connection()
    try:
        try:
            target_dt = datetime.datetime.strptime(hour, "%Y-%m-%d %H")
        except ValueError:
             raise HTTPException(status_code=400, detail="Invalid hour format. Use 'YYYY-MM-DD HH'")
             
        s = target_dt.strftime("%Y-%m-%d %H:00:00")
        e = (target_dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")
        
        # Join with users to get details
        query = """
            SELECT u.username, u.is_bot, u.created_at, l.timestamp 
            FROM likes l 
            JOIN users u ON l.user_id = u.id 
            WHERE l.video_id = ? AND l.timestamp >= ? AND l.timestamp < ?
            ORDER BY l.timestamp ASC
        """
        rows = conn.execute(query, (video_id, s, e)).fetchall()
        
        # Calculate flags dynamically
        results = []
        for r in rows:
            mapped = dict(r)
            created = datetime.datetime.fromisoformat(str(r["created_at"]))
            liked = datetime.datetime.fromisoformat(str(r["timestamp"]))
            age = liked - created
            
            # Risk Flags
            mapped['risk_label'] = 'Normal'
            if age < timedelta(hours=48): mapped['risk_label'] = 'Fresh Account'
            elif mapped['is_bot'] and age > timedelta(days=90): mapped['risk_label'] = 'Sleeper Pattern'
            
            results.append(mapped)
            
        return results
    finally:
        conn.close()

# --- Chat Endpoint (Gemini Integration) ---

class ChatRequest(BaseModel):
    message: str
    history: list = [] # Not used yet, simple stateless for now or just current turn

@app.post("/api/chat")
def chat_agent(request: ChatRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not found")

    client = genai.Client(api_key=API_KEY)
    
    # --- TOOLS ---
    
    def get_video_stats(video_id: int):
        conn = get_db_connection()
        try:
            video = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
            if not video: return f"Error: Video ID {video_id} not found."
            
            # Basic stats
            count = conn.execute("SELECT COUNT(*) FROM likes WHERE video_id = ?", (video_id,)).fetchone()[0]
            
            # Peak detection
            peak = conn.execute("""
                SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, COUNT(*) as cnt 
                FROM likes WHERE video_id = ? 
                GROUP BY hour ORDER BY cnt DESC LIMIT 1
            """, (video_id,)).fetchone()
            
            peak_info = f", Peak Activity: {peak['hour']} ({peak['cnt']} likes)" if peak else ", Peak Activity: None"
            
            return f"ID: {video['id']}, Title: {video['title']}, Uploaded: {video['upload_date']}, Total Likes: {count}, Archetype: {video['archetype']}{peak_info}"
        finally:
            conn.close()

    def analyze_hourly_spike(video_id: int, target_hour: str):
        conn = get_db_connection()
        try:
            try:
                target_dt = datetime.datetime.strptime(target_hour, "%Y-%m-%d %H")
            except ValueError:
                return "Error: Invalid date format. Use 'YYYY-MM-DD HH'."
            prev = target_dt - timedelta(hours=1)
            next_h = target_dt + timedelta(hours=1)
            
            def count(dt):
                s = dt.strftime("%Y-%m-%d %H:00:00")
                e = (dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")
                return conn.execute("SELECT COUNT(*) FROM likes WHERE video_id=? AND timestamp>=? AND timestamp<?", (video_id,s,e)).fetchone()[0]
            
            return f"Analysis {target_hour}: Prev={count(prev)}, Target={count(target_dt)}, Next={count(next_h)}"
        finally:
            conn.close()

    def fetch_suspicious_users(video_id: int, target_hour: str):
        """Analyze users in a spike."""
        conn = get_db_connection()
        try:
            try:
                target_dt = datetime.datetime.strptime(target_hour, "%Y-%m-%d %H")
            except ValueError: return "Error: Date format YYYY-MM-DD HH"
            s = target_dt.strftime("%Y-%m-%d %H:00:00")
            e = (target_dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:00:00")
            
            query = """
                SELECT u.username, u.created_at, l.timestamp 
                FROM likes l JOIN users u ON l.user_id = u.id 
                WHERE l.video_id=? AND l.timestamp>=? AND l.timestamp<?
            """
            rows = conn.execute(query, (video_id, s, e)).fetchall()
            results = []
            for r in rows:
                try:
                    created = datetime.datetime.fromisoformat(str(r[1]))
                    liked = datetime.datetime.fromisoformat(str(r[2]))
                    age = liked - created
                    flag = "[FRESH ACCOUNT]" if age < timedelta(hours=24) else ("[SLEEPER]" if age > timedelta(days=90) else "")
                    if flag: results.append(f"User: {r[0]}, Age: {age}, {flag}")
                except: continue
            return "\n".join(results[:50]) + ("..." if len(results)>50 else "") if results else "No users found."
        finally:
            conn.close()

    def get_user_details(username: str):
        """Get details about a specific user."""
        try:
            res = get_user_details_api(username) # Reuse the API function logic
            return str(res)
        except Exception as e: return f"Error: {e}"

    def run_read_only_sql(sql_query: str):
        """
        Run a READ-ONLY SQL query on 'social_media_logs.db'.
        Tables: users(id, username, created_at, is_bot), videos(id, title), likes(user_id, video_id, timestamp).
        """
        if not sql_query.lower().strip().startswith("select"):
            return "Error: Only SELECT queries are allowed."
        conn = get_db_connection()
        try:
            rows = conn.execute(sql_query).fetchall()
            return str([dict(r) for r in rows][:20]) # Limit to 20 rows
        except Exception as e: return f"SQL Error: {e}"
        finally: conn.close()

    
    def get_security_briefing(limit: int = 5):
        """
        Global Scan: Finds TOP anomalies across the entire database.
        Returns videos and times with high 'Fresh Bot' activity.
        Use this when asked "Tell me about alerts" or "What is suspicious?".
        """
        conn = get_db_connection()
        try:
            # Detect clusters of Fresh Accounts (Created < 48 hours before Like)
            # This is the strongest signal of a bot attack
            query = """
                SELECT 
                    v.id as video_id, v.title,
                    strftime('%Y-%m-%d %H:00', l.timestamp) as hour,
                    COUNT(*) as total_likes,
                    SUM(CASE 
                        WHEN (julianday(l.timestamp) - julianday(u.created_at)) * 24 < 48 THEN 1 
                        ELSE 0 
                    END) as fresh_bot_count
                FROM likes l
                JOIN users u ON l.user_id = u.id
                JOIN videos v ON l.video_id = v.id
                GROUP BY video_id, hour
                HAVING fresh_bot_count > 10
                ORDER BY fresh_bot_count DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
            
            if not rows: return "No major anomalies detected in the system."
            
            report = "Security Briefing (Top Anomalies):\n"
            for r in rows:
                report += f"- ALERT: Video {r['video_id']} ('{r['title']}') at {r['hour']}. Detected {r['fresh_bot_count']} fresh bots (Total Likes: {r['total_likes']}).\n"
            
            return report + "\nAnalysis: Please investigate these specific timeframes using 'fetch_suspicious_users'."
        finally:
             conn.close()

    tools_map = {
        "get_video_stats": get_video_stats,
        "analyze_hourly_spike": analyze_hourly_spike,
        "fetch_suspicious_users": fetch_suspicious_users,
        "get_user_details": get_user_details,
        "run_read_only_sql": run_read_only_sql,
        "get_security_briefing": get_security_briefing
    }

    # System Prompt
    sys_instruct = """You are a Forensics Analyst.
    
    CORE WORKFLOWS:
    1. GENERAL ALERTS ("What's happening?", "Any alerts?"):
       -> Call 'get_security_briefing()' immediately.
       -> Summarize the findings.
       
    2. SPECIFIC SPIKE ("Investigate the spike on video 20"):
       -> Call 'get_video_stats(20)' to find the peak time.
       -> Then call 'fetch_suspicious_users' for that time.
       
    3. DEEP DIVE ("Who is user_123?"):
       -> Call 'get_user_details'.

    Tools:
    - 'get_security_briefing': **START HERE** for open-ended queries. Finds high-risk attacks.
    - 'get_video_stats': Peak activity detection.
    - 'fetch_suspicious_users': List users in a specific hour.
    - 'run_read_only_sql': Advanced custom queries.
    
    Be concise and professional."""

    # Chat execution
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(name="get_video_stats", description="Get video stats", parameters={"type":"object","properties":{"video_id":{"type":"integer"}}}),
                types.FunctionDeclaration(name="analyze_hourly_spike", description="Check neighbors", parameters={"type":"object","properties":{"video_id":{"type":"integer"},"target_hour":{"type":"string"}}}),
                types.FunctionDeclaration(name="fetch_suspicious_users", description="List users in spike", parameters={"type":"object","properties":{"video_id":{"type":"integer"},"target_hour":{"type":"string"}}}),
                types.FunctionDeclaration(name="get_user_details", description="Get details for a username", parameters={"type":"object","properties":{"username":{"type":"string"}}}),
                types.FunctionDeclaration(name="run_read_only_sql", description="Run generic SQL query", parameters={"type":"object","properties":{"sql_query":{"type":"string"}}}),
                types.FunctionDeclaration(name="get_security_briefing", description="Global security summary", parameters={"type":"object","properties":{"limit":{"type":"integer"}}})
            ])],
            temperature=0
        )
    )

    try:
        response = chat.send_message(request.message)
        
        for _ in range(5):
             try:
                part = response.candidates[0].content.parts[0]
             except: break
             
             if hasattr(part, "function_call") and part.function_call:
                 fn = part.function_call
                 name = fn.name
                 args = fn.args
                 print(f"Calling Tool: {name}")
                 if name in tools_map:
                     res_txt = str(tools_map[name](**args))
                 else:
                     res_txt = "Error: Tool not found"
                 
                 response = chat.send_message(
                     types.Part.from_function_response(name=name, response={"result": res_txt})
                 )
             else:
                 return {"response": response.text}
                 
        return {"response": response.text}

    except Exception as e:
        print(f"Chat Error: {e}")
        return {"response": f"Error interacting with Agent: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
