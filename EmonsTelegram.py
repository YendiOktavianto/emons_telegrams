from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

# init
app = Flask(__name__)

# Load env var 
load_dotenv()

# Ensure env var are loaded perfectly
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
IP_TOKEN = os.getenv('IP_TOKEN')
DEFAULT_IP = os.getenv('DEFAULT_IP')
DEFAULT_PORT = os.getenv('DEFAULT_PORT')
REST_DOMAIN = os.getenv('REST_DOMAIN')
AUTH_CODE = os.getenv('AUTH_CODE')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')

API_URL = "{}:{}/{}".format(DEFAULT_IP, DEFAULT_PORT, REST_DOMAIN)

# Logger for security tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



# Fungsi untuk mengirim notifikasi ke penerima tertentu
def send_telegram_notification(message, chat_id):
    telegram_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'MarkdownV2'
    }
    
    try:
        response = requests.post(telegram_url, data=payload, timeout=5)
        response.raise_for_status()
        if response.status_code == 200:
            print(f"Notifikasi berhasil dikirim ke chat ID: {chat_id}.")
        else:
            print(f"Error sending message to {chat_id}: {response.status_code}")
            print(f"Response: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")
        abort(500, description="Failed to send notification.")

# Fungsi untuk melakukan hit ke API yang ditunjukkan di gambar
def hit_ip_address_api(tenant):
    headers = {
        "Content-Type": "application/json",
        "tenant": tenant,
        "Authorization": "{AUTH_CODE}",
        "token": "{AUTH_TOKEN}"
    }

    payload = {
        "username": "test1",
        "nvalue": "172.0.0.1",
        "token": IP_TOKEN,
        "type": 1,
        "tenant": tenant
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data and response_data.get('status') and response_data.get('param'):
            api_token = response_data['param']['token']
            if api_token == IP_TOKEN:
                return True 
            else:
                logging.warning("API token mismatch.")
                return False
        else:
            logging.warning("Status API tidak true atau response kosong.")
            return False
    except requests.RequestException as e:
        logging.error(f"Error contacting API: {e}")
        abort(500, description="API request failed.")
        return False

# Route to handle alarm notification sent to telegram
@app.route('/send_alarm', methods=['POST'])
def send_alarm():
    if not hit_ip_address_api(tenant='alif'):
        return jsonify({"error": "API validation failed, alarm not sent."}), 400
    
    data = request.json 
    # print("Received JSON Data:", data)
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    device_data = data.get('device_data', {})
    if not device_data:
        return jsonify({"error": "No device data provided"}), 400
    
    recipients = data.get('recipients', [])
    if not recipients:
        return jsonify({"error": "No recipients provided"}), 400
    
    # Ambil field site_name
    site_name = data.get('site_name', 'N/A')
    
    raw_send_date = device_data.get('send_date', 'N/A')
    try:
        if "." in raw_send_date:
            parsed_date = datetime.strptime(raw_send_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            parsed_date = datetime.strptime(raw_send_date, "%Y-%m-%dT%H:%M:%SZ")
        
        formatted_send_date = parsed_date.strftime("%d %B %Y %H:%M:%S")
    except ValueError:
        formatted_send_date = raw_send_date

    raw_lane = device_data.get('lane', 'N/A')
    formatted_lane = f"{raw_lane[0]}-{raw_lane[1]}" if len(raw_lane) == 2 else raw_lane
    
    message_template = (
    f"🚨*Alarm Detected*\n\n"
    f"{'Name'.ljust(10)}: {escape_markdown(device_data.get('name', 'N/A').capitalize())}\n"
    f"{'Line'.ljust(13)}: {escape_markdown(formatted_lane)}\n"
    f"{'Value'.ljust(11)}: {escape_markdown(str(device_data.get('value', 'N/A')))} Volt\n"
    f"{'Status'.ljust(11)}: {escape_markdown(device_data.get('status', 'N/A'))} 🔴\n"
    f"{'Date'.ljust(12)}: {escape_markdown(formatted_send_date)}\n"
    f"{'Location'.ljust(9)}: {escape_markdown(site_name)} \- {escape_markdown(str(device_data.get('location', 'N/A')))}\n"
    )
    
    for recipient in recipients:
        name = recipient.get('name', 'N/A')
        chat_id = recipient.get('chat_id')
        
        if not chat_id:
            logging.warning(f"Missing chat ID for recipient: {recipient.get('name', 'N/A')}")
            continue
        
        send_telegram_notification(message_template, chat_id)
    
    return jsonify({"message": "Alarm notifications sent successfully"}), 200

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

if __name__ == '__main__':
    app.run(debug=False, port=5000)
