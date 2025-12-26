# Amazon Bedrock AgentCore Policy Tutorials

This repository contains tutorials for implementing **fine-grained access control** using **Amazon Bedrock AgentCore Policy** with Cedar policies.

## Overview

Amazon Bedrock AgentCore Policy enables you to control what actions AI agents can perform based on:
- **Principal attributes** (JWT claims from identity tokens)
- **Input parameters** (tool arguments)
- **Resource context** (Gateway, targets)

## Tutorials

| Tutorial | Description | Target Type |
|----------|-------------|-------------|
| [01-Lambda-Target](./01-Lambda-Target/) | Policy enforcement with AWS Lambda backend | Lambda Function |
| [02-MCP-Server-Target](./02-MCP-Server-Target/) | Policy enforcement with MCP Server on AgentCore Runtime | MCP Server |

## Architecture

```
                                ┌───────────────────────┐
                                │  Policy Engine        │
                                │  (Cedar Policies)     │
                                └───────────┬───────────┘
                                            │ Attached
                                            ▼
┌─────────────────┐             ┌───────────────────────┐             ┌─────────────────────┐
│   Amazon        │  JWT Token  │  AgentCore Gateway    │             │  Target             │
│   Cognito       │────────────>│  + JWT Authorizer     │────────────>│  (Lambda or MCP)    │
│                 │             │  + Policy Evaluation  │             │                     │
└─────────────────┘             └───────────────────────┘             └─────────────────────┘
```

## Getting Started

### Prerequisites

- AWS Account with appropriate permissions
- Python 3.10+
- [UV](https://github.com/astral-sh/uv) package manager (recommended)

### Setup

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd amazon-bedrock-agentcore-policy-tutorials
   ```

2. **Create virtual environment**
   ```bash
   cd 00_setup
   chmod +x create_uv_virtual_env.sh
   ./create_uv_virtual_env.sh AgentCorePolicy
   ```

3. **Select kernel in Jupyter**
   - Open Jupyter Lab/Notebook
   - Select the `AgentCorePolicy` kernel

4. **Choose a tutorial**
   - For Lambda targets: Start with [01-Lambda-Target](./01-Lambda-Target/)
   - For MCP Server targets: Start with [02-MCP-Server-Target](./02-MCP-Server-Target/)

## Repository Structure

```
amazon-bedrock-agentcore-policy-tutorials/
├── README.md                    # This file
├── 00_setup/                    # Shared environment setup
│   ├── pyproject.toml           # Python dependencies
│   ├── uv.lock                  # Lock file
│   └── create_uv_virtual_env.sh # Setup script
├── docs/                        # Shared documentation
│   ├── cedar-policy.md          # Cedar policy syntax guide
│   ├── cognito.md               # Amazon Cognito concepts
│   ├── jwt-authorizer.md        # JWT Authorizer guide
│   └── troubleshooting.md       # Common issues and solutions
├── common/                      # Shared utility scripts
│   ├── auth_utils.py            # Token and authentication utilities
│   ├── cognito_utils.py         # Cognito Lambda trigger utilities
│   ├── gateway_utils.py         # Gateway management utilities
│   └── policy_utils.py          # Policy Engine utilities
├── 01-Lambda-Target/            # Lambda target tutorial
│   ├── README.md
│   ├── img/                     # Screenshots
│   ├── policy_for_agentcore_tutorial.ipynb
│   └── setup-gateway.py
└── 02-MCP-Server-Target/        # MCP Server target tutorial
    ├── README.md
    ├── img/                     # Screenshots
    ├── mcp_server.py            # MCP Server implementation
    ├── Dockerfile               # Container configuration
    ├── deploy_mcp_runtime.py    # Deployment script
    └── policy_for_mcp_target_tutorial.ipynb
```

## Cedar Policy Patterns

### String Equality
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level == "low"
};
```

### Pattern Matching (like)
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level like "*low*"
};
```

### OR Conditions
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level == "low" ||
    context.input.risk_level == "medium"
};
```

### Negation
```cedar
permit(principal, action, resource)
when {
    !(context.input.risk_level == "critical")
};
```

### JWT Claims (Principal Tags)
```cedar
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};
```

## Documentation

| Document | Description |
|----------|-------------|
| [Cedar Policy](./docs/cedar-policy.md) | Cedar policy language syntax and examples |
| [Amazon Cognito](./docs/cognito.md) | Cognito User Pool, OAuth2, custom claims |
| [JWT Authorizer](./docs/jwt-authorizer.md) | Gateway JWT validation and principal tags |
| [Troubleshooting](./docs/troubleshooting.md) | Common issues and solutions |

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting a pull request.
