# AgentCore Policy with MCP Server Target

## Overview

This tutorial demonstrates how to use **Amazon Bedrock AgentCore Policy** with an **MCP Server Target** instead of a Lambda Target.

### Architecture

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Agent     │────>│  AgentCore Gateway  │────>│  MCP Server     │
│  (Client)   │ JWT │  + Cedar Policy     │ MCP │  (FastMCP)      │
└─────────────┘     └─────────────────────┘     └─────────────────┘
```

### Lambda Target vs MCP Server Target

| Aspect | Lambda Target | MCP Server Target |
|--------|---------------|-------------------|
| Backend | AWS Lambda Function | MCP Server (HTTP) |
| Protocol | Lambda Invoke | MCP over HTTP |
| Tool Discovery | Inline Schema | SynchronizeGatewayTargets API |
| Hosting | AWS Managed | Self-hosted / AgentCore Runtime |

## Prerequisites

- AWS Account with appropriate IAM permissions
- Existing AgentCore Gateway with OAuth Authorizer
- Python 3.10+
- bedrock-agentcore-starter-toolkit (for Runtime deployment)

## Folder Structure

```
05-Fine-Grained-Access-Control-MCP/
├── README.md                 # This file
├── tutorial.ipynb            # Main tutorial notebook
├── mcp_server.py             # FastMCP server with refund tool
├── deploy_mcp_runtime.py     # Deploy to AgentCore Runtime
├── test_mcp_target.py        # Step-by-step test script
├── requirements.txt          # Python dependencies
└── scripts/                  # Utility modules
    ├── __init__.py
    ├── auth_utils.py         # Token handling
    ├── gateway_utils.py      # Gateway + MCP target functions
    └── policy_utils.py       # Policy Engine + Cedar policies
```

## Quick Start

### Option A: Deploy to AgentCore Runtime (Recommended)

This deploys the MCP server to AWS AgentCore Runtime, providing a public URL automatically.

```bash
# Step 1: Deploy MCP server to Runtime
python test_mcp_target.py --step 1r

# Step 2: Test MCP server
python test_mcp_target.py --step 2

# Step 3-5: Create target, policy, and test
python test_mcp_target.py --step 3
python test_mcp_target.py --step 4
python test_mcp_target.py --step 5

# Or run all steps automatically
python test_mcp_target.py --all --use-runtime
```

### Option B: Local Server with ngrok

```bash
# Terminal 1: Run MCP server
python mcp_server.py

# Terminal 2: Expose via ngrok (for Gateway access)
ngrok http 8000

# Use the ngrok URL when prompted in step 3
python test_mcp_target.py --step 3 --mcp-url https://abc.ngrok.io/mcp
```

### Run Tutorial Notebook

Open `tutorial.ipynb` in Jupyter and follow the steps.

## MCP Server Tools

The included MCP server (`mcp_server.py`) provides these tools:

| Tool | Description | Parameters |
|------|-------------|------------|
| `refund` | Process a refund | `amount`, `order_id`, `reason` |
| `get_order` | Get order details | `order_id` |
| `approve_claim` | Approve insurance claim | `claim_id`, `amount`, `risk_level` |

## Key APIs

### Create MCP Server Target

```python
target_config = {
    "mcp": {
        "mcpServer": {
            "url": "https://your-mcp-server.com/mcp"
        }
    }
}

response = gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="MyMCPTarget",
    targetConfiguration=target_config,
    credentialProviderConfigurations=[{"credentialProviderType": "NONE"}]
)
```

### Synchronize Gateway Targets

```python
gateway_client.synchronize_gateway_targets(
    gatewayIdentifier=gateway_id,
    targetId=target_id
)
```

## Cedar Policy Examples

### Amount-based Control

```cedar
permit(principal,
    action == AgentCore::Action::"RefundMCPServerTarget___refund",
    resource == AgentCore::Gateway::"arn:aws:...")
when {
    context.input.amount <= 1000
};
```

### Risk-level Control

```cedar
permit(principal,
    action == AgentCore::Action::"RefundMCPServerTarget___approve_claim",
    resource == AgentCore::Gateway::"arn:aws:...")
when {
    context.input.risk_level != "critical"
};
```

## Troubleshooting

### Gateway cannot reach MCP Server

- Ensure MCP server has a public URL (use ngrok or deploy to EC2)
- Check security groups allow inbound traffic on port 8000
- Verify URL is correctly URL-encoded

### Tool Synchronization Failed

- Check MCP server is running and accessible
- Verify MCP protocol version is supported (2025-06-18 or 2025-03-26)
- Use `GetGatewayTarget` API to check synchronization status

### Policy Not Enforced

- Verify Policy Engine is attached to Gateway in ENFORCE mode
- Check policy is in ACTIVE state
- Confirm tool name matches: `{TargetName}___{tool_name}`

## References

- [AWS Docs: MCP Server Targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/servers)
- [Cedar Policy Language](https://www.cedarpolicy.com/)
