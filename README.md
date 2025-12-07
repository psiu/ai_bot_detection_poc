# Social Media Fraud Detection Agent (PoC)

## Overview
This is an advanced **AI-Powered Forensics Dashboard** designed to detect and analyze social media bot networks. It combines a **FastAPI/SQLite backend** with a **React Frontend** and a **Gemini 2.5 Flash Agent** to provide autonomous investigation capabilities.

## Key Features
### 🕵️ Autonmous Agent
- **Self-Correcting Investigator**: Can investigate vague queries like "What happened during the spike?" by autonomously checking video stats first.
- **Tools**: `get_video_stats` (Peak Detection), `run_read_only_sql` (Generic Queries), `fetch_suspicious_users`.

### 📊 Forensics Dashboard (React)
- **User Risk Explorer**: Sortable list of flagged users with "Alert Reasons" (e.g., *Spike Participation*).
- **Interactive Charts**: Click on any data point in the activity graph to drill down into that specific hour's traffic.
- **Rich User Profiles**: Modals displaying simulated Bio, Location, Avatar, and a **Risk Narrative** explaining why the user was flagged.

### 🛡️ Detection Logic
- **Fresh Bots**: Accounts < 48h old with high velocity.
- **Sleeper Bots**: Old accounts dormant for > 90 days that suddenly activate during an attack.
- **Spike Analysis**: Statistical anomaly detection on hourly traffic.

## Tech Stack
- **Frontend**: React (Vite), Chart.js, Lucide Icons.
- **Backend**: Python FastAPI, SQLite.
- **AI**: Google Gemini 2.5 Flash (via `google-genai` SDK).

## Setup & Run

1.  **Environment**:
    Create a `.env` file:
    ```env
    GOOGLE_API_KEY=your_gemini_api_key
    ```

2.  **Install Dependencies**:
    ```powershell
    # Backend
    pip install fastapi uvicorn google-genai python-dotenv asyncio

    # Frontend (in /web_app)
    cd web_app
    npm install
    ```

3.  **Generate Data**:
    ```powershell
    python data_gen.py
    ```

4.  **Launch System**:
    *   **Backend**: `python web_server.py` (Runs on port 8000)
    *   **Frontend**: `npm run dev` (Runs on port 5173)

5.  **Access**: Open `http://localhost:5173` in your browser.

## Project Structure
- `web_server.py`: Main FastAPI application and Agent definition.
- `data_gen.py`: Generates the mock database with organic vs. bot traffic.
- `web_app/`: Source code for the React dashboard.

