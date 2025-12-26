"""
Deploy MCP Server to AgentCore Runtime with OAuth

This script deploys the RefundMCPServer to AgentCore Runtime using the
bedrock_agentcore_starter_toolkit with Cognito OAuth authentication.

Usage:
    python deploy_mcp_runtime.py [--delete]

Prerequisites:
    - bedrock_agentcore_starter_toolkit installed
    - mcp_server.py in the same directory
    - AWS credentials configured
"""

import sys
import os
import time
import json
import boto3
from pathlib import Path
from urllib.parse import quote

# ============================================================================
# Configuration
# ============================================================================

RUNTIME_NAME = "refund_mcp_server"
ENTRYPOINT = "mcp_server.py"
REGION = "us-east-1"
COGNITO_POOL_NAME = "RefundMCPServerPool"

# Source directory (current directory)
SCRIPT_DIR = Path(__file__).parent
MCP_SERVER_FILE = SCRIPT_DIR / "mcp_server.py"


def print_header(message: str):
    print(f"\n{'=' * 60}")
    print(message)
    print('=' * 60)


def print_success(message: str):
    print(f"✓ {message}")


def print_error(message: str):
    print(f"✗ {message}")


def print_info(message: str):
    print(f"  {message}")


# ============================================================================
# Cognito Setup Functions
# ============================================================================

def setup_cognito_for_runtime() -> dict:
    """Set up Cognito User Pool and App Client for Runtime authentication."""
    print_header("Setting up Cognito for Runtime OAuth")

    cognito_client = boto3.client("cognito-idp", region_name=REGION)

    # Check for existing pool
    pools = cognito_client.list_user_pools(MaxResults=60).get("UserPools", [])
    existing_pool = next((p for p in pools if p["Name"] == COGNITO_POOL_NAME), None)

    if existing_pool:
        pool_id = existing_pool["Id"]
        print_info(f"Using existing User Pool: {pool_id}")
    else:
        # Create new User Pool
        print_info("Creating new Cognito User Pool...")
        response = cognito_client.create_user_pool(
            PoolName=COGNITO_POOL_NAME,
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": False,
                }
            },
            AutoVerifiedAttributes=["email"],
            UsernameAttributes=["email"],
            MfaConfiguration="OFF",
        )
        pool_id = response["UserPool"]["Id"]
        print_success(f"User Pool created: {pool_id}")

    # Get or create domain
    try:
        cognito_client.describe_user_pool_domain(Domain=f"refund-mcp-{pool_id.split('_')[1].lower()}")
        domain = f"refund-mcp-{pool_id.split('_')[1].lower()}"
        print_info(f"Using existing domain: {domain}")
    except cognito_client.exceptions.ResourceNotFoundException:
        domain = f"refund-mcp-{pool_id.split('_')[1].lower()}"
        try:
            cognito_client.create_user_pool_domain(
                Domain=domain,
                UserPoolId=pool_id
            )
            print_success(f"Domain created: {domain}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print_info(f"Domain already exists: {domain}")
            else:
                raise

    # Create or get Resource Server for scopes
    resource_server_id = "refund-mcp"
    try:
        cognito_client.create_resource_server(
            UserPoolId=pool_id,
            Identifier=resource_server_id,
            Name="Refund MCP Server",
            Scopes=[
                {"ScopeName": "invoke", "ScopeDescription": "Invoke MCP tools"}
            ]
        )
        print_success("Resource Server created")
    except cognito_client.exceptions.ResourceExistsException:
        print_info("Resource Server already exists")

    # Get or create App Client
    clients = cognito_client.list_user_pool_clients(
        UserPoolId=pool_id, MaxResults=60
    ).get("UserPoolClients", [])

    client_name = "refund-mcp-client"
    existing_client = next((c for c in clients if c["ClientName"] == client_name), None)

    if existing_client:
        client_id = existing_client["ClientId"]
        # Get client details including secret
        client_details = cognito_client.describe_user_pool_client(
            UserPoolId=pool_id, ClientId=client_id
        )["UserPoolClient"]
        client_secret = client_details.get("ClientSecret")
        print_info(f"Using existing App Client: {client_id}")
    else:
        # Create App Client with client credentials flow
        response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=client_name,
            GenerateSecret=True,
            AllowedOAuthFlows=["client_credentials"],
            AllowedOAuthScopes=[f"{resource_server_id}/invoke"],
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=["COGNITO"],
        )
        client_id = response["UserPoolClient"]["ClientId"]
        client_secret = response["UserPoolClient"]["ClientSecret"]
        print_success(f"App Client created: {client_id}")

    # Build URLs
    discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
    token_endpoint = f"https://{domain}.auth.{REGION}.amazoncognito.com/oauth2/token"

    cognito_config = {
        "pool_id": pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "discovery_url": discovery_url,
        "token_endpoint": token_endpoint,
        "domain": domain,
        "scope": f"{resource_server_id}/invoke",
        "region": REGION,
    }

    # Save Cognito config
    config_file = SCRIPT_DIR / "cognito_config.json"
    config_file.write_text(json.dumps(cognito_config, indent=2))
    print_success(f"Cognito config saved: {config_file}")

    return cognito_config


def get_bearer_token(cognito_config: dict) -> str:
    """Get Bearer token using client credentials flow."""
    import requests

    data = {
        "grant_type": "client_credentials",
        "client_id": cognito_config["client_id"],
        "client_secret": cognito_config["client_secret"],
        "scope": cognito_config["scope"],
    }

    response = requests.post(
        cognito_config["token_endpoint"],
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
    )
    response.raise_for_status()
    return response.json()["access_token"]


# ============================================================================
# Runtime Deployment Functions
# ============================================================================

def get_agentcore_client():
    """Get bedrock-agentcore-control client."""
    return boto3.client("bedrock-agentcore-control", region_name=REGION)


def list_runtimes(client):
    """List all agent runtimes."""
    response = client.list_agent_runtimes()
    return response.get("agentRuntimeSummaries", [])


def get_runtime_by_name(client, name: str):
    """Find runtime by name."""
    runtimes = list_runtimes(client)
    for runtime in runtimes:
        if runtime.get("agentRuntimeName") == name:
            return runtime
    return None


def get_runtime_details(client, runtime_id: str):
    """Get detailed runtime information."""
    return client.get_agent_runtime(agentRuntimeId=runtime_id)


def delete_runtime(client, runtime_id: str):
    """Delete an agent runtime."""
    print(f"Deleting runtime: {runtime_id}")
    client.delete_agent_runtime(agentRuntimeId=runtime_id)

    max_wait = 180
    start = time.time()
    while time.time() - start < max_wait:
        try:
            client.get_agent_runtime(agentRuntimeId=runtime_id)
            print("  Waiting for deletion...")
            time.sleep(10)
        except client.exceptions.ResourceNotFoundException:
            print_success("Runtime deleted")
            return True
        except Exception as e:
            if "ResourceNotFoundException" in str(type(e).__name__):
                print_success("Runtime deleted")
                return True
            time.sleep(10)

    print_error("Deletion timeout")
    return False


def create_requirements_file():
    """Create requirements.txt file for the runtime."""
    requirements_file = SCRIPT_DIR / "requirements_runtime.txt"
    requirements = [
        "mcp>=1.0.0",
        "uvicorn>=0.30.0",
        "starlette>=0.45.0",
    ]
    requirements_file.write_text("\n".join(requirements))
    print_info(f"Created: {requirements_file}")
    return requirements_file


def deploy_with_starter_toolkit(cognito_config: dict):
    """Deploy MCP server using bedrock_agentcore_starter_toolkit."""
    print_header("Deploying with Starter Toolkit")

    try:
        from bedrock_agentcore_starter_toolkit import Runtime
    except ImportError:
        print_error("bedrock_agentcore_starter_toolkit not installed")
        print_info("Install: pip install bedrock-agentcore-starter-toolkit")
        return None

    # Check MCP server exists
    if not MCP_SERVER_FILE.exists():
        print_error(f"MCP server not found: {MCP_SERVER_FILE}")
        return None

    print_info(f"Runtime Name: {RUNTIME_NAME}")
    print_info(f"Entrypoint: {ENTRYPOINT}")
    print_info(f"Region: {REGION}")

    # Create requirements file
    requirements_file = create_requirements_file()

    # Initialize Runtime
    runtime = Runtime()

    # Build OAuth authorizer configuration
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config["client_id"]],
            "discoveryUrl": cognito_config["discovery_url"],
        }
    }

    print("\n[1/2] Configuring Runtime...")

    # Change to script directory for relative paths to work
    original_dir = os.getcwd()
    os.chdir(SCRIPT_DIR)

    try:
        config_response = runtime.configure(
            agent_name=RUNTIME_NAME,
            entrypoint=ENTRYPOINT,
            requirements_file=str(requirements_file.name),
            region=REGION,
            auto_create_ecr=True,
            auto_create_execution_role=True,
            # MCP protocol for Gateway compatibility
            protocol="MCP",
            # OAuth configuration
            authorizer_configuration=auth_config,
            # PUBLIC network mode for MCP server accessibility
            vpc_enabled=False,
            non_interactive=True
        )

        print_success("Configuration completed")
        print_info(f"Config: {config_response.config_path}")
        print_info(f"Dockerfile: {config_response.dockerfile_path}")

        # Launch runtime
        print("\n[2/2] Launching Runtime (Docker build + ECR push + Create)...")
        print_info("This may take 5-10 minutes...")

        launch_response = runtime.launch()

        print_success("Runtime launched!")
        print_info(f"Runtime ARN: {launch_response.agent_arn}")
        print_info(f"Runtime ID: {launch_response.agent_id}")

        return {
            "runtime_id": launch_response.agent_id,
            "runtime_arn": launch_response.agent_arn
        }

    finally:
        os.chdir(original_dir)


def wait_for_runtime_ready(client, runtime_id: str, max_wait: int = 600):
    """Wait for runtime to reach READY state."""
    print(f"\nWaiting for Runtime READY state...")
    start = time.time()
    attempt = 0

    while time.time() - start < max_wait:
        attempt += 1
        try:
            runtime = get_runtime_details(client, runtime_id)
            status = runtime.get("status")
            print(f"  [{attempt}] Status: {status}")

            if status == "READY":
                return runtime
            elif status in ["FAILED", "CREATE_FAILED", "UPDATE_FAILED"]:
                reason = runtime.get("statusReason", "Unknown")
                print_error(f"Runtime failed: {reason}")
                return None

        except Exception as e:
            print_error(f"Status check error: {e}")

        time.sleep(10)

    print_error("Timeout waiting for runtime")
    return None


def save_config(runtime_id: str, runtime_arn: str, cognito_config: dict, endpoint: str = None):
    """Save runtime configuration to file."""
    config_file = SCRIPT_DIR / "runtime_config.json"

    # Build MCP invocation URL from ARN
    encoded_arn = quote(runtime_arn, safe='')
    mcp_invocation_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

    config = {
        "runtime_id": runtime_id,
        "runtime_arn": runtime_arn,
        "runtime_name": RUNTIME_NAME,
        "endpoint": endpoint,
        "mcp_url": mcp_invocation_url,
        "region": REGION,
        "cognito": {
            "pool_id": cognito_config["pool_id"],
            "client_id": cognito_config["client_id"],
            "discovery_url": cognito_config["discovery_url"],
            "token_endpoint": cognito_config["token_endpoint"],
        }
    }

    config_file.write_text(json.dumps(config, indent=2))
    print_info(f"Configuration saved: {config_file}")
    print_info(f"MCP URL: {mcp_invocation_url}")


def main():
    """Main deployment function."""
    print_header("AgentCore Runtime Deployment for MCP Server")
    print_info(f"Runtime Name: {RUNTIME_NAME}")
    print_info(f"Region: {REGION}")
    print_info(f"MCP Server: {MCP_SERVER_FILE}")

    # Check for delete flag
    delete_existing = "--delete" in sys.argv

    # Get client
    client = get_agentcore_client()

    # Check for existing runtime
    existing = get_runtime_by_name(client, RUNTIME_NAME)
    if existing:
        runtime_id = existing.get("agentRuntimeId")
        status = existing.get("status")
        print(f"\nExisting runtime found:")
        print_info(f"ID: {runtime_id}")
        print_info(f"Status: {status}")

        if delete_existing:
            print("\nDeleting existing runtime...")
            if not delete_runtime(client, runtime_id):
                return 1
            # Also clean up config file
            config_yaml = SCRIPT_DIR / ".bedrock_agentcore.yaml"
            if config_yaml.exists():
                config_yaml.unlink()
                print_info("Cleaned up .bedrock_agentcore.yaml")
        else:
            # Get full details
            details = get_runtime_details(client, runtime_id)
            endpoint = details.get("agentRuntimeEndpoint")

            if status == "READY":
                print_success("Runtime is READY")

                # Load or setup Cognito
                cognito_file = SCRIPT_DIR / "cognito_config.json"
                if cognito_file.exists():
                    cognito_config = json.loads(cognito_file.read_text())
                else:
                    cognito_config = setup_cognito_for_runtime()

                save_config(runtime_id, details.get("agentRuntimeArn"), cognito_config, endpoint)
                return 0
            else:
                print_info("Runtime not ready. Use --delete to recreate.")
                return 1

    # Setup Cognito first
    cognito_config = setup_cognito_for_runtime()

    # Deploy new runtime
    result = deploy_with_starter_toolkit(cognito_config)
    if not result:
        print_error("Failed to deploy runtime")
        return 1

    runtime_id = result["runtime_id"]
    runtime_arn = result["runtime_arn"]

    # Wait for ready
    runtime = wait_for_runtime_ready(client, runtime_id)
    if not runtime:
        print_error("Runtime did not reach READY state")
        return 1

    endpoint = runtime.get("agentRuntimeEndpoint")
    print_header("Deployment Complete!")
    print_success("Runtime is READY")
    print_info(f"Runtime ID: {runtime_id}")
    print_info(f"Runtime ARN: {runtime_arn}")

    save_config(runtime_id, runtime_arn, cognito_config, endpoint)

    # Test token
    print("\n[Testing OAuth]")
    try:
        token = get_bearer_token(cognito_config)
        print_success(f"Bearer token obtained ({len(token)} chars)")
    except Exception as e:
        print_error(f"Token error: {e}")

    print("\nNext Steps:")
    print("  1. Use the MCP URL with Bearer token to invoke")
    print("  2. Run: python test_mcp_target.py --step 2")

    return 0


if __name__ == "__main__":
    sys.exit(main())
