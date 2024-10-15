# Alarm Notification Service

This project is a Flask-based API that sends alarm notifications to Telegram chat groups or individual recipients. It also performs IP address validation using an external API and ensures proper logging depending on the environment (development or production).

# Features

1. Telegram Notifications: Sends alarm messages to configured chat groups or recipients using Telegram Bot API.
2. IP Address Validation: Verifies the request by hitting an external IP address API before sending notifications.
3. Environment-based Logging:
4. In development mode: Debugging enabled with detailed logging.
5. In production mode: Only essential logs are recorded.
6. Alarm Information: Sends details such as device name, status, voltage value, and timestamp.

# Example Output

```
🚨*Alarm Detected*
Name      : Voltage Monitor
Line      : A-B
Value     : 220 Volt
Status    : Critical 🔴
Date      : 15 October 2024 14:30:01
Location  : Main Site - N/A
```
