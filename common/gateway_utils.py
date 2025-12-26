"""
Gateway Utility Module for MCP Server Targets

Amazon Bedrock AgentCore Gateway setup and management functions,
including MCP server target support.
"""

import time
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from botocore.exceptions import ClientError


def get_gateway_details(gateway_control_client, gateway_id: str) -> Dict[str, Any]:
    """
    Get current Gateway details.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID

    Returns:
        Gateway details dictionary
    """
    return gateway_control_client.get_gateway(gatewayIdentifier=gateway_id)


def wait_for_gateway_ready(
    gateway_control_client,
    gateway_id: str,
    max_wait: int = 300,
    poll_interval: int = 5
) -> bool:
    """
    Wait for Gateway to reach READY state.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        max_wait: Maximum wait time (seconds)
        poll_interval: Status check interval (seconds)

    Returns:
        Whether READY state was reached
    """
    terminal_states = {"READY", "FAILED", "UPDATE_UNSUCCESSFUL"}
    start_time = time.time()

    while time.time() - start_time < max_wait:
        gateway = get_gateway_details(gateway_control_client, gateway_id)
        status = gateway.get("status", "UNKNOWN")
        print(f"  Gateway status: {status}")

        if status == "READY":
            return True
        if status in terminal_states:
            print(f"  ✗ Gateway reached terminal state: {status}")
            return False

        time.sleep(poll_interval)

    print("  ✗ Gateway wait timeout")
    return False


def validate_and_fix_gateway_authorizer(
    gateway_control_client,
    gateway_id: str,
    region: str,
    user_pool_id: str,
    client_id: str,
    scope: str = ""
) -> bool:
    """
    Validate and fix Gateway Authorizer settings.

    Cognito Access Token doesn't have 'aud' claim,
    so setting allowedAudience will reject valid tokens.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        region: AWS region
        user_pool_id: Cognito User Pool ID
        client_id: Cognito App Client ID
        scope: OAuth2 scope (optional)

    Returns:
        True if settings are valid or successfully fixed
    """
    print("\nGateway Authorizer Validation")
    print("=" * 70)

    gw = get_gateway_details(gateway_control_client, gateway_id)
    jwt_config = gw.get("authorizerConfiguration", {}).get("customJWTAuthorizer", {})

    # Check current settings
    discovery_url = jwt_config.get("discoveryUrl")
    allowed_clients = jwt_config.get("allowedClients", [])
    allowed_audience = jwt_config.get("allowedAudience", [])
    allowed_scopes = jwt_config.get("allowedScopes", [])

    print(f"  Discovery URL: {discovery_url or 'Not set'}")
    print(f"  Allowed Clients: {allowed_clients}")
    print(f"  Allowed Audience: {allowed_audience}")
    print(f"  Allowed Scopes: {allowed_scopes}")

    # Expected Discovery URL
    expected_discovery_url = (
        f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )

    # Check if fix is needed
    needs_fix = False
    reasons = []

    if not discovery_url:
        needs_fix = True
        reasons.append("Discovery URL not set")
    elif discovery_url != expected_discovery_url:
        needs_fix = True
        reasons.append("Discovery URL mismatch")

    if client_id not in allowed_clients:
        needs_fix = True
        reasons.append(f"Client ID {client_id} not in allowed list")

    if allowed_audience:
        needs_fix = True
        reasons.append("allowedAudience is set (Cognito Access Token has no 'aud' claim)")

    if not needs_fix:
        print("\n✓ Gateway Authorizer settings are valid")
        return True

    print("\n⚠️  Fix needed:")
    for reason in reasons:
        print(f"   - {reason}")

    # Fix settings
    print("\n⏳ Updating Gateway Authorizer...")

    new_auth_config = {
        "customJWTAuthorizer": {
            "discoveryUrl": expected_discovery_url,
            "allowedClients": [client_id],
        }
    }

    if scope:
        new_auth_config["customJWTAuthorizer"]["allowedScopes"] = [scope]

    try:
        gateway_control_client.update_gateway(
            gatewayIdentifier=gateway_id,
            name=gw.get("name"),
            roleArn=gw.get("roleArn"),
            protocolType=gw.get("protocolType", "MCP"),
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration=new_auth_config,
            policyEngineConfiguration=gw.get("policyEngineConfiguration", {}),
        )

        print("\n⏳ Waiting for Gateway READY state...")
        if wait_for_gateway_ready(gateway_control_client, gateway_id):
            print("\n✓ Gateway Authorizer updated successfully")
            return True
        else:
            print("\n✗ Gateway did not reach READY state")
            return False

    except ClientError as e:
        print(f"\n✗ Gateway update error: {e}")
        return False


def attach_policy_engine_to_gateway(
    gateway_control_client,
    gateway_id: str,
    policy_engine_arn: str,
    mode: str = "ENFORCE"
) -> bool:
    """
    Attach Policy Engine to Gateway.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        policy_engine_arn: Policy Engine ARN
        mode: Policy mode ('LOG_ONLY' or 'ENFORCE')

    Returns:
        Whether attachment was successful
    """
    print("\nAttaching Policy Engine to Gateway")
    print("=" * 70)

    gateway_config = get_gateway_details(gateway_control_client, gateway_id)

    # Check if already attached
    existing_pe = gateway_config.get("policyEngineConfiguration", {})
    if existing_pe.get("arn"):
        print(f"✓ Policy Engine already attached: {existing_pe.get('arn')}")
        print(f"  Mode: {existing_pe.get('mode', 'N/A')}")
        return True

    print(f"  Policy Engine ARN: {policy_engine_arn}")
    print(f"  Mode: {mode}")

    try:
        gateway_control_client.update_gateway(
            gatewayIdentifier=gateway_id,
            name=gateway_config.get("name"),
            roleArn=gateway_config.get("roleArn"),
            protocolType=gateway_config.get("protocolType", "MCP"),
            authorizerType=gateway_config.get("authorizerType", "CUSTOM_JWT"),
            authorizerConfiguration=gateway_config.get("authorizerConfiguration"),
            policyEngineConfiguration={"arn": policy_engine_arn, "mode": mode},
        )

        print("✓ Gateway update request complete")
        print("\n⏳ Waiting for Gateway READY state...")

        if wait_for_gateway_ready(gateway_control_client, gateway_id):
            print("✓ Policy Engine attached successfully")
            return True
        else:
            print("✗ Gateway did not reach READY state")
            return False

    except ClientError as e:
        print(f"✗ Gateway update error: {e}")
        return False


# ============================================================================
# MCP Server Target Functions
# ============================================================================


def create_mcp_server_target(
    gateway_control_client,
    gateway_id: str,
    target_name: str,
    mcp_server_url: str,
    description: str = "",
    auth_type: str = "NONE"
) -> Optional[Dict[str, Any]]:
    """
    Create an MCP Server target on the Gateway.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        target_name: Target name
        mcp_server_url: MCP server endpoint URL (must be URL-encoded)
        description: Target description
        auth_type: Authentication type ('NONE' or 'OAUTH2')

    Returns:
        Created target details, or None on failure
    """
    print(f"\nCreating MCP Server Target: {target_name}")
    print("=" * 70)
    print(f"  MCP Server URL: {mcp_server_url}")
    print(f"  Auth Type: {auth_type}")

    # URL encode the MCP server URL
    encoded_url = quote(mcp_server_url, safe=':/')

    target_config = {
        "mcp": {
            "mcpServer": {
                "url": encoded_url
            }
        }
    }

    # Credential configuration
    if auth_type == "NONE":
        credential_config = [{"credentialProviderType": "NONE"}]
    else:
        # For OAuth2, would need additional configuration
        credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

    try:
        response = gateway_control_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            description=description or f"MCP Server Target: {target_name}",
            targetConfiguration=target_config,
            credentialProviderConfigurations=credential_config,
        )

        target_id = response.get("targetId")
        print(f"\n✓ MCP Server Target created")
        print(f"  Target ID: {target_id}")
        print(f"  Status: {response.get('status')}")

        return response

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        print(f"\n✗ Target creation error: {error_code}")
        print(f"  {error_msg}")
        return None


def synchronize_gateway_targets(
    gateway_control_client,
    gateway_id: str,
    target_id: str
) -> bool:
    """
    Synchronize Gateway targets to discover MCP server tools.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        target_id: Target ID to synchronize

    Returns:
        Whether synchronization was initiated successfully
    """
    print(f"\nSynchronizing Gateway Target: {target_id}")
    print("=" * 70)

    try:
        gateway_control_client.synchronize_gateway_targets(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )

        print("✓ Synchronization initiated (async)")
        print("  Use get_gateway_target to check progress")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        print(f"\n✗ Synchronization error: {error_code}")
        print(f"  {error_msg}")
        return False


def get_gateway_target(
    gateway_control_client,
    gateway_id: str,
    target_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get Gateway target details.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        target_id: Target ID

    Returns:
        Target details, or None if not found
    """
    try:
        return gateway_control_client.get_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
    except ClientError:
        return None


def list_gateway_targets(
    gateway_control_client,
    gateway_id: str
) -> List[Dict[str, Any]]:
    """
    List all Gateway targets.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID

    Returns:
        List of targets
    """
    print(f"\nListing Gateway Targets")
    print("=" * 70)

    try:
        response = gateway_control_client.list_gateway_targets(
            gatewayIdentifier=gateway_id
        )

        targets = response.get("targets", [])
        print(f"  Found {len(targets)} target(s)")

        for target in targets:
            print(f"    - {target.get('name')} (ID: {target.get('targetId')}, Status: {target.get('status')})")

        return targets

    except ClientError as e:
        print(f"✗ List targets error: {e}")
        return []


def wait_for_target_ready(
    gateway_control_client,
    gateway_id: str,
    target_id: str,
    max_wait: int = 120,
    poll_interval: int = 5
) -> bool:
    """
    Wait for Gateway target to reach READY state.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        target_id: Target ID
        max_wait: Maximum wait time (seconds)
        poll_interval: Status check interval (seconds)

    Returns:
        Whether READY state was reached
    """
    print(f"\n⏳ Waiting for Target READY state...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        target = get_gateway_target(gateway_control_client, gateway_id, target_id)
        if not target:
            print(f"  ⚠️  Target not found: {target_id}")
            return False

        status = target.get("status", "UNKNOWN")
        print(f"  Target status: {status}")

        if status == "READY":
            print("✓ Target is READY")
            return True

        if status in ["FAILED", "CREATE_FAILED"]:
            print(f"✗ Target failed: {target.get('statusReason', 'Unknown')}")
            return False

        time.sleep(poll_interval)

    print("✗ Target wait timeout")
    return False


def delete_gateway_target(
    gateway_control_client,
    gateway_id: str,
    target_id: str
) -> bool:
    """
    Delete a Gateway target.

    Args:
        gateway_control_client: bedrock-agentcore-control boto3 client
        gateway_id: Gateway ID
        target_id: Target ID

    Returns:
        Whether deletion was successful
    """
    try:
        gateway_control_client.delete_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
        print(f"✓ Target deleted: {target_id}")
        return True
    except ClientError as e:
        print(f"⚠️  Target deletion failed {target_id}: {e}")
        return False
