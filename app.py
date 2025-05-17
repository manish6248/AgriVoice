from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, send_file
from gtts import gTTS
from twilio.rest import Client
import os
import json
import requests
from bs4 import BeautifulSoup
import schedule
import time
import threading
from datetime import datetime
import re
import logging
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/audio/'
app.config['FARMERS_FILE'] = 'farmers.json'
app.config['NOTICES_FILE'] = 'notices.json'
app.config['LAST_SCRAPE_FILE'] = 'last_scrape.json'

# Import credentials from config file
try:
    from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, SERVER_URL, NGROK_AUDIO_URL
    account_sid = TWILIO_ACCOUNT_SID
    auth_token = TWILIO_AUTH_TOKEN
    whatsapp_number = TWILIO_WHATSAPP_NUMBER
    server_url = SERVER_URL
    ngrok_audio_url = NGROK_AUDIO_URL
except ImportError:
    # Fallback to environment variables or defaults
    import os
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    server_url = os.environ.get('SERVER_URL', 'http://localhost:5000')
    ngrok_audio_url = "https://6a4f-2409-40d0-12e7-b690-ad0d-cc77-f41e-13cf.ngrok-free.app/audio"

# This will be updated when the app starts
def update_server_url():
    try:
        import requests
        import json
        import time
        
        # Wait for ngrok to start
        time.sleep(5)
        
        # Try to get the ngrok public URL from its API
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            data = response.json()
            
            if 'tunnels' in data and len(data['tunnels']) > 0:
                global server_url
                # Get the HTTPS URL
                for tunnel in data['tunnels']:
                    if tunnel['proto'] == 'https':
                        server_url = tunnel['public_url']
                        print(f"Updated server URL to: {server_url}")
                        break
        except:
            print("Could not connect to ngrok API. Make sure ngrok is running.")
    except ImportError:
        print("Requests module not available for ngrok URL detection.")


# Initialize Twilio client
try:
    client = Client(account_sid, auth_token)
    logging.info("Twilio client initialized successfully")
except Exception as e:
    logging.error(f"Twilio client initialization failed: {e}")
    client = None

# Initialize JSON files if they don't exist
for file_path in [app.config['FARMERS_FILE'], app.config['NOTICES_FILE']]:
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump([], f)

if not os.path.exists(app.config['LAST_SCRAPE_FILE']):
    with open(app.config['LAST_SCRAPE_FILE'], 'w') as f:
        json.dump({"last_notice_id": ""}, f)

# Ensure static/audio directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

def send_whatsapp_voice_note(phone_number, text_to_speak, message_body=None):
    """
    Send a WhatsApp voice note by converting text to speech
    Returns True if successful, False otherwise
    """
    if not client:
        logging.warning(f"Skipping WhatsApp voice note to {phone_number} - Twilio client not initialized")
        return False
    
    try:
        # Format the phone number correctly for WhatsApp
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'
        
        # Generate audio from text
        tts = gTTS(text=text_to_speak, lang='hi')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        audio_filename = f'voice_note_{timestamp}.mp3'
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        tts.save(audio_path)
        
        # Create media URL for the voice note
        media_url = f'{server_url}/static/audio/{audio_filename}'
        
        # Default message body if none provided
        if not message_body:
            message_body = "कृषि सूचना वॉइस नोट"  # "Agriculture information voice note" in Hindi
        
        # Send the voice note as a media message
        message = client.messages.create(
            from_=whatsapp_number,
            body=message_body,
            media_url=media_url,
            to=phone_number
        )
        
        logging.info(f"Sent WhatsApp voice note to {phone_number}: SID {message.sid}")
        return True
    except Exception as e:
        logging.error(f"Failed to send WhatsApp voice note to {phone_number}: {e}")
        return False

def get_latest_notices(count=3):
    """
    Get the latest notices from the notices.json file
    Returns a list of the latest 'count' notices
    """
    try:
        with open(app.config['NOTICES_FILE'], 'r') as f:
            notices = json.load(f)
        
        # Sort notices by time in descending order (newest first)
        notices.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        # Return the latest 'count' notices
        return notices[:count]
    except Exception as e:
        logging.error(f"Error getting latest notices: {e}")
        return []

def send_latest_notices_to_farmer(phone_number, farmer_name):
    """
    Send the latest 3 notices to a specific farmer as voice notes
    """
    latest_notices = get_latest_notices(3)
    
    if not latest_notices:
        logging.warning(f"No notices available to send to {phone_number}")
        return False
    
    # Send welcome message first
    welcome_message = f"नमस्ते {farmer_name}! आपका AGRIVOICE में स्वागत है। यहां आपके लिए नवीनतम कृषि सूचनाएँ हैं:"
    send_whatsapp_message(phone_number, welcome_message)
    
    # Send each notice as a voice note with a small delay to avoid rate limiting
    for i, notice in enumerate(latest_notices):
        try:
            # Send as voice note
            message_body = f"सूचना {i+1}/3"  # "Notice 1/3" in Hindi
            send_whatsapp_voice_note(phone_number, notice['text'], message_body)
            
            # Also send the original audio file if available
            if 'audio' in notice:
                media_url = f"{server_url}/static/audio/{notice['audio']}"
                send_whatsapp_message(phone_number, f"सूचना {i+1}/3 का ऑडियो", media_url)
            
            time.sleep(2)  # Small delay between messages
            
        except Exception as e:
            logging.error(f"Error sending notice to {phone_number}: {e}")
    
    return True

def send_voice_notices_to_all_farmers():
    """
    Send the latest 3 notices as voice notes to all registered farmers
    """
    latest_notices = get_latest_notices(3)
    
    if not latest_notices:
        logging.warning("No notices available to send to farmers")
        return False
    
    try:
        with open(app.config['FARMERS_FILE'], 'r') as f:
            farmers = json.load(f)
        
        if not farmers:
            logging.warning("No farmers registered to send notices to")
            return False
        
        for farmer in farmers:
            threading.Thread(
                target=send_latest_notices_to_farmer, 
                args=(farmer['phone'], farmer['name']), 
                daemon=True
            ).start()
            time.sleep(1)  # Small delay between farmers to avoid rate limiting
        
        logging.info(f"Started sending voice notices to {len(farmers)} farmers")
        return True
    except Exception as e:
        logging.error(f"Error sending voice notices to farmers: {e}")
        return False

def scrape_notices():
    """
    Scrape notices from agriwelfare.gov.in and send audio to registered farmers
    """
    logging.info("Scraping notices from agriwelfare.gov.in...")
    try:
        # Get last scraped notice ID
        with open(app.config['LAST_SCRAPE_FILE'], 'r') as f:
            last_scrape_data = json.load(f)
            last_notice_id = last_scrape_data.get("last_notice_id", "")
        
        # Fetch webpage
        url = "https://agriwelfare.gov.in/en/Recent"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch website: {response.status_code}")
            return
        
        # Fetch notices via AJAX
        ajax_url = "https://agriwelfare.gov.in/en/getRecent?vacancy_type=Y"
        ajax_response = requests.post(ajax_url, headers=headers)
        
        if ajax_response.status_code != 200:
            logging.error(f"Failed to fetch notices via AJAX: {ajax_response.status_code}")
            return
        
        try:
            notices_data = ajax_response.json()
            if 'data' not in notices_data:
                logging.error("No data found in AJAX response")
                logging.debug(f"Response content: {ajax_response.text[:500]}")
                return
                
            notices = notices_data['data']
            logging.info(f"Found {len(notices)} notices via AJAX")
            
            new_notices = []
            newest_notice_id = last_notice_id
            
            # Process notices
            for notice in notices:
                notice_id = str(notice.get('Id', '')) or str(hash(notice.get('Title', '')))
                if notice_id == last_notice_id:
                    break
                
                notice_text = notice.get('Title', '')
                if not notice_text:
                    continue
                    
                if newest_notice_id == last_notice_id:
                    newest_notice_id = notice_id
                    
                new_notices.append({
                    'id': notice_id,
                    'text': notice_text,
                    'publish_date': notice.get('PublishDate', ''),
                    'file_path': notice.get('FilePath', '')
                })
            
            # Process new notices
            for notice in reversed(new_notices):
                notice_text = f"{notice['text']} - Published on {notice['publish_date']}"
                
                # Generate audio
                tts = gTTS(text=notice_text, lang='hi')
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                audio_filename = f'notice_{timestamp}.mp3'
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
                tts.save(audio_path)
                
                # Add to notices.json
                with open(app.config['NOTICES_FILE'], 'r+') as f:
                    notices = json.load(f)
                    notices.append({
                        'text': notice_text,
                        'audio': audio_filename,
                        'time': timestamp,
                        'source': 'agriwelfare.gov.in',
                        'original_link': notice['file_path']
                    })
                    f.seek(0)
                    json.dump(notices, f)
                    f.truncate()
            
            # Update last scraped notice ID
            if new_notices and newest_notice_id != last_notice_id:
                with open(app.config['LAST_SCRAPE_FILE'], 'w') as f:
                    json.dump({"last_notice_id": newest_notice_id}, f)
                logging.info(f"Added {len(new_notices)} new notices")
                
                # Send voice notes to all farmers with the new notices
                threading.Thread(target=send_voice_notices_to_all_farmers, daemon=True).start()
            else:
                logging.info("No new notices found")
                
        except ValueError as e:
            logging.error(f"Failed to parse AJAX response as JSON: {e}")
            logging.debug(f"Response content: {ajax_response.text[:500]}")
            
    except Exception as e:
        logging.error(f"Error scraping notices: {e}")

def schedule_scraper():
    """
    Run the scraper every 6 hours
    """
    schedule.every(6).hours.do(scrape_notices)
    logging.info("Scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(60)

# Schedule automatic sending of audio files every day
def schedule_audio_sender():
    """
    Run the audio sender every day at 9 AM
    """
    schedule.every().day.at("09:00").do(send_recent_audio_to_all_farmers)
    logging.info("Audio sender scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start background threads
scraper_thread = threading.Thread(target=schedule_scraper, daemon=True)
scraper_thread.start()

audio_sender_thread = threading.Thread(target=schedule_audio_sender, daemon=True)
audio_sender_thread.start()

@app.before_first_request
def initial_tasks():
    # Start initial scrape
    threading.Thread(target=scrape_notices, daemon=True).start()
    
    # Send recent audio files to all farmers on startup
    threading.Thread(target=send_recent_audio_to_all_farmers, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    phone = request.form['phone'].replace(' ', '')  # Remove spaces
    district = request.form['district']
    
    # Normalize phone number to +91 format
    if not phone.startswith('+91'):
        if phone.startswith('91'):
            phone = '+' + phone
        elif phone.startswith('0'):
            phone = '+91' + phone[1:]
        else:
            phone = '+91' + phone.lstrip('+')
    
    # Validate Indian phone number
    if not re.match(r'^\\+91[6-9]\\d{9}$', phone):
        logging.warning(f"Invalid phone number: {phone}")
        return redirect(url_for('index'))
    
    # Check for duplicates
    with open(app.config['FARMERS_FILE'], 'r') as f:
        farmers = json.load(f)
        if any(farmer['phone'] == phone for farmer in farmers):
            logging.warning(f"Phone number already registered: {phone}")
            return redirect(url_for('index'))
    
    # Register new farmer
    with open(app.config['FARMERS_FILE'], 'r+') as f:
        farmers = json.load(f)
        farmers.append({'name': name, 'phone': phone, 'district': district})
        f.seek(0)
        json.dump(farmers, f)
        f.truncate()
    logging.info(f"Registered new farmer: {name}, {phone}")
    
    # Send the latest 3 notices to the newly registered farmer as voice notes
    threading.Thread(target=send_latest_notices_to_farmer, args=(phone, name), daemon=True).start()
    
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate():
    notice_text = request.form['notice']
    tts = gTTS(text=notice_text, lang='hi')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    audio_filename = f'notice_{timestamp}.mp3'
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
    tts.save(audio_path)

    with open(app.config['NOTICES_FILE'], 'r+') as f:
        notices = json.load(f)
        notices.append({
            'text': notice_text,
            'audio': audio_filename,
            'time': timestamp,
            'source': 'manual'
        })
        f.seek(0)
        json.dump(notices, f)
        f.truncate()

    # Send to farmers as voice notes
    with open(app.config['FARMERS_FILE'], 'r') as f:
        farmers = json.load(f)
        for farmer in farmers:
            threading.Thread(
                target=send_whatsapp_voice_note,
                args=(
                    farmer["phone"],
                    notice_text,
                    "नई कृषि सूचना वॉइस नोट"  # "New agriculture information voice note" in Hindi
                ),
                daemon=True
            ).start()

    return redirect(url_for('index'))

@app.route('/archive')
def archive():
    with open(app.config['NOTICES_FILE'], 'r') as f:
        notices = json.load(f)
    return render_template('archive.html', notices=notices)

@app.route('/scrape-now')
def scrape_now():
    """
    Manually trigger the scraper
    """
    threading.Thread(target=scrape_notices, daemon=True).start()
    return redirect(url_for('index'))

@app.route('/send-latest-notices/<phone>')
def send_latest_notices(phone):
    """
    Manually send the latest 3 notices to a specific farmer
    """
    with open(app.config['FARMERS_FILE'], 'r') as f:
        farmers = json.load(f)
        farmer = next((f for f in farmers if f['phone'] == phone), None)
    
    if farmer:
        threading.Thread(target=send_latest_notices_to_farmer, args=(phone, farmer['name']), daemon=True).start()
        return "Sending latest notices to farmer..."
    else:
        return "Farmer not found"

@app.route('/send-voice-notices-to-all')
def send_voice_notices_to_all():
    """
    Manually send voice notes of the latest 3 notices to all farmers
    """
    logging.info("Manual trigger: Sending voice notices to all farmers")
    threading.Thread(target=send_voice_notices_to_all_farmers, daemon=True).start()
    return "Sending voice notices to all farmers..."

@app.route('/direct-send-audio/<phone>')
def direct_send_audio(phone):
    """
    Directly send audio files to a specific phone number for testing
    """
    logging.info(f"Direct audio test to phone: {phone}")
    
    # Get 3 most recent audio files
    audio_files = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.mp3'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            audio_files.append({
                'filename': file,
                'path': file_path,
                'created': os.path.getctime(file_path)
            })
    
    audio_files.sort(key=lambda x: x['created'], reverse=True)
    recent_files = audio_files[:3]
    
    if not recent_files:
        return "No audio files found"
    
    # Send test message
    send_whatsapp_message(phone, "Test audio message")
    
    # Send each audio file
    for i, audio in enumerate(recent_files):
        media_url = f"{ngrok_audio_url}/{audio['filename']}"
        message = f"Test audio file {i+1}/3"
        result = send_whatsapp_message(phone, message, media_url)
        logging.info(f"Sent audio file {i+1} to {phone}: {result}")
        time.sleep(3)
    
    return f"Sent {len(recent_files)} audio files to {phone}"

def broadcast_latest_notices():
    """
    Sends the latest 3 voice notices to every farmer in the database.
    """
    with open(app.config['FARMERS_FILE'], 'r') as f:
        farmers = json.load(f)

    for farmer in farmers:
        phone = farmer.get("phone")
        name = farmer.get("name", "किसान मित्र")
        logging.info(f"Sending top 3 notices to {name} at {phone}")
        send_latest_notices_to_farmer(phone, name)

@app.route('/send-top-notices-all')
def send_top_notices_all():
    threading.Thread(target=broadcast_latest_notices, daemon=True).start()
    return "Started sending top 3 notices to all farmers."

@app.route('/send-recent-audio-files')
def send_recent_audio_files():
    """
    Send the 3 most recent audio files directly to all farmers
    """
    threading.Thread(target=send_recent_audio_to_all_farmers, daemon=True).start()
    return "Started sending recent audio files to all farmers."

def send_recent_audio_to_all_farmers():
    """
    Sends the 3 most recent audio files in static/audio to all farmers
    """
    try:
        logging.info("Starting to send recent audio files to all farmers")
        
        # Get all audio files from static/audio directory
        audio_files = []
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            if file.endswith('.mp3'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
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
        
        logging.info(f"Found {len(recent_files)} recent audio files to send")
        
        # Get all farmers
        with open(app.config['FARMERS_FILE'], 'r') as f:
            farmers = json.load(f)
        
        if not farmers:
            logging.warning("No farmers registered to send audio files to")
            return
        
        logging.info(f"Sending audio files to {len(farmers)} farmers")
        
        # Create direct URL to the audio files using the public URL
        public_url = request.url_root.rstrip('/') if request else "http://localhost:5000"
        if 'ngrok' not in public_url and ngrok_audio_url:
            # If not using ngrok URL in the request, use the configured one
            public_url = ngrok_audio_url.rsplit('/', 1)[0]
        
        # Send audio files to each farmer
        for farmer in farmers:
            phone = farmer.get("phone")
            name = farmer.get("name", "किसान मित्र")
            
            logging.info(f"Sending audio files to {name} at {phone}")
            
            # Send welcome message
            welcome_message = f"नमस्ते {name}! यहां आपके लिए नवीनतम कृषि ऑडियो फ़ाइलें हैं:"
            send_result = send_whatsapp_message(phone, welcome_message)
            
            if not send_result:
                logging.error(f"Failed to send welcome message to {phone}, skipping this farmer")
                continue
            
            # Send each audio file
            for i, audio in enumerate(recent_files):
                # Create full URL for the audio file
                media_url = f"{public_url}/audio/{audio['filename']}"
                logging.info(f"Sending audio file: {media_url}")
                
                message = f"ऑडियो फ़ाइल {i+1}/3"
                result = send_whatsapp_message(phone, message, media_url)
                if result:
                    logging.info(f"Successfully sent audio file {i+1} to {phone}")
                else:
                    logging.error(f"Failed to send audio file {i+1} to {phone}")
                time.sleep(3)  # Increased delay between messages
            
            logging.info(f"Sent {len(recent_files)} audio files to {name} at {phone}")
            time.sleep(2)  # Increased delay between farmers
        
        logging.info(f"Finished sending audio files to {len(farmers)} farmers")
    except Exception as e:
        logging.error(f"Error sending audio files: {e}")
        import traceback
        logging.error(traceback.format_exc())

@app.route('/audio')
def audio_index():
    """List all available audio files"""
    files = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.mp3'):
            files.append(file)
    
    files_html = "<br>".join([f'<a href="/audio/{file}">{file}</a>' for file in files])
    return f"""
    <h1>Available Audio Files</h1>
    {files_html}
    <hr>
    <h2>Test Audio Sending</h2>
    <form action="/test-audio-send" method="post">
        <label>Phone Number (with country code): <input type="text" name="phone" value="+917739006104"></label><br>
        <input type="submit" value="Send Test Audio">
    </form>
    """

@app.route('/audio/<filename>')
def send_audio(filename):
    """Serve a specific audio file"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), mimetype="audio/mpeg")

@app.route('/test-message')
def test_message():
    # Use a placeholder phone number
    test_phone = os.environ.get('TEST_PHONE', '+917739006104')  # Using a real number from farmers.json
    result = send_whatsapp_message(test_phone, 'यह एक परीक्षण संदेश है')
    if result:
        return 'Sent test message successfully'
    else:
        return 'Failed to send test message, check logs'

@app.route('/test-audio-send', methods=['POST'])
def test_audio_send():
    """Test endpoint to send a single audio file to a specific number"""
    phone = request.form.get('phone', '+917739006104')
    
    # Get the most recent audio file
    audio_files = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.mp3'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            audio_files.append({
                'filename': file,
                'path': file_path,
                'created': os.path.getctime(file_path)
            })
    
    if not audio_files:
        return "No audio files found to send"
    
    # Sort by creation time (newest first)
    audio_files.sort(key=lambda x: x['created'], reverse=True)
    audio = audio_files[0]
    
    # Create direct URL to the audio file
    public_url = request.url_root.rstrip('/')
    if 'ngrok' not in public_url:
        # If not using ngrok URL, use the configured one
        public_url = ngrok_audio_url.rsplit('/', 1)[0]
    
    media_url = f"{public_url}/audio/{audio['filename']}"
    logging.info(f"Testing with media URL: {media_url}")
    
    # Send the audio file
    result = send_whatsapp_message(phone, f"Test audio file: {audio['filename']}", media_url)
    
    if result:
        return f"""
        <h1>Audio Test Sent</h1>
        <p>Sent audio file <strong>{audio['filename']}</strong> to <strong>{phone}</strong></p>
        <p>Media URL: <a href="{media_url}" target="_blank">{media_url}</a></p>
        <p>Check your WhatsApp to see if you received it.</p>
        <p><a href="/audio">Back to audio list</a></p>
        """
    else:
        return f"""
        <h1>Failed to Send Audio</h1>
        <p>Failed to send audio file <strong>{audio['filename']}</strong> to <strong>{phone}</strong></p>
        <p>Check the logs for more details.</p>
        <p><a href="/audio">Back to audio list</a></p>
        """

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("dotenv module not installed. Environment variables must be set manually.")
    
    # Try to import and use the ngrok helper
    try:
        from ngrok_helper import setup_ngrok
        setup_ngrok(app)
        print("ngrok setup complete. Check the ngrok interface for your public URL.")
    except ImportError:
        print("ngrok_helper module not found. Run without ngrok integration.")
    except Exception as e:
        print(f"Error setting up ngrok: {e}")
    
    # Start the Flask app
    app.run(debug=True)