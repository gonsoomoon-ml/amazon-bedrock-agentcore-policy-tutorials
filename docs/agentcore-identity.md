# AgentCore Identity 가이드

## 1. AgentCore Identity란?

**AgentCore Identity**는 AI 에이전트를 위한 포괄적인 ID 및 자격 증명 관리 서비스입니다.

> *"Identity is a key glue that's going to enable agents to be productionized quickly."* — AWS re:Invent 2025

### 핵심 원칙: 위임(Delegation) vs 가장(Impersonation)

AgentCore Identity는 **가장이 아닌 위임** 원칙으로 동작합니다:

| 방식 | 설명 | 보안 |
|------|------|------|
| **가장 (Impersonation)** | 에이전트가 사용자 자격 증명을 직접 사용 | ❌ 위험 |
| **위임 (Delegation)** | 에이전트가 자신으로 인증 + 사용자 컨텍스트 전달 | ✅ 안전 |

```
❌ 가장: Agent uses User's credentials directly
✅ 위임: Agent authenticates as itself + carries User context
```

---

## 2. AgentCore Runtime이란?

**AgentCore Runtime**은 AI 에이전트와 도구를 배포하고 확장하기 위한 **서버리스 런타임**입니다.

### 주요 특징

| 특징 | 설명 |
|------|------|
| **프레임워크 유연성** | Strands, LangChain, LangGraph, CrewAI 등 모든 프레임워크 지원 |
| **모델 독립성** | Amazon Bedrock 또는 외부 모델 사용 가능 |
| **서버리스** | 로컬 프로토타입을 최소한의 코드 변경으로 프로덕션 배포 |
| **통합** | Gateway, Memory, Observability, Tools와 통합 |

### Runtime에서 호스팅 가능한 것

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentCore Runtime                            │
│                                                                  │
│   ┌───────────────────────┐    ┌───────────────────────┐        │
│   │      AI Agent         │    │      MCP Server       │        │
│   │                       │    │                       │        │
│   │  - Strands Agent      │    │  - refund tool        │        │
│   │  - LangGraph Agent    │    │  - get_order tool     │        │
│   │  - CrewAI Agent       │    │  - approve_claim tool │        │
│   └───────────────────────┘    └───────────────────────┘        │
│                                                                  │
│   ┌───────────────────────┐                                     │
│   │    A2A (Agent-to-     │                                     │
│   │     Agent) Server     │                                     │
│   └───────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Gateway와 Runtime의 인증

**AgentCore Gateway**와 **AgentCore Runtime**은 모두 **Inbound Auth**와 **Outbound Auth**가 필요합니다.

### 3.1 Gateway의 Inbound/Outbound Auth

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AgentCore Gateway                                     │
│                                                                              │
│   Inbound Auth                                           Outbound Auth       │
│   (클라이언트 → Gateway)                              (Gateway → 타겟)       │
│                                                                              │
│   ┌────────────┐         ┌────────────┐         ┌────────────────────────┐  │
│   │  클라이언트 │ ──JWT──> │  Gateway   │ ──OAuth─> │  타겟                │  │
│   │            │  검증    │            │   발급   │  - Lambda            │  │
│   └────────────┘         └────────────┘         │  - MCP Server         │  │
│                                                  │  - AgentCore Runtime  │  │
│                                                  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

| 인증 유형 | 방향 | 방식 | 용도 |
|----------|------|------|------|
| **Inbound** | 클라이언트 → Gateway | JWT Authorizer 또는 AWS IAM | 누가 Gateway를 호출하는지 확인 |
| **Outbound** | Gateway → 타겟 | OAuth 또는 IAM Role | Gateway가 타겟(Runtime 등)에 접근 |

### 3.2 Runtime의 Inbound/Outbound Auth

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AgentCore Runtime                                     │
│                       (AI Agent 또는 MCP Server 호스팅)                       │
│                                                                              │
│   Inbound Auth                                           Outbound Auth       │
│   (Gateway → Runtime)                                 (Runtime → 외부 서비스) │
│                                                                              │
│   ┌────────────┐         ┌────────────┐         ┌────────────────────────┐  │
│   │  Gateway   │ ──OAuth─> │  Runtime   │ ──OAuth─> │  외부 서비스          │  │
│   │            │  검증    │ (MCP/Agent)│   발급   │  - Google Calendar    │  │
│   └────────────┘         └────────────┘         │  - GitHub             │  │
│                                                  │  - Slack              │  │
│                                                  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

| 인증 유형 | 방향 | 방식 | 용도 |
|----------|------|------|------|
| **Inbound** | Gateway → Runtime | OAuth 또는 AWS IAM | Gateway가 Runtime을 호출할 수 있는지 확인 |
| **Outbound** | Runtime → 외부 서비스 | OAuth (2-legged 또는 3-legged) | AI Agent가 외부 API에 접근 |

---

## 4. 핵심 컴포넌트

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AgentCore Identity                                  │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Identity        │  │   Authorizer    │  │ Resource Credential         │  │
│  │ Directory       │  │                 │  │ Provider                    │  │
│  │                 │  │ IDP 무관 검증    │  │                             │  │
│  │ 에이전트별      │  │ (Okta, Azure,   │  │ OAuth 자격 증명 저장         │  │
│  │ 고유 Workload ID│  │  Cognito 등)    │  │ (client_id, secret)         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Token Vault                                      ││
│  │                                                                          ││
│  │  - Access/Refresh 토큰, API 키 암호화 저장                                ││
│  │  - 자동 토큰 갱신 (사용자 재인증 불필요)                                   ││
│  │  - Zero Trust: 특정 agent+user 조합만 접근 가능                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Workload Access Token

AgentCore Identity의 핵심 혁신은 **Workload Access Token**입니다:

```
┌─────────────────────────────────────────────────────────────────┐
│  Workload Access Token                                           │
│                                                                  │
│  - 에이전트 ID + 사용자 컨텍스트를 바인딩                          │
│  - 에이전트가 할당된 사용자의 컨텍스트 내에서만 동작               │
│  - 세션 간 가장(impersonation) 방지                              │
│  - 세분화된 접근 제어 가능                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Zero Trust 보안

> 소스나 이전 신뢰 관계와 관계없이 **모든 요청을 검증**

| 단계 | 검증 내용 |
|------|----------|
| 1 | 에이전트 ID 검증 |
| 2 | 사용자 토큰 서명/클레임 검증 |
| 3 | 리소스 접근 권한 검증 |

### 4.3 Token Vault

```
┌─────────────────────────────────────────────────────────────────┐
│  Token Vault 동작 방식                                           │
│                                                                  │
│  1. Agent가 리소스 접근 토큰 요청                                 │
│  2. Token Vault에 기존 토큰이 있으면 → 즉시 반환                  │
│  3. 기존 토큰이 없으면 → 사용자 동의 URL 반환                      │
│  4. 사용자가 동의하면 → 토큰 저장 및 반환                         │
│  5. 토큰 만료 시 → Refresh Token으로 자동 갱신                    │
│                                                                  │
│  ⚠️ Zero Trust: agent+user 조합별로 격리                         │
│     Agent A + User 1의 토큰 ≠ Agent B + User 1의 토큰            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 이 튜토리얼의 아키텍처

### 5.1 전체 흐름

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              전체 인증 흐름                                      │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────┐                                                                 │
│  │  Gateway   │  (1) JWT 발급                                                   │
│  │  Cognito   │ ────────────┐                                                   │
│  └────────────┘             │                                                   │
│                             ▼                                                   │
│  ┌────────────┐  (2) JWT   ┌────────────┐                      ┌────────────┐  │
│  │  클라이언트 │ ─────────> │  Gateway   │                      │  Runtime   │  │
│  │            │            │            │                      │  Cognito   │  │
│  └────────────┘            └─────┬──────┘                      └─────┬──────┘  │
│                                  │                                   │         │
│                 (3) JWT Authorizer 검증                              │         │
│                                  │                                   │         │
│                 (4) Identity에서 자격 증명 조회                       │         │
│                                  ▼                                   │         │
│                            ┌────────────┐                            │         │
│                            │  Identity  │                            │         │
│                            │ (Credential│                            │         │
│                            │  Provider) │                            │         │
│                            └─────┬──────┘                            │         │
│                                  │                                   │         │
│                 (5) client_id, secret 반환                           │         │
│                                  │                                   │         │
│                                  ▼                                   │         │
│                 (6) OAuth 토큰 요청 ─────────────────────────────────>│         │
│                                                                      │         │
│                 (7) Access Token 발급 <──────────────────────────────┘         │
│                                  │                                             │
│                                  ▼                                             │
│                            ┌────────────┐                                      │
│                 (8) MCP 요청│  Runtime   │                                      │
│                 (OAuth 토큰)│ (MCP 서버) │                                      │
│                            └────────────┘                                      │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

> **참고:** Policy Engine (Cedar 정책 평가)은 **인가(Authorization)** 단계로, Identity (인증)와는 별개입니다.
> Policy Engine에 대해서는 [Cedar Policy 가이드](./cedar-policy.md)를 참조하세요.

### 5.2 두 개의 Cognito User Pool

MCP 서버 타겟을 사용할 때는 **두 개의 Cognito User Pool**이 필요합니다:

| Cognito Pool | 위치 | 인증 유형 | 용도 |
|--------------|------|----------|------|
| **Gateway Cognito** | Gateway Inbound | JWT Authorizer | 클라이언트 → Gateway 인증 |
| **Runtime Cognito** | Runtime Inbound | OAuth (Identity) | Gateway → Runtime 인증 |

---

## 6. OAuth 플로우

### 6.1 2-Legged OAuth (Client Credentials)

**M2M (Machine-to-Machine)** 통신에 사용됩니다. 이 튜토리얼에서 Gateway → Runtime 인증에 사용.

```
┌──────────────┐                         ┌──────────────┐
│   Gateway    │ ──(client_id)────────> │   Runtime    │
│              │ ──(client_secret)────> │   Cognito    │
│              │ <──(access_token)───── │              │
└──────────────┘                         └──────────────┘
```

특징:
- 사용자 개입 없음
- 사전 승인된 서버 간 통신

### 6.2 3-Legged OAuth (Authorization Code)

**사용자 위임 접근**에 사용됩니다. AI Agent가 사용자를 대신하여 외부 서비스 접근.

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  사용자   │     │  AI Agent│     │ 외부 서비스  │
│          │     │ (Runtime)│     │ (Google 등)  │
└────┬─────┘     └────┬─────┘     └──────┬───────┘
     │                │                   │
     │  1. Agent가    │                   │
     │     리소스 요청 │                   │
     │                │                   │
     │  2. 사용자 동의 필요 (URL 반환)      │
     │<───────────────│                   │
     │                │                   │
     │  3. 사용자가 동의                   │
     │────────────────────────────────────>│
     │                │                   │
     │  4. 토큰 발급 (Token Vault에 저장)  │
     │                │<──────────────────│
     │                │                   │
     │  5. Agent가 API 호출               │
     │                │────────────────────>│
```

특징:
- 사용자가 명시적으로 권한 부여
- Token Vault가 토큰 저장 및 자동 갱신
- Google Calendar, GitHub, Slack 등 외부 서비스 접근

---

## 7. 사용법

### 7.1 Resource Credential Provider 생성

```python
import boto3

agentcore_client = boto3.client("bedrock-agentcore-control")

# Gateway → Runtime Outbound Auth를 위한 Credential Provider
response = agentcore_client.create_oauth2_credential_provider(
    name="my-mcp-server-identity",
    credentialProviderVendor="CustomOauth2",
    oauth2ProviderConfigInput={
        "customOauth2ProviderConfig": {
            "oauthDiscovery": {
                "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXX/.well-known/openid-configuration"
            },
            "clientId": "runtime-client-id",
            "clientSecret": "runtime-client-secret"
        }
    }
)

credential_provider_arn = response["credentialProviderArn"]
```

### 7.2 Gateway 타겟에 연결

```python
# MCP 서버 타겟 생성 시 Credential Provider 연결
response = agentcore_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="MyMCPServerTarget",
    targetConfiguration={
        "mcp": {
            "mcpServer": {
                "endpoint": "https://runtime-url/mcp"
            }
        }
    },
    credentialProviderConfigurations=[
        {
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": credential_provider_arn,
                    "scopes": ["mcp-server/invoke"]
                }
            }
        }
    ]
)
```

---

## 8. Lambda 타겟 vs MCP 서버 타겟

| 항목 | Lambda 타겟 | MCP 서버 타겟 (Runtime) |
|------|-------------|------------------------|
| **Gateway Outbound Auth** | ❌ (IAM Role 사용) | ✅ (Credential Provider) |
| **인증 방식** | `GATEWAY_IAM_ROLE` | `OAUTH` |
| **Cognito Pool** | 1개 (Gateway용) | 2개 (Gateway + Runtime) |
| **Runtime Inbound Auth** | N/A | Runtime Cognito |
| **설정 복잡도** | 낮음 | 중간 |

---

## 9. AgentCore 통합

AgentCore Identity는 다른 AgentCore 컴포넌트와 통합됩니다:

| 컴포넌트 | 통합 내용 |
|----------|----------|
| **AgentCore Runtime** | 호스팅된 에이전트에 인증 제공 |
| **AgentCore Gateway** | 도구 및 외부 API 접근 보안 |
| **AgentCore Memory** | 사용자별 메모리 저장소에 안전한 접근 |
| **AgentCore Observability** | 모든 에이전트 작업에 대한 감사 로그 |

---

## 10. 참고 자료

### AWS 공식 블로그

- [Introducing Amazon Bedrock AgentCore Identity](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-identity-securing-agentic-ai-at-scale/)
- [Securing AI agents with Amazon Bedrock AgentCore Identity](https://aws.amazon.com/blogs/security/securing-ai-agents-with-amazon-bedrock-agentcore-identity/)

### 튜토리얼

- [AgentCore Runtime 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime)
- [AgentCore Identity 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity)
  - [Inbound Auth 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/03-Inbound%20Auth%20example)
  - [Outbound Auth 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/04-Outbound%20Auth%20example)
  - [3-Legged OAuth (Google)](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/05-Outbound_Auth_3lo)
  - [GitHub Integration](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/06-Outbound_Auth_Github)
- [Outbound Auth 3LO - Google Calendar](./agentcore-identity-outbound-auth-3lo-google-calendar.md) (로컬)
