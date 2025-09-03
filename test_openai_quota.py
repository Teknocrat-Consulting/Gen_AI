#!/usr/bin/env python3
import openai
import os
from dotenv import load_dotenv

load_dotenv()

def test_openai_quota():
    """Test OpenAI API quota by making a simple request."""
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in the .env file")
        return False
    
    # Initialize client
    client = openai.OpenAI(api_key=api_key)
    
    try:
        print("🔍 Testing OpenAI API quota...")
        print(f"Using API key: {api_key[:8]}...{api_key[-4:]}")
        
        # Make a minimal API request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ SUCCESS: API request completed successfully")
        print(f"Response: {response.choices[0].message.content}")
        print("Your OpenAI API quota is working properly")
        return True
        
    except openai.RateLimitError as e:
        print("❌ QUOTA ERROR: You have exceeded your OpenAI API quota")
        print(f"Error details: {e}")
        print("\nSolutions:")
        print("1. Check your OpenAI billing at: https://platform.openai.com/account/billing")
        print("2. Add payment method if needed")
        print("3. Wait for quota reset if on free tier")
        return False
        
    except openai.AuthenticationError as e:
        print("❌ AUTH ERROR: Invalid API key")
        print(f"Error details: {e}")
        print("Please check your OPENAI_API_KEY in the .env file")
        return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_quota()
    exit(0 if success else 1)