# AgentCore Identity 가이드

> 이 문서는 AgentCore Policy 튜토리얼을 위한 AgentCore Identity 개념을 설명합니다.

## 이 튜토리얼에서 다루는 컴포넌트

이 튜토리얼은 **Gateway**, **Identity**, **Policy** 세 가지 AgentCore 컴포넌트의 통합에 초점을 맞춥니다.

| 컴포넌트 | 역할 |
|----------|------|
| **Gateway** | MCP 프로토콜 엔드포인트, 도구 호출 중개 |
| **Identity** | 인증/인가, Outbound Auth 자격 증명 관리 |
| **Policy** | Cedar 기반 세분화된 접근 제어 |

> *"Identity is a key glue that's going to enable agents to be productionized quickly."* — AWS re:Invent 2025

## AgentCore Identity 핵심 컴포넌트

AgentCore Identity는 AI 에이전트를 위한 포괄적인 ID 및 자격 증명 관리 서비스입니다.

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
│  │  OAuth Access/Refresh 토큰, API 키를 안전하게 저장                        ││
│  │  자동 토큰 갱신 및 라이프사이클 관리                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 각 컴포넌트의 역할

#### Identity Directory

각 에이전트나 Gateway 배포에 **고유한 Workload ID**를 자동으로 생성합니다.

```
┌─────────────────────────────────────────────────────────┐
│  Identity Directory                                      │
│                                                          │
│  Agent: my-customer-service-agent                        │
│  Workload ID: arn:aws:bedrock-agentcore:us-east-1:123:agent/abc123
│                                                          │
│  Agent: my-data-analysis-agent                           │
│  Workload ID: arn:aws:bedrock-agentcore:us-east-1:123:agent/def456
└─────────────────────────────────────────────────────────┘
```

- 각 에이전트에 ARN 기반의 고유 식별자 부여
- 안정적인 에이전트 식별 및 추적 가능
- 감사 로그에서 어떤 에이전트가 작업을 수행했는지 명확히 파악

#### Authorizer

**IDP(Identity Provider)에 무관하게** 토큰을 검증하는 컴포넌트입니다.

```
┌────────────┐     ┌────────────┐     ┌─────────────────┐
│   Okta     │     │            │     │                 │
├────────────┤     │            │     │                 │
│ Azure      │ ──> │ Authorizer │ ──> │  에이전트/Gateway │
│ Entra ID   │     │            │     │                 │
├────────────┤     │ 토큰 검증   │     │                 │
│  Cognito   │     │            │     │                 │
└────────────┘     └────────────┘     └─────────────────┘
```

- 기존 IDP를 그대로 사용 (마이그레이션 불필요)
- Okta, Azure Entra ID, Cognito, Ping 등 다양한 IDP 지원
- 토큰 서명, 만료, 클레임 등을 자동 검증

#### Resource Credential Provider

OAuth 자격 증명과 API 키를 **안전하게 저장**합니다.

```python
# 코드에 자격 증명을 직접 포함하지 않음 (보안 위험)
# ❌ client_secret = "my-secret-key"

# Resource Credential Provider 사용 (안전)
# ✅ 자격 증명은 Identity에 안전하게 저장
response = agentcore_client.create_oauth2_credential_provider(
    name="my-service-identity",
    oauth2ProviderConfigInput={
        "customOauth2ProviderConfig": {
            "clientId": "...",
            "clientSecret": "..."  # Identity가 안전하게 저장
        }
    }
)
```

- 자격 증명을 코드나 CI/CD 파이프라인에 포함하지 않음
- 중앙에서 자격 증명 관리 및 교체 가능
- 이 튜토리얼에서 Gateway → Runtime 인증에 사용

#### Token Vault

OAuth 토큰의 **전체 라이프사이클을 자동 관리**합니다.

**Access Token vs Refresh Token**

| 토큰 | 용도 | 유효 기간 |
|------|------|----------|
| **Access Token** | API 호출 시 인증에 사용 | 짧음 (1시간 등) |
| **Refresh Token** | 새로운 Access Token 발급에 사용 | 김 (30일 등) |

```
┌─────────────────────────────────────────────────────────────────────────┐
│  토큰 자동 갱신 흐름                                                     │
│                                                                          │
│  1. 최초 인증                                                            │
│     사용자 동의 → Access Token (1시간) + Refresh Token (30일) 발급       │
│                                                                          │
│  2. API 호출                                                             │
│     에이전트 → Access Token으로 Google Calendar API 호출                  │
│                                                                          │
│  3. Access Token 만료 (1시간 후)                                         │
│     ❌ 기존 Access Token 사용 불가                                        │
│                                                                          │
│  4. 자동 갱신 (Token Vault가 처리)                                        │
│     Token Vault → Refresh Token으로 새 Access Token 요청                 │
│     Google → 새 Access Token 발급                                        │
│     ✅ 사용자 재로그인 불필요!                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**왜 Refresh Token이 필요한가?**

- **보안**: Access Token은 유효 기간이 짧아 탈취되어도 피해 최소화
- **사용자 경험**: 매번 로그인하지 않고 Refresh Token으로 자동 갱신
- **Token Vault**: 이 과정을 자동으로 처리하여 개발자가 신경 쓸 필요 없음

```
┌─────────────────────────────────────────────────────────────────┐
│  Token Vault 저장 예시                                           │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Resource: google-calendar                                 │  │
│  │  Access Token: eyJhbGc... (1시간 후 만료)                   │  │
│  │  Refresh Token: dGhpcyBp... (30일 후 만료)                  │  │
│  │  Status: ACTIVE                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

- Access Token, Refresh Token, API 키 저장
- 토큰 만료 시 **자동 갱신** (사용자 개입 불필요)
- 암호화 저장 및 접근 제어
- 특정 에이전트-사용자 조합만 해당 토큰에 접근 가능

> **핵심**: Token Vault가 Refresh Token을 안전하게 보관하고 자동으로 Access Token을 갱신해주므로, 개발자는 이 과정을 신경 쓸 필요가 없습니다.

## Inbound vs Outbound 인증

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│         Inbound Auth                              Outbound Auth              │
│   (사용자 → Gateway)                          (Gateway → 외부 서비스)         │
│                                                                              │
│   ┌────────────┐              ┌────────────┐              ┌────────────┐    │
│   │   사용자    │ ──────────> │  Gateway   │ ──────────> │ 외부 서비스 │    │
│   │            │  JWT 토큰    │            │  OAuth 토큰  │            │    │
│   └────────────┘  (검증)      └────────────┘  (발급)      └────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

| 인증 유형 | 방향 | 방식 | 용도 |
|----------|------|------|------|
| **Inbound Auth** | 사용자 → Gateway | JWT 토큰 **검증** | 누가 Gateway를 호출하는지 확인 |
| **Outbound Auth** | Gateway → 외부 서비스 | OAuth 토큰 **발급** | Gateway가 외부 리소스에 접근 |

### 차이점

| 구분 | Inbound Auth | Outbound Auth |
|------|-------------|---------------|
| **토큰 흐름** | 사용자가 토큰을 **가져옴** | Gateway가 토큰을 **발급받음** |
| **Gateway 역할** | 토큰 **검증** (JWT Authorizer) | 토큰 **요청** (Identity 사용) |
| **Cognito** | Gateway Cognito | Runtime Cognito |

---

## 이 튜토리얼에서 사용하는 Identity

AgentCore Policy 튜토리얼에서는 **MCP 서버 타겟**을 사용하며, 이를 위해 Identity의 **Resource Credential Provider**가 필요합니다.

### 왜 Resource Credential Provider가 필요한가?

> AWS 공식 샘플: *"First, we will create an AgentCore Identity Resource Credential Provider for our AgentCore Gateway to use as outbound auth to our MCP server in AgentCore Runtime."*

Gateway가 MCP 서버(Runtime)를 호출할 때 OAuth 인증이 필요합니다. Resource Credential Provider는 이 인증에 필요한 자격 증명을 안전하게 저장합니다.

### 두 개의 Cognito User Pool

MCP 서버 타겟을 사용할 때는 **두 개의 Cognito User Pool**이 필요합니다:

| Cognito Pool | 인증 유형 | 용도 |
|--------------|----------|------|
| **Gateway Cognito** | Inbound Auth | 클라이언트 → Gateway 인증 (JWT Authorizer) |
| **Runtime Cognito** | Outbound Auth | Gateway → Runtime 인증 (Identity 사용) |

### 전체 인증 흐름

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              전체 인증 흐름                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌────────────┐                                                                      │
│  │  Gateway   │                                                                      │
│  │  Cognito   │                                                                      │
│  └─────┬──────┘                                                                      │
│        │ 1. JWT 토큰 발급                                                             │
│        ▼                                                                             │
│  ┌────────────┐      2. JWT 토큰      ┌────────────┐                                 │
│  │  클라이언트 │ ───────────────────> │  Gateway   │                                 │
│  │  (Agent)   │                       │            │                                 │
│  └────────────┘                       └─────┬──────┘                                 │
│                                             │                                        │
│                                             │ 3. JWT Authorizer가 토큰 검증           │
│                                             │    (서명, 만료, 클레임 확인)             │
│                                             │                                        │
│                                             │ 4. Identity에서 자격 증명 조회          │
│                                             ▼                                        │
│                                       ┌────────────┐                                 │
│                                       │  Identity  │                                 │
│                                       │ (Resource  │                                 │
│                                       │ Credential │                                 │
│                                       │ Provider)  │                                 │
│                                       └─────┬──────┘                                 │
│                                             │                                        │
│                                             │ 5. client_id, client_secret 반환       │
│                                             ▼                                        │
│                                       ┌────────────┐                                 │
│                                       │  Runtime   │                                 │
│                                       │  Cognito   │                                 │
│                                       └─────┬──────┘                                 │
│                                             │                                        │
│                                             │ 6. OAuth Access Token 발급             │
│                                             ▼                                        │
│  ┌────────────┐      7. 도구 호출      ┌────────────┐      8. OAuth 토큰      ┌──────────┐
│  │  클라이언트 │ <───────────────────  │  Gateway   │ ───────────────────> │ Runtime  │
│  │            │      (결과 반환)       │            │     (MCP 요청)       │(MCP 서버)│
│  └────────────┘                       └────────────┘                       └──────────┘
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 단계별 설명

| 단계 | 설명 | 컴포넌트 |
|------|------|----------|
| 1 | 클라이언트가 Gateway Cognito에서 JWT 토큰 발급받음 | Gateway Cognito |
| 2 | 클라이언트가 JWT 토큰과 함께 Gateway에 요청 | 클라이언트 → Gateway |
| 3 | JWT Authorizer가 토큰 검증 (서명, 만료, 클레임) | Gateway |
| 4 | Gateway가 Identity에서 Runtime 자격 증명 조회 | Gateway → Identity |
| 5 | Identity가 저장된 client_id, client_secret 반환 | Identity |
| 6 | Gateway가 Runtime Cognito에서 OAuth 토큰 발급받음 | Runtime Cognito |
| 7-8 | Gateway가 OAuth 토큰으로 Runtime(MCP 서버)에 요청 | Gateway → Runtime |

### Resource Credential Provider 생성

```python
import boto3

agentcore_client = boto3.client("bedrock-agentcore-control")

# Outbound Auth를 위한 Resource Credential Provider 생성
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

### Gateway 타겟에 Identity 연결

```python
# MCP 서버 타겟 생성 시 Credential Provider 연결
response = agentcore_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="MyMCPServerTarget",
    targetConfiguration={
        "mcp": {
            "mcpServer": {
                "endpoint": "https://mcp-server-url/mcp"
            }
        }
    },
    credentialProviderConfigurations=[
        {
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": credential_provider_arn,
                    "scopes": ["resource-server/invoke"]
                }
            }
        }
    ]
)
```

### Lambda 타겟과의 비교

| 항목 | Lambda 타겟 | MCP 서버 타겟 |
|------|-------------|---------------|
| **Identity 필요** | 아니오 (IAM Role 사용) | 예 (Resource Credential Provider) |
| **인증 방식** | `GATEWAY_IAM_ROLE` | `OAUTH` |
| **Cognito Pool** | 1개 (Gateway용) | 2개 (Gateway + Runtime) |

---

## OAuth 플로우

### 2-Legged OAuth (이 튜토리얼에서 사용)

**Client Credentials Grant** - 서버 간 직접 통신에 사용됩니다.

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
- M2M (Machine-to-Machine) 인증

### 3-Legged OAuth (참고)

**Authorization Code Grant** - 사용자가 명시적으로 권한을 부여합니다.

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  사용자   │ ──> │  에이전트 │ ──> │ 외부 서비스  │
│          │     │          │     │ (Google 등)  │
│          │ <── 동의 요청 ──│     │              │
│          │ ── 동의 승인 ─>│     │              │
│          │     │          │ <── access_token   │
└──────────┘     └──────────┘     └──────────────┘
```

특징:
- 사용자가 명시적으로 권한 부여
- Google Calendar, GitHub 등 외부 서비스 접근에 사용
- 최소 권한 원칙 적용

---

## 고급 주제

### Workload Access Token

AgentCore Identity의 핵심 혁신은 **Workload Access Token**입니다. 이 토큰은 특정 사용자-에이전트 쌍을 바인딩하여:

- 에이전트가 할당된 사용자의 컨텍스트 내에서만 동작
- 세션 간 가장(impersonation) 방지
- 세분화된 접근 제어 가능

### 위임(Delegation) vs 가장(Impersonation)

AgentCore Identity는 **가장이 아닌 위임** 원칙으로 동작합니다:

| 방식 | 설명 | 보안 |
|------|------|------|
| **가장 (Impersonation)** | 에이전트가 사용자 자격 증명을 직접 사용 | 위험 |
| **위임 (Delegation)** | 에이전트가 자신으로 인증 + 사용자 컨텍스트 전달 | 안전 |

### Zero Trust 보안

> 소스나 이전 신뢰 관계와 관계없이 **모든 요청을 검증**

| 단계 | 검증 내용 |
|------|----------|
| 1 | 에이전트 ID 검증 |
| 2 | 사용자 토큰 서명/클레임 검증 |
| 3 | 리소스 접근 권한 검증 |

### Token Vault

OAuth 토큰을 안전하게 저장하고 자동으로 관리합니다:

- Access Token, Refresh Token, API 키 저장
- 자동 토큰 갱신
- 암호화 저장
- 특정 에이전트-사용자 조합만 접근 가능

### Observability

CloudTrail 통합으로 모든 API 호출을 로깅:
- 인증 성공률
- 토큰 발급 패턴
- 규정 준수 및 문제 해결

---

## Identity 관리 API

### Credential Provider 목록 조회

```python
response = agentcore_client.list_oauth2_credential_providers()

for provider in response.get("oauth2CredentialProviders", []):
    print(f"Name: {provider['name']}")
    print(f"ARN: {provider['credentialProviderArn']}")
```

### Credential Provider 삭제

```python
agentcore_client.delete_oauth2_credential_provider(
    name="my-mcp-server-identity"
)
```

---

## 관련 문서

- [JWT Authorizer](jwt-authorizer.md) - Gateway Inbound Auth
- [Cognito](cognito.md) - Amazon Cognito 설정
- [Cedar Policy](cedar-policy.md) - 정책 기반 접근 제어

## 참고 자료

### AWS 공식 블로그

- [Introducing Amazon Bedrock AgentCore Identity: Securing agentic AI at scale](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-identity-securing-agentic-ai-at-scale/)
- [Securing AI agents with Amazon Bedrock AgentCore Identity](https://aws.amazon.com/blogs/security/securing-ai-agents-with-amazon-bedrock-agentcore-identity/)
- [Amazon Bedrock AgentCore 정식 출시](https://aws.amazon.com/ko/blogs/tech/building-secure-agent-with-agentcore-identity/)

### 튜토리얼

- [AgentCore Identity 튜토리얼](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity)
- [Inbound Auth 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/03-Inbound%20Auth%20example)
- [Outbound Auth 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/04-Outbound%20Auth%20example)
- [3-Legged OAuth 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/05-Outbound_Auth_3lo)
