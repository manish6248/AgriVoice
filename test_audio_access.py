import requests
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_audio_access(ngrok_url, audio_filename):
    """
    Test if an audio file is accessible through the ngrok URL
    """
    # Construct the URL to the audio file
    url = f"{ngrok_url}/audio/{audio_filename}"
    
    logging.info(f"Testing access to: {url}")
    
    try:
        # Try to access the file
        response = requests.get(url, stream=True)
        
        # Check if the request was successful
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', 'unknown')
            
            logging.info(f"SUCCESS: File is accessible")
            logging.info(f"Content-Type: {content_type}")
            logging.info(f"Content-Length: {content_length} bytes")
            
            # Save a small sample of the file to verify it's audio
            with open("test_sample.mp3", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        break  # Just save a small sample
            
            logging.info(f"Saved sample to test_sample.mp3")
            return True
        else:
            logging.error(f"FAILED: HTTP status code {response.status_code}")
            logging.error(f"Response: {response.text[:500]}")
            return False
    
    except Exception as e:
        logging.error(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_audio_access.py <ngrok_url> <audio_filename>")
        print("Example: python test_audio_access.py https://6a4f-2409-40d0-12e7-b690-ad0d-cc77-f41e-13cf.ngrok-free.app notice_20250518040008.mp3")
        sys.exit(1)
    
    ngrok_url = sys.argv[1]
    audio_filename = sys.argv[2]
    
    # Remove trailing slash from URL if present
    ngrok_url = ngrok_url.rstrip('/')
    
    test_audio_access(ngrok_url, audio_filename)