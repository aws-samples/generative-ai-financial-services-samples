from parameters.logger import get_logger
from parameters.parameters import config
from awsmanager.manager import AWSClientSession, AWSSecretsManager
from parameters.parameters import AWS_DEFAULT_REGION
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


logging = get_logger(__name__)
aws_session = AWSClientSession()


def create_aoss_client(session):
    # AOSS Settings
    ASM = AWSSecretsManager(session)
    aoss_secrets = ASM.get_secret_credentials(config["secret"]["aoss_credentials_name"])
    # TO BE DELETED
    print(f"<<<ONLY FOR VALIDATION>>>{aoss_secrets}")
    aoss_host = aoss_secrets["aoss_host"]
    aoss_port = aoss_secrets["aoss_port"]
    aoss_index = aoss_secrets["aoss_index"]
    aoss_region = AWS_DEFAULT_REGION
    service = "aoss"
    credentials = session.obtain_credentials()
    aoss_auth = AWSV4SignerAuth(credentials, aoss_region, service)
    _client = OpenSearch(
        hosts=[{"host": aoss_host, "port": aoss_port}],
        http_auth=aoss_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
        timeout=50000,
    )
    return _client, aoss_index
