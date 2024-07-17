from awsmanager.manager import AWSClientSession, AWSSecretsManager, delete_bucket
from aoss.aoss_logger import get_logger
from aoss.aoss import delete_aoss
from aoss.permissions import delete_permissions
from parameters.parameters import (
    config,
    aoss_params,
    PROXY_TEXT_BUCKET,
    PROXY_PDF_BUCKET,
    text_data_path,
    key_folder,
)
from utils.utils import delete_folder

logging = get_logger(__name__)

vector_store_name = aoss_params["vector_store_name"]
index_name = aoss_params["index_name"]
encryption_policy_name = aoss_params["encryption_policy_name"]
network_policy_name = aoss_params["network_policy_name"]
access_policy_name = aoss_params["access_policy_name"]

# Identity Access, Role & Policy
username = config["identity_access_role_policy"]["username"]
role_name = config["identity_access_role_policy"]["role_name"]
policy_name = config["identity_access_role_policy"]["policy_name"]

aws_session = AWSClientSession()
asm = AWSSecretsManager(aws_session)

delete_aoss(aws_session, vector_store_name, action=True)
asm.delete_secret(aws_secret_name=config["secret"]["aoss_credentials_name"])
delete_bucket(aws_session, PROXY_TEXT_BUCKET)
delete_bucket(aws_session, PROXY_PDF_BUCKET)
delete_permissions(aws_session, username, role_name, policy_name)
delete_folder(text_data_path)
delete_folder(key_folder)
