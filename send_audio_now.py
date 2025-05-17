import os
import json
import logging
from twilio.rest import Client
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Twilio credentials
account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Ngrok URL for audio files
ngrok_audio_url = "https://6a4f-2409-40d0-12e7-b690-ad0d-cc77-f41e-13cf.ngrok-free.app/audio"

# Initialize Twilio client
try:
    client = Client(account_sid, auth_token)
    logging.info("Twilio client initialized successfully")
except Exception as e:
    logging.error(f"Twilio client initialization failed: {e}")
    client = None

def send_whatsapp_message(phone_number, message_body, media_url=None):
    """
    Send a WhatsApp message to a specific phone number
    Returns True if successful, False otherwise
    """
    if not client:
        logging.warning(f"Skipping WhatsApp message to {phone_number} - Twilio client not initialized")
        return False
    
    try:
        # Format the phone number correctly for WhatsApp
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'
        
        message_params = {
            'from_': whatsapp_number,
            'body': message_body,
            'to': phone_number
        }
        
        if media_url:
            message_params['media_url'] = media_url
            
        message = client.messages.create(**message_params)
        logging.info(f"Sent WhatsApp message to {phone_number}: SID {message.sid}")
        return True
    except Exception as e:
        logging.error(f"Failed to send WhatsApp message to {phone_number}: {e}")
        return False

def send_audio_files():
    """
    Send audio files to all farmers
    """
    # Configuration
    upload_folder = 'static/audio/'
    farmers_file = 'farmers.json'
    
    # Get all audio files from static/audio directory
    audio_files = []
    for file in os.listdir(upload_folder):
        if file.endswith('.mp3'):
            file_path = os.path.join(upload_folder, file)
            audio_files.append({
                'filename': file,
                'path': file_path,
                'created': os.path.getctime(file_path)
            })
    
    # Sort by creation time (newest first)
    audio_files.sort(key=lambda x: x['created'], reverse=True)
    
    # Get the 3 most recent files
    recent_files = audio_files[:3]
    
    if not recent_files:
        logging.warning("No audio files found to send")
        return
    
    logging.info(f"Found {len(recent_files)} recent audio files:")
    for audio in recent_files:
        logging.info(f"- {audio['filename']}")
    
    # Get all farmers
    with open(farmers_file, 'r') as f:
        farmers = json.load(f)
    
    if not farmers:
        logging.warning("No farmers registered to send audio files to")
        return
    
    logging.info(f"Found {len(farmers)} farmers:")
    for farmer in farmers:
        logging.info(f"- {farmer['name']}: {farmer['phone']}")
    
    # Send audio files to each farmer
    for farmer in farmers:
        phone = farmer.get("phone")
        name = farmer.get("name", "किसान मित्र")
        
        # Send welcome message
        welcome_message = f"नमस्ते {name}! यहां आपके लिए नवीनतम कृषि ऑडियो फ़ाइलें हैं:"
        send_whatsapp_message(phone, welcome_message)
        
        # Send each audio file
        for i, audio in enumerate(recent_files):
            # Create full URL for the audio file
            media_url = f"{ngrok_audio_url}/{audio['filename']}"
            logging.info(f"Sending audio file: {media_url}")
            
            message = f"ऑडियो फ़ाइल {i+1}/3"
            result = send_whatsapp_message(phone, message, media_url)
            if result:
                logging.info(f"Successfully sent audio file {i+1} to {phone}")
            else:
                logging.error(f"Failed to send audio file {i+1} to {phone}")
            time.sleep(3)  # Delay between messages
        
        logging.info(f"Sent {len(recent_files)} audio files to {name} at {phone}")
        time.sleep(2)  # Delay between farmers
    
    logging.info(f"Finished sending audio files to {len(farmers)} farmers")

if __name__ == "__main__":
    print("Starting to send audio files to all farmers...")
    send_audio_files()
    print("Done. Check logs for details.")