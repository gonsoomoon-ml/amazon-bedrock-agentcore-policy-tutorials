# Amazon Bedrock AgentCore Policy Tutorials

## Repository Location
`/home/ubuntu/amazon-bedrock-agentcore-policy-tutorials/`

## Repository Structure

```
amazon-bedrock-agentcore-policy-tutorials/
├── 00_setup/                    # Shared virtual environment setup
├── 01-Lambda-Target/            # Lambda Target Tutorial
│   ├── 01-Setup-Gateway-Lambda.ipynb      # Infrastructure only
│   ├── 02-Policy-Enforcement.ipynb        # Policy Engine + testing
│   ├── setup-gateway.py
│   └── img/
├── 02-MCP-Server-Target/        # MCP Server Target Tutorial
│   ├── 01-Setup-MCP-Runtime-Gateway.ipynb # Runtime + Gateway setup
│   ├── 02-Policy-Enforcement.ipynb        # Policy Engine + testing
│   ├── deploy_mcp_runtime.py
│   ├── mcp_server.py
│   └── Dockerfile
├── common/                      # Shared utility scripts
│   ├── auth_utils.py            # Token/authentication (get_bearer_token, decode_token, make_gateway_request)
│   ├── cognito_utils.py         # Cognito Lambda triggers
│   ├── gateway_utils.py         # Gateway management
│   └── policy_utils.py          # Policy Engine utilities
└── docs/                        # Cedar policy, Cognito, JWT docs
```

## Key Design Decisions

1. **Notebook Split**: Each tutorial has 2 notebooks:
   - `01-Setup-*` - Infrastructure only (no Policy Engine)
   - `02-Policy-Enforcement` - Policy Engine setup + Cedar policy testing
   - Reason: Users who don't want policy enforcement only run notebook 01

2. **Shared Imports**: All notebooks use:
   ```python
   sys.path.insert(0, str(Path.cwd().parent))
   from common.auth_utils import ...
   from common.policy_utils import ...
   ```

3. **Tool Naming Convention**: MCP tools use format `{TargetName}___{tool_name}`
   - Example: `RefundMCPServerTarget___approve_claim`

## Cedar Policy Patterns

```cedar
# String Equality
context.input.risk_level == "low"

# Pattern Matching
context.input.risk_level like "*low*"

# OR Conditions
context.input.risk_level == "low" || context.input.risk_level == "medium"

# Negation
!(context.input.risk_level == "critical")

# JWT Claims (Principal Tags)
principal.hasTag("department_name") && principal.getTag("department_name") == "finance"
```

## Security Notes

- `.gitignore` excludes `*.json` and `.bedrock_agentcore.yaml` (contain secrets)
- Config files with credentials are generated at runtime, never committed
- Rotate Cognito client secrets if exposed

## AWS Resources Created by Tutorials

| Resource | Service |
|----------|---------|
| AgentCore Gateway | bedrock-agentcore-control |
| Gateway Target (Lambda/MCP) | bedrock-agentcore-control |
| Policy Engine | bedrock-agentcore-control |
| AgentCore Runtime | bedrock-agentcore-control |
| OAuth2 Credential Provider | bedrock-agentcore-control |
| Cognito User Pool | cognito-idp |
| Lambda Function (RefundLambda) | lambda |
| Lambda Trigger (custom claims) | lambda |

## Cleanup Commands

```bash
# Delete Gateway Target
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier <ID> --target-id <ID> --region us-east-1

# Delete Gateway
aws bedrock-agentcore-control delete-gateway --gateway-identifier <ID> --region us-east-1

# Delete OAuth2 Credential Provider
aws bedrock-agentcore-control delete-oauth2-credential-provider --name <NAME> --region us-east-1

# Delete AgentCore Runtime
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id <ID> --region us-east-1

# Delete Cognito (domain first, then pool)
aws cognito-idp delete-user-pool-domain --user-pool-id <ID> --domain <DOMAIN> --region us-east-1
aws cognito-idp delete-user-pool --user-pool-id <ID> --region us-east-1
```

## Git Status

- Initial commit with split notebooks completed
- Ready to push to remote repository
