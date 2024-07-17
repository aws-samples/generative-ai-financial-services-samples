from botocore.exceptions import NoCredentialsError
from awsmanager.manager import AWSClientSession, create_bucket_if_not_exists
from aoss.permissions import set_permissions
from aoss.aoss import aoss_creation
from parameters.parameters import config, PROXY_TEXT_BUCKET, PROXY_PDF_BUCKET


# Change this to False if you have all permissions set prior
RUN_PERMISSION = config["runtime_action"]["run_permission"]

# Set to True to remove old AOSS if exist
ACTION = config["runtime_action"]["aoss_action"]

# Identity Access, Role & Policy
# username = config["identity_access_role_policy"]["username"]
role_name = config["identity_access_role_policy"]["role_name"]
policy_name = config["identity_access_role_policy"]["policy_name"]
aws_session = AWSClientSession()

try:
    # Step 0
    if RUN_PERMISSION:
        set_permissions(aws_session, role_name, policy_name)

    # Step 1
    try:
        create_bucket_if_not_exists(aws_session, PROXY_TEXT_BUCKET)
        print(f"Bucket {PROXY_TEXT_BUCKET} may already exists.")
    except Exception as e:
        print(e)
        pass

    try:
        create_bucket_if_not_exists(aws_session, PROXY_PDF_BUCKET)
        print(f"Bucket {PROXY_PDF_BUCKET} may already exists.")
    except Exception as e:
        print(e)
        pass

    # Step 2
    aoss_credentials = aoss_creation(
        aws_session, ACTION, config["secret"]["aoss_credentials_name"]
    )
    print(f"Created {aoss_credentials}")
except NoCredentialsError:
    print("Exiting due to credential errors.")


aoss_client = aws_session.get_aoss_client()


# Create and Enable username and password for the OpenSearch dashboard
def create_and_enable_dashboard_credentials(aoss_client):
    try:
        response = aoss_client.create_dashboard_credential(
            DomainName=config["opensearch"]["domain_name"],
            UserName=config["opensearch"]["dashboard_username"],
            Password=config["opensearch"]["dashboard_password"],
        )
        print(response)
    except Exception as e:
        print(e)
