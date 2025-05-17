import os
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if required variables are set
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Warning: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment.")
        
    return not missing_vars

# If this file is run directly, load environment variables
if __name__ == "__main__":
    if load_environment():
        print("Environment variables loaded successfully.")
    else:
        print("Failed to load all required environment variables.")