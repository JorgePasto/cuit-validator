import asyncio
from app.connectors.wsaa_connector import WSAAConnector

def manual_test_wsaa():
    connector = WSAAConnector()
    try:
        token_data = asyncio.run(connector.get_token())
        print("Token obtained successfully:")
        print(f"Token: {token_data.token}")
        print(f"Sign: {token_data.sign}")
        print(f"Expiration: {token_data.expiration_time}")
    except Exception as e:
        print(f"Error during WSAA test: {str(e)}")

if __name__ == "__main__":
    manual_test_wsaa()