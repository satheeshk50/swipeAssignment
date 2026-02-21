import os
from google import genai
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

def test_gemini_connection():
    # 1. Grab the API key from the environment
    # Alternatively, you can hardcode it for a quick local test: api_key = "AIzaSy..."
    api_key = os.getenv("GEMINI_API_KEY")
   
    
    if not api_key:
        print("⚠️ Warning: GEMINI_API_KEY environment variable not found.")
        print("Please set it, or temporarily paste your key into the code.")
        return

    print("Initializing Gemini Client...")
    
    try:
        # 2. Initialize the client
        client = genai.Client(api_key=api_key)
        
        print("Sending 'Hi' to the model...")
        
        # 3. Call generate_content 
        # (Using flash here as it's the fastest and cheapest for a simple test)
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents="Hi! I am testing my API connection. Can you reply with a quick 'Hello world' message?"
        )
        
        # 4. Print the result
        print("\n✅ Success! Response from Gemini:")
        print("-" * 40)
        print(response.text)
        print("-" * 40)

    except Exception as e:
        print(f"\n❌ Error connecting to Gemini API: {e}")

if __name__ == "__main__":
    test_gemini_connection()