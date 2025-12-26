# JWT Authorizer 가이드

## JWT란?

**JWT (JSON Web Token)**는 사용자 인증 정보를 담은 토큰입니다.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.signature
└──────── Header ────────┘└─────────── Payload ─────────────┘└── Signature ──┘
```

디코딩된 Payload:
```json
{
  "sub": "user-123",
  "name": "Alice",
  "client_id": "my-app",
  "scope": "openid email",
  "exp": 1735027200,
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC"
}
```

## JWT Authorizer란?

**JWT Authorizer**는 API 요청이 들어올 때 JWT를 검증하여 요청자의 신원을 확인하는 컴포넌트입니다.

### 검증 항목

| 항목 | 설명 |
|------|------|
| 서명 (Signature) | 토큰이 위변조되지 않았는지 |
| 만료 (exp) | 토큰이 만료되지 않았는지 |
| 발급자 (iss) | 신뢰할 수 있는 발급자인지 |
| 클라이언트 (client_id) | 허용된 앱에서 발급했는지 |
| 범위 (scope) | 필요한 권한이 있는지 |

### 동작 흐름

```
┌─────────────┐                      ┌─────────────────────────────────────┐
│   Client    │                      │            Gateway                  │
│   (Agent)   │                      │                                     │
└──────┬──────┘                      │  ┌─────────────────────────────┐    │
       │                             │  │     JWT Authorizer          │    │
       │  1. Request + JWT Token     │  │                             │    │
       │ ───────────────────────────>│  │  검증 항목:                  │    │
       │                             │  │  ✓ 서명 유효한가?            │    │
       │                             │  │  ✓ 만료되지 않았나?          │    │
       │                             │  │  ✓ 발급자(iss) 맞나?        │    │
       │                             │  │  ✓ 허용된 client_id인가?    │    │
       │                             │  │  ✓ 필요한 scope 있나?       │    │
       │                             │  └──────────────┬──────────────┘    │
       │                             │                 │                   │
       │                             │         ┌───────┴───────┐           │
       │                             │         │               │           │
       │  2a. 401 Unauthorized       │      유효 ✓          무효 ✗         │
       │ <─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │         │               │           │
       │                             │         ▼               │           │
       │  2b. 요청 처리              │    ┌─────────┐          │           │
       │ <───────────────────────────│    │ Backend │          │           │
       │                             │    │ (Lambda)│          │           │
       │                             │    └─────────┘          │           │
└──────┴─────────────────────────────┴─────────────────────────┴───────────┘
```

## Gateway JWT Authorizer 설정

### Gateway Authorizer란?

**Gateway Authorizer**는 AgentCore Gateway로 들어오는 요청의 **JWT 토큰을 검증**하는 컴포넌트입니다.

> 📝 **참고**: Gateway Authorizer는 별도의 이름이 있는 리소스가 아니라 **Gateway 내부 설정(속성)**입니다.

### 역할

```
┌─────────────┐         ┌─────────────────────────────────────────────────┐
│   Client    │         │              AgentCore Gateway                   │
│   (Agent)   │         │                                                  │
└──────┬──────┘         │  ┌─────────────────┐      ┌─────────────────┐  │
       │                │  │ Gateway         │      │ Policy Engine   │  │
       │ Request +      │  │ Authorizer      │      │ (Cedar 정책)    │  │
       │ JWT Token      │  │                 │      │                 │  │
       │                │  │ 검증:           │  OK  │ 검증:           │  │
       │───────────────>│  │ - 서명 유효?    │─────>│ - 부서=finance? │  │
       │                │  │ - 만료 안됨?    │      │ - 금액<=1000?   │  │
       │                │  │ - client_id?    │      │                 │  │
       │                │  │ - scope?        │      │                 │  │
       │                │  └────────┬────────┘      └────────┬────────┘  │
       │                │           │                        │           │
       │                │        실패 시                   실패 시       │
       │                │      401 Unauthorized          403 Forbidden   │
       │                └─────────────────────────────────────────────────┘
```

### Authorizer vs Policy Engine

| 항목 | Gateway Authorizer | Policy Engine (Cedar) |
|------|-------------------|----------------------|
| **검증 대상** | JWT 토큰 자체 | 토큰 내 클레임 + 요청 내용 |
| **검증 예시** | 서명 유효? 만료? client_id? | department=finance? amount<=1000? |
| **실패 응답** | `401 Unauthorized` | `403 Forbidden` |
| **역할** | "이 토큰이 진짜인가?" | "이 사용자가 이 작업을 할 수 있는가?" |

### 검증 순서

```
1. JWT 서명 검증
   └── discoveryUrl에서 공개키 가져와서 서명 확인

2. 토큰 만료 확인
   └── exp 클레임 확인

3. client_id 확인
   └── allowedClients에 포함되어 있는지

4. scope 확인 (선택)
   └── allowedScopes에 포함되어 있는지

5. audience 확인 (선택)
   └── allowedAudience에 포함되어 있는지
   └── ⚠️ Cognito Access Token에는 aud 없음!
```

### Gateway 내 Authorizer 위치

```
Gateway
├── gatewayId: "testgwforpolicyengine-****"
├── name: "TestGWforPolicyEngine"
├── authorizerType: "CUSTOM_JWT"
├── authorizerConfiguration:        ← Authorizer 설정 (여기!)
│   └── customJWTAuthorizer:
│       ├── discoveryUrl: "https://cognito-idp..."
│       ├── allowedClients: ["****"]
│       ├── allowedAudience: []
│       └── allowedScopes: ["TestGateway/invoke"]
└── policyEngineConfiguration: {...}
```

### Authorizer 설정 확인 방법

#### Python 코드로 확인

```python
import boto3

gateway_control_client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

# Gateway 상세 정보 조회
gateway = gateway_control_client.get_gateway(gatewayIdentifier=GATEWAY_ID)

# Authorizer 설정 확인
authorizer_config = gateway.get("authorizerConfiguration", {})
jwt_config = authorizer_config.get("customJWTAuthorizer", {})

print("Authorizer Type:", gateway.get("authorizerType"))
print("Discovery URL:", jwt_config.get("discoveryUrl"))
print("Allowed Clients:", jwt_config.get("allowedClients"))
print("Allowed Audience:", jwt_config.get("allowedAudience"))
print("Allowed Scopes:", jwt_config.get("allowedScopes"))
```

#### AWS CLI로 확인

```bash
aws bedrock-agentcore-control get-gateway \
  --gateway-identifier testgwforpolicyengine-**** \
  --region us-east-1 \
  --query 'authorizerConfiguration'
```

#### 튜토리얼에서 확인

Step 1.3 `validate_and_fix_gateway_authorizer()` 실행 시 출력:

```
Gateway Authorizer 설정 검증
======================================================================
  Discovery URL: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_****/...
  Allowed Clients: ['7vgk****']
  Allowed Audience: []
  Allowed Scopes: ['TestGateway/invoke']

✓ Gateway Authorizer 설정이 유효합니다
```

### Authorizer 설정 항목

```python
{
    "customJWTAuthorizer": {
        "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC/.well-known/openid-configuration",
        "allowedClients": ["client-id-123"],
        "allowedAudience": [],        # Cognito Access Token은 aud 없음
        "allowedScopes": ["TestGateway/invoke"]
    }
}
```

| 설정 | 설명 | 예시 |
|------|------|------|
| `discoveryUrl` | OIDC 설정 URL (공개키 등 포함) | Cognito User Pool URL |
| `allowedClients` | 허용된 App Client ID | `["abc123"]` |
| `allowedAudience` | JWT `aud` 클레임 검증 | Cognito는 `[]` |
| `allowedScopes` | 허용된 OAuth scope | `["TestGateway/invoke"]` |

### Authorizer 생성 시점

Gateway Authorizer는 `setup-gateway.py`에서 **Gateway 생성 시 자동으로 설정**됩니다:

```python
# setup-gateway.py

# 1. Cognito 리소스 생성 (authorizer_config 포함)
cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")

# 2. Gateway 생성 시 authorizer_config 전달 → Authorizer 자동 설정
gateway = client.create_mcp_gateway(
    name=gateway_name,
    authorizer_config=cognito_response.get("authorizer_config"),  # ← 여기서 설정됨
    ...
)
```

| 단계 | 역할 |
|------|------|
| `setup-gateway.py` (Step 1.1) | Gateway + Authorizer 자동 생성 |
| `validate_and_fix_gateway_authorizer()` (Step 1.3) | 설정 검증 및 필요시 수정 |

### Cognito 특이사항

**Cognito Access Token에는 `aud` 클레임이 없습니다!**

```json
// 일반적인 JWT (aud 있음)
{
  "sub": "user123",
  "aud": "my-client-id"    // ← 있음
}

// Cognito Access Token (aud 없음!)
{
  "sub": "user123",
  "client_id": "my-client-id"  // ← aud 대신 client_id 사용
}
```

→ `allowedAudience`를 설정하면 **유효한 토큰도 거부**됩니다!

## OAuth2 Scope

### 표준 OIDC Scopes

| Scope | 접근 가능한 정보 |
|-------|-----------------|
| `openid` | 사용자 ID (sub) - 필수 |
| `profile` | 이름, 사진 등 |
| `email` | 이메일 주소 |
| `phone` | 전화번호 |

### 커스텀 Scopes

```
Resource Server: insurance-api
├── insurance-api/read      → 보험 정보 조회
├── insurance-api/write     → 보험 정보 수정
├── insurance-api/approve   → 보험 승인
└── insurance-api/admin     → 관리자 기능
```

## JWT Scope vs Cedar Policy

### Scope의 한계

Gateway `allowedScopes`는 **전체 Gateway 접근**을 제어하지, **개별 Target별 제어**는 하지 않습니다.

```
┌─────────────────────────────────────────────────────────────┐
│  Gateway JWT Authorizer                                     │
│                                                             │
│  allowedScopes: ["insurance-api/access"]                    │
│                                                             │
│  토큰에 scope 있으면 → Gateway 전체 접근 ✅                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Targets (모두 동일하게 접근 가능)                    │    │
│  │  ├── Lambda: ApplicationTool    ✅                  │    │
│  │  ├── Lambda: RiskModelTool      ✅                  │    │
│  │  └── Lambda: ApprovalTool       ✅  ← 구분 안 됨!   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Cedar Policy로 해결

```
┌─────────────────────────────────────────────────────────────┐
│  Cedar Policy Engine                                        │
│                                                             │
│  ApplicationTool                                            │
│  → permit when { principal.role in ["junior", "senior"] }  │
│                                                             │
│  RiskModelTool                                              │
│  → permit when { principal.role in ["senior", "manager"] } │
│                                                             │
│  ApprovalTool                                               │
│  → permit when { principal.role == "manager" }             │
└─────────────────────────────────────────────────────────────┘
```

## 비교 요약

| 기능 | JWT Scope + Gateway Authorizer | Cedar Policy |
|------|-------------------------------|--------------|
| Gateway 전체 접근 제어 | ✅ | ✅ |
| **Target별 접근 제어** | ❌ | ✅ |
| **파라미터 기반 조건** | ❌ | ✅ |
| **사용자 역할 기반** | ❌ | ✅ |
| 실시간 정책 변경 | ❌ (토큰 재발급) | ✅ |

## 결론

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   JWT Scope    →  "문을 열 수 있는 열쇠가 있나?"          │
│                   (API 접근 여부)                        │
│                                                         │
│   Cedar Policy →  "이 조건에서 이 행동이 허용되나?"       │
│                   (세부 비즈니스 규칙)                    │
│                                                         │
│   둘 다 필요!  →  Defense in Depth (심층 방어)           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**JWT Scope = 대문 열쇠** 🔑
**Cedar Policy = 각 방의 출입 규칙** 📋
