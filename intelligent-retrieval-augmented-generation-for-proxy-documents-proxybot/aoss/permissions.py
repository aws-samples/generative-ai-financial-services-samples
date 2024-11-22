import json
from aoss.aoss_logger import get_logger


logging = get_logger(__name__)

trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "aoss.amazonaws.com",
                    "cloud9.amazonaws.com",
                    "ec2.amazonaws.com",
                    "osis-pipelines.amazonaws.com",
                ]
            },
            "Action": "sts:AssumeRole",
        }
    ],
}

managed_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreatePolicy",
                "iam:CreateServiceLinkedRole",
                "aoss:*",
                "osis:Ingest",
                "secretsmanager:*",
                "s3:*",
                "textract:*",
                "bedrock:*",
            ],
            "Resource": "*",
        }
    ],
}


def set_permissions(
    session, role_name, policy_name, username=None, username_flag=False
):
    """
    Set permissions for the user.
    :param session: session object
    :param role_name: role name
    :param policy_name: policy name
    :param username: username
    :param username_flag: username flag
    username must be provided if username flag is True
    """

    # Step 1: Check for user
    iam_client = session.get_iam_client()
    sts_client = session.get_sts_client()

    if username_flag:
        print(f"Username: {username}\nRole: {role_name}\nPolicy: {policy_name}")
        try:
            iam_response = iam_client.get_user(UserName=username)
            logging.info(f"User {username} exist. Response: {iam_response}")
        except iam_client.exceptions.NoSuchEntityException:
            logging.error(f"User {username} does not exist. Please check user exists")
            iam_client.create_user(UserName=username)
            logging.error(f"User {username}, creating user...")

        # Step 2: Check for existing credentials and create one if not exist
        existing_credentials = iam_client.list_access_keys(UserName=username)
        if not existing_credentials["AccessKeyMetadata"]:
            logging.info(
                f"No existing credentials found for user {username}. Creating new credentials..."
            )
            iam_client.create_access_key(UserName=username)
        else:
            logging.error(
                f"Existing credentials <{existing_credentials}> found for user {username}."
            )

    # Step 3: Create iam role if using role
    try:
        role_response = iam_client.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        logging.info(f"Role {role_name} created <{role_response}>")
    except iam_client.exceptions.EntityAlreadyExistsException:
        logging.info(f"Role {role_name} already exist.")

    # Step 4: Create policy
    account_id = sts_client.get_caller_identity()["Account"]
    try:
        policy_response = iam_client.create_policy(
            PolicyName=policy_name, PolicyDocument=json.dumps(managed_policy)
        )
        policy_arn = policy_response["Policy"]["Arn"]
        logging.info(f"Policy {policy_name} created. <{policy_response}>")
    except iam_client.exceptions.EntityAlreadyExistsException:
        # TODO - Investigate why this part fails for policy update
        policy_response = iam_client.get_policy(
            PolicyArn=f"arn:aws:iam::{account_id}:policy/{policy_name}"
        )
        policy_arn = policy_response["Policy"]["Arn"]
        logging.info(f"Policy {policy_name} already exist.")

    # Step 5: Attach policy to role or user
    try:
        if username:
            iam_client.attach_user_policy(UserName=username, PolicyArn=policy_arn)
            logging.info(f"Policy {policy_name} attached to role {username}.")
        if role_name:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            logging.info(f"Policy {policy_name} attached to role {role_name}.")
    except iam_client.exceptions.EntityAlreadyExistsException as error:
        logging.error(f"Policy attachment role {error}.")

    return logging.info("Set permissions run complete")


def delete_all_policy_versions(iam_client, policy_arn):
    policy_version_list = iam_client.list_policy_versions(PolicyArn=policy_arn)
    if not policy_version_list["Versions"]:
        logging.info("No versions to delete")
    else:
        for version in policy_version_list["Versions"]:
            if not version["IsDefaultVersion"]:
                iam_client.delete_policy_version(
                    PolicyArn=policy_arn, VersionId=version["VersionId"]
                )
                logging.info(f"Policy version {version['VersionId']} deleted.")
    return logging.info("Policy versions deleted")


def delete_permissions(session, username, role_name, policy_name):
    # delete created role, policy and user
    iam_client = session.get_iam_client()
    sts_client = session.get_sts_client()
    account_id = sts_client.get_caller_identity()["Account"]
    try:
        policy_response = iam_client.get_policy(
            PolicyArn=f"arn:aws:iam::{account_id}:policy/{policy_name}"
        )
        policy_arn = policy_response["Policy"]["Arn"]
        logging.info(f"Policy {policy_name} with {policy_arn} found.")
    except Exception as error:
        policy_arn = None
        logging.error(f"Policy {policy_name} not found.")

    try:
        role_response = iam_client.get_role(RoleName=role_name)
        role_arn = role_response["Role"]["Arn"]
        logging.info(f"Role {role_name} with {role_arn} found.")
    except Exception as error:
        role_arn = None
        logging.error(f"Role {role_name} not found.")

    if policy_arn and role_arn:
        try:
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            logging.info(f"Policy {policy_name} detached from role {role_name}.")
        except Exception as error:
            logging.error(f"Error detaching policy: {error}")

        try:
            iam_client.detach_user_policy(UserName=username, PolicyArn=policy_arn)
            logging.info(f"Policy {policy_name} detached from user {username}.")
        except Exception as error:
            logging.error(f"Error detaching policy {error}, no username -> {username}")

        try:
            if not policy_still_in_use(iam_client, policy_arn):
                delete_all_policy_versions(iam_client, policy_arn)
                logging.info(f"All policy versions deleted.")
                iam_client.delete_policy(PolicyArn=policy_arn)
                logging.info(f"Policy {policy_name} deleted successfully.")
        except Exception as error:
            logging.error(f"Error deleting policy {error}")
            logging.error(f"Check that policy is not being used..")
        try:
            iam_client.delete_role(RoleName=role_name)
            logging.info(f"Role {role_name} deleted.")
        except Exception as error:
            logging.error(f"Error deleting role {error}")


def policy_still_in_use(iam_client, policy_arn):
    for role in iam_client.list_roles():
        for policy in role["AttachedPolicies"]:
            if policy["Arn"] == policy_arn:
                return True

    for user in iam_client.list_users():
        for policy in user["AttachedPolicies"]:
            if policy["Arn"] == policy_arn:
                return True
    return False
