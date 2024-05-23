import logging
import requests
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def check_telegram_connectivity():
    """Check connectivity to Telegram API."""
    try:
        response = requests.get(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/getMe", timeout=10)
        response.raise_for_status()
        logging.info("Telegram connectivity check passed")
        logging.info(f"Response: {response.json()}")
        return True
    except requests.RequestException as ex:
        logging.error(f"Telegram connectivity check failed: {ex}")
        return False

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    logging.info("Checking Telegram connectivity")
    if check_telegram_connectivity():
        return {
            'statusCode': 200,
            'body': 'Telegram connectivity check passed'
        }
    else:
        return {
            'statusCode': 500,
            'body': 'Telegram connectivity check failed'
        }

if __name__ == '__main__':
    check_telegram_connectivity()
