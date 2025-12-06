import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    sys.exit(1)

def test_api():
    print("Initializing Gemini Client...")
    client = genai.Client(api_key=API_KEY)
    
    print("Sending a simple 'Hello' request...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Hello, are you online?"
        )
        print("\nSuccess! API Responded:")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"\nAPI Error: {e}")
        return False

if __name__ == "__main__":
    test_api()
