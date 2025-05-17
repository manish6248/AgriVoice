import os

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Server configuration
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')

# Ngrok URL for audio files
NGROK_AUDIO_URL = "https://6a4f-2409-40d0-12e7-b690-ad0d-cc77-f41e-13cf.ngrok-free.app/audio"