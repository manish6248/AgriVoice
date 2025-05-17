import os
import time
import json
import logging
import requests
import subprocess
from threading import Thread

def get_ngrok_url():
    """
    Get the public URL from ngrok API
    Returns the HTTPS URL if available, None otherwise
    """
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        data = response.json()
        
        if 'tunnels' in data and len(data['tunnels']) > 0:
            # Get the HTTPS URL
            for tunnel in data['tunnels']:
                if tunnel['proto'] == 'https':
                    return tunnel['public_url']
            
            # If no HTTPS URL found, return the first URL
            return data['tunnels'][0]['public_url']
    except Exception as e:
        logging.error(f"Error getting ngrok URL: {e}")
    
    return None

def start_ngrok(port=5000):
    """
    Start ngrok in a separate process
    """
    try:
        # Check if ngrok is already running
        try:
            requests.get('http://localhost:4040/api/tunnels')
            logging.info("ngrok is already running")
            return True
        except:
            pass
        
        # Start ngrok
        subprocess.Popen(['ngrok', 'http', str(port)], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        stdin=subprocess.PIPE)
        
        # Wait for ngrok to start
        for _ in range(10):
            time.sleep(1)
            try:
                url = get_ngrok_url()
                if url:
                    logging.info(f"ngrok started with URL: {url}")
                    return True
            except:
                pass
        
        logging.error("Failed to start ngrok")
        return False
    except Exception as e:
        logging.error(f"Error starting ngrok: {e}")
        return False

def update_server_url_thread(app):
    """
    Thread function to update the server_url variable
    """
    time.sleep(5)  # Wait for Flask and ngrok to start
    
    try:
        url = get_ngrok_url()
        if url:
            # Update the global server_url variable
            import app as flask_app
            flask_app.server_url = url
            logging.info(f"Updated server URL to: {url}")
    except Exception as e:
        logging.error(f"Error updating server URL: {e}")

def setup_ngrok(app, port=5000):
    """
    Setup ngrok for the Flask app
    """
    # Start a thread to update the server URL
    Thread(target=update_server_url_thread, args=(app,), daemon=True).start()
    
    # Try to start ngrok if not already running
    Thread(target=start_ngrok, args=(port,), daemon=True).start()