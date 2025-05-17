# AGRIVOICE

A Flask application that sends agricultural notices to farmers via WhatsApp voice notes using Twilio.

## Features

- Converts text notices to voice notes in Hindi
- Sends WhatsApp messages to registered farmers
- Scrapes agricultural notices from government websites
- Web interface for managing notices and farmers
- Automatic ngrok integration for exposing local server

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/agrivoice.git
   cd agrivoice
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Update Twilio credentials in `app.py`:
   ```python
   account_sid = 'your_account_sid'
   auth_token = 'your_auth_token'
   whatsapp_number = 'whatsapp:+14155238886'  # Your Twilio WhatsApp number
   ```

4. Run the application:
   ```
   python app.py
   ```

5. For public access, use ngrok:
   ```
   ./start_ngrok.bat
   ```

## Project Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/audio/`: Generated voice notes
- `farmers.json`: Registered farmers data
- `notices.json`: Agricultural notices
- `ngrok_helper.py`: Helper for ngrok integration

## License

[MIT License](LICENSE)