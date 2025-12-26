# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains Jupyter notebook tutorials for implementing fine-grained access control using Amazon Bedrock AgentCore Policy with Cedar policies. The tutorials demonstrate how to control AI agent actions based on JWT claims (principal attributes), tool arguments (input parameters), and resource context.

## Environment Setup

```bash
# From 00_setup directory
cd 00_setup
chmod +x create_uv_virtual_env.sh
./create_uv_virtual_env.sh AgentCorePolicy

# Activate virtual environment
source .venv/bin/activate

# Run Jupyter
uv run jupyter lab
```

Select the `AgentCorePolicy` kernel when running notebooks.

## Architecture

### Component Flow
```
Cognito (JWT) → AgentCore Gateway (JWT Authorizer + Policy Engine) → Target (Lambda or MCP Server)
```

### Common Utilities (`common/`)

The `common/` module provides shared boto3 wrapper functions:

- **auth_utils.py**: OAuth2 token acquisition (`get_bearer_token`), JWT decoding, Gateway JSON-RPC requests (`make_gateway_request`), response analysis
- **gateway_utils.py**: Gateway CRUD operations, MCP server target management, synchronization helpers
- **policy_utils.py**: Policy Engine lifecycle, Cedar policy CRUD, cleanup utilities
- **cognito_utils.py**: Lambda trigger creation for custom JWT claims (requires Cognito V3_0 triggers for M2M flows)

### AWS Services Used

- **bedrock-agentcore-control**: boto3 client for Gateway and Policy Engine management
- **cognito-idp**: User Pool configuration and Lambda triggers
- **lambda**: Custom claims Lambda function deployment

## Cedar Policy Patterns

Policies use Cedar syntax with AgentCore-specific context:

```cedar
// Check input parameters
permit(principal, action, resource)
when { context.input.amount <= 1000 };

// Check JWT claims via principal tags
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};

// Pattern matching
permit(principal, action, resource)
when { context.input.risk_level like "*low*" };
```

## Key Implementation Notes

- Cognito Access Tokens lack an `aud` claim; do not set `allowedAudience` in JWT authorizer configuration
- M2M (machine-to-machine) flows require Cognito Lambda trigger V3_0 (Essentials or Plus tier)
- MCP servers must use `stateless_http=True` for AgentCore Gateway compatibility
- Gateway targets require synchronization after creation to discover MCP tools
- Policy Engine modes: `LOG_ONLY` for testing, `ENFORCE` for production
