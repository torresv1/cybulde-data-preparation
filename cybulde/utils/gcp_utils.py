from google.cloud import secretmanager


def access_secret_version(project_id: str, secret_id: str, version_id: str = "1") -> str:
    """
        Access the payload for the given secret version if one exists.
        Args:
            project_id (str): GCP project ID
            secret_id (str): ID of the secret
            version_id (str): Version of the secret (e.g., "latest")
    Returns:
        str: The secret payload"""

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Return the decoded payload.
    payload = response.payload.data.decode("UTF-8")
    return payload
