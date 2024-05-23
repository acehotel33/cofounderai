import logging
import openai
import os
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize the OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv('COFOUNDERAI_GPT_API_KEY'))

def lambda_handler(event, context):
    """AWS Lambda handler function for testing OpenAI connectivity."""
    logging.info("Received event: %s", json.dumps(event))

    try:
        # Test OpenAI connection by making a simple API call
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system", 
                "content": "say Hello World!",
            }]
        )
        logging.info("OpenAI response: %s", response)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'OpenAI connectivity check passed',
                'response': response.choices[0].message.content
            })
        }
    except Exception as e:
        logging.error("OpenAI connectivity check failed: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'OpenAI connectivity check failed',
                'error': str(e)
            })
        }

if __name__ == "__main__":
    # For local testing
    event = {}
    context = None
    print(lambda_handler(event, context))
