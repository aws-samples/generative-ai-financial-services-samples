import boto3
import json
from streamlit_cognito_auth import CognitoAuthenticator


class Auth:

    @staticmethod
    def get_authenticator(secret_id):
        """
        Get Cognito parameters from Secrets Manager and
        returns a CognitoAuthenticator object.
        """
        # Get Cognito parameters from Secrets Manager
        secretsmanager_client = boto3.client("secretsmanager")
        response = secretsmanager_client.get_secret_value(
            SecretId=secret_id,
        )
        secret_string = json.loads(response['SecretString'])
        pool_id = secret_string['userPoolId']
        app_client_id = secret_string['appClientId']
        app_client_secret = secret_string['appClientSecret']

        # Initialise CognitoAuthenticator
        authenticator = CognitoAuthenticator(
            pool_id=pool_id,
            app_client_id=app_client_id,
            app_client_secret=app_client_secret,
        )

        return authenticator