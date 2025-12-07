# Social Media Bot Detection Agent (PoC)

## Overview
This Proof of Concept (PoC) demonstrates a **Fraud Detection Agent** that identifies bot attacks on social media platforms. It uses **Google Gemini 2.5 Flash** combined with the **Model Context Protocol (MCP)** to give the AI direct access to database forensics tools.

## Architecture
- **Agent**: `client.py` (Gemini-powered interactive forensic analyst).
- **Server**: `server.py` (FastMCP server connecting to SQLite).
- **Database**: `social_media_logs.db` (Generated mock data with embedded "bot attacks").

## Features
- **Data Generation**: creates a realistic mix of organic traffic and coordinated bot attacks (Fresh Bots & Sleeper Bots).
- **Tool Logic**:
    - `get_video_stats`: Fetch metadata and total likes.
    - `analyze_hourly_spike`: Detects unnatural traffic spikes compared to neighboring hours.
    - `fetch_suspicious_users`: Lists users involved in a spike and flags suspicious account ages.

## Setup

1.  **Prerequisites**:
    - Python 3.10+
    - Google API Key (with Gemini access)

2.  **Install**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    pip install mcp google-genai python-dotenv
    ```

3.  **Configure**:
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_api_key_here
    ```

4.  **Generate Data**:
    ```powershell
    python data_gen.py
    ```
    *This creates `social_media_logs.db` with a bot attack simulated on Video #20.*

## Usage

Run the agent:
```powershell
python client.py
```

**Example Scenario**:
> **User**: "Investigate video 20 for suspicious activity yesterday at 14:00"
>
> **Agent**: *Analyzing spike... Found 150 likes. 100% of users are <24h old. This is a Bot Attack.*

## Project Structure
- `client.py`: Main entry point. Handles rate limiting and Gemini API interaction.
- `server.py`: Defines the forensics tools available to the agent.
- `data_gen.py`: Setup script to populates the database.
- `test_api.py`: Utility to verify API key connectivity.
