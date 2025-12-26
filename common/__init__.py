"""
MCP Server Policy Control - Utility Scripts
"""

from .auth_utils import (
    get_bearer_token,
    decode_token,
    make_gateway_request,
    analyze_response,
    display_test_result,
)
from .gateway_utils import (
    get_gateway_details,
    wait_for_gateway_ready,
    validate_and_fix_gateway_authorizer,
    attach_policy_engine_to_gateway,
    create_mcp_server_target,
    synchronize_gateway_targets,
    list_gateway_targets,
)
from .policy_utils import (
    get_policy_engine,
    create_cedar_policy,
    wait_for_policy_active,
    delete_policy,
    cleanup_existing_policies,
    ensure_policy_engine,
)

__all__ = [
    # Auth
    "get_bearer_token",
    "decode_token",
    "make_gateway_request",
    "analyze_response",
    "display_test_result",
    # Gateway
    "get_gateway_details",
    "wait_for_gateway_ready",
    "validate_and_fix_gateway_authorizer",
    "attach_policy_engine_to_gateway",
    "create_mcp_server_target",
    "synchronize_gateway_targets",
    "list_gateway_targets",
    # Policy
    "get_policy_engine",
    "create_cedar_policy",
    "wait_for_policy_active",
    "delete_policy",
    "cleanup_existing_policies",
    "ensure_policy_engine",
]
