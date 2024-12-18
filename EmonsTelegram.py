from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

app = Flask(__name__)

load_dotenv()

FLASK_ENV = os.getenv('FLASK_ENV', 'production').lower()

if FLASK_ENV == 'development':
    logging_level = logging.DEBUG
    app.config['DEBUG'] = True  
else:
    logging_level = logging.INFO
    app.config['DEBUG'] = False

logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
IP_TOKEN = os.getenv('IP_TOKEN')
DEFAULT_IP = os.getenv('DEFAULT_IP')
DEFAULT_PORT = os.getenv('DEFAULT_PORT')
REST_DOMAIN = os.getenv('REST_DOMAIN')
AUTH_CODE = os.getenv('AUTH_CODE')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')

API_URL = "{}:{}/{}".format(DEFAULT_IP, DEFAULT_PORT, REST_DOMAIN)


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
            logging.info(f"Notification sent to chat ID: {chat_id}.")
            logging.info(f"Response result from telegram action: {response.json()}")
        else:
            logging.error(f"Error sending message to {chat_id}: {response.status_code}")
            logging.error(f"Response: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")
        abort(500, description="Failed to send notification.")


def hit_ip_address_api(tenant):
    headers = {
        "Content-Type": "application/json",
        "tenant": tenant,
        "Authorize": AUTH_CODE,
        "token": AUTH_TOKEN
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
                logging.info(f"API token matched: {api_token}")
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


@app.route('/send_alarm', methods=['POST'])
def send_alarm():
    if not hit_ip_address_api(tenant='alif'):
        return jsonify({"error": "API validation failed, alarm not sent."}), 400
    
    data = request.json 
    logging.debug("Received JSON Data:\n%s", json.dumps(data, indent=4))
    logging.info("The data object is:\n%s", json.dumps(data, indent=4, ensure_ascii=False))
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    device_data = data.get('device_data', {})
    logging.info("The device data is:\n%s", json.dumps(device_data, indent=4, ensure_ascii=False))
    if not device_data:
        return jsonify({"error": "No device data provided"}), 400
    
    if not device_data or len(device_data) == 0:
        return jsonify({"error": "No Data Alarm Provided"}), 400
    
    recipients = data.get('recipients', [])
    logging.info("The recipients are:\n%s", json.dumps(recipients, indent=4, ensure_ascii=False))
    if not recipients:
        return jsonify({"error": "No recipients provided"}), 400
    
    site_name = data.get('site_name', 'N/A')
    logging.info(f"The site name is {site_name}")
    
    for alarm in device_data:
        value = alarm.get('value', 0)
        if value < 0:
            logging.warning("Value is less than 0. Notification will not be sent.")
            continue
        
        raw_send_date = alarm.get('send_date', 'N/A')
        try:
            if "." in raw_send_date:
                parsed_date = datetime.strptime(raw_send_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                parsed_date = datetime.strptime(raw_send_date, "%Y-%m-%dT%H:%M:%SZ")
            
            formatted_send_date = parsed_date.strftime("%d %B %Y %H:%M:%S")
        except ValueError:
            formatted_send_date = raw_send_date

        raw_lane = alarm.get('lane', 'N/A')
        logging.info(f"The raw lane is {raw_lane}")
        formatted_lane = f"{raw_lane[0]}-{raw_lane[1]}" if len(raw_lane) == 2 else raw_lane
        logging.info(f"The formatted lane is {formatted_lane}")
        
        message_template = (
        f"🚨*Alarm Detected*\n\n"
        f"{'Name'.ljust(10)}: {escape_markdown(alarm.get('name', 'N/A').capitalize())}\n"
        f"{'Line'.ljust(13)}: {escape_markdown(formatted_lane)}\n"
        f"{'Value'.ljust(11)}: {escape_markdown(str(alarm.get('value', 'N/A')))} Volt\n"
        f"{'Status'.ljust(11)}: {escape_markdown(alarm.get('status', 'N/A'))} 🔴\n"
        f"{'Date'.ljust(12)}: {escape_markdown(formatted_send_date)}\n"
        f"{'Location'.ljust(9)}: {escape_markdown(site_name)} \- {escape_markdown(str(alarm.get('location', 'N/A')))}\n"
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
    app.run(debug=(FLASK_ENV == 'development'), port=5000)
