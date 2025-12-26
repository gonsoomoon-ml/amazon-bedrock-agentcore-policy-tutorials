"""
Simple MCP Server for AgentCore Policy Testing

This MCP server provides a refund tool that can be used to test
Cedar policy enforcement through AgentCore Gateway.

Usage:
    python mcp_server.py

The server runs on http://0.0.0.0:8000/mcp
"""

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
# stateless_http=True is required for AgentCore Gateway compatibility
mcp = FastMCP(
    name="RefundMCPServer",
    host="0.0.0.0",
    port=8000,
    stateless_http=True
)


@mcp.tool()
def refund(amount: float, order_id: str, reason: str = "Customer request") -> dict[str, Any]:
    """
    Process a refund for an order.

    Args:
        amount: The refund amount in dollars
        order_id: The order ID to refund
        reason: The reason for the refund

    Returns:
        A dictionary containing the refund status and details
    """
    logger.info(f"Processing refund: amount={amount}, order_id={order_id}, reason={reason}")

    # Simulate refund processing
    result = {
        "status": "approved",
        "refund_id": f"REF-{order_id}-{int(amount)}",
        "amount": amount,
        "order_id": order_id,
        "reason": reason,
        "message": f"Refund of ${amount} for order {order_id} has been processed successfully."
    }

    logger.info(f"Refund result: {json.dumps(result)}")
    return result


@mcp.tool()
def get_order(order_id: str) -> dict[str, Any]:
    """
    Get order details by order ID.

    Args:
        order_id: The order ID to look up

    Returns:
        A dictionary containing order details
    """
    logger.info(f"Getting order: order_id={order_id}")

    # Simulate order lookup
    result = {
        "order_id": order_id,
        "status": "delivered",
        "total": 150.00,
        "items": [
            {"name": "Widget A", "quantity": 2, "price": 50.00},
            {"name": "Widget B", "quantity": 1, "price": 50.00}
        ],
        "customer": "customer-123"
    }

    return result


@mcp.tool()
def approve_claim(claim_id: str, amount: float, risk_level: str = "low") -> dict[str, Any]:
    """
    Approve an insurance claim.

    Args:
        claim_id: The claim ID to approve
        amount: The claim amount
        risk_level: Risk level (low, medium, high, critical)

    Returns:
        A dictionary containing the approval status
    """
    logger.info(f"Approving claim: claim_id={claim_id}, amount={amount}, risk_level={risk_level}")

    result = {
        "claim_id": claim_id,
        "status": "approved",
        "amount": amount,
        "risk_level": risk_level,
        "message": f"Claim {claim_id} for ${amount} has been approved."
    }

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Refund MCP Server")
    print("=" * 60)
    print(f"Server URL: http://0.0.0.0:8000/mcp")
    print(f"Available tools: refund, get_order, approve_claim")
    print("=" * 60)

    # Run the server with streamable-http transport
    mcp.run(transport="streamable-http")
