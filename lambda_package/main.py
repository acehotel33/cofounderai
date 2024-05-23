import os
import json
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Setup logging
logging.basicConfig(level=logging.INFO)

def lambda_handler(event, context):
    logging.info("Starting MongoDB connectivity test")
    try:
        # MongoDB connection string from environment variable
        mongo_uri = os.getenv('COFOUNDERAI_MONGO_URI')
        
        # Create a MongoDB client with extended timeout settings
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=30000, connectTimeoutMS=30000)

        # Test the connection by listing the databases
        databases = client.list_database_names()
        
        # If successful, return the list of databases
        logging.info("MongoDB connectivity check passed")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'MongoDB connectivity check passed',
                'databases': databases
            })
        }
    except ConnectionFailure as e:
        # If there's a connection failure, return the error message
        logging.error(f"Connection to MongoDB failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'MongoDB connectivity check failed',
                'error': str(e)
            })
        }
    except Exception as e:
        # If there's any other error, return the error message
        logging.error(f"An error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'An unexpected error occurred',
                'error': str(e)
            })
        }

if __name__ == '__main__':
    # For local testing, set the MONGO_URI environment variable
    print(lambda_handler(None, None))
