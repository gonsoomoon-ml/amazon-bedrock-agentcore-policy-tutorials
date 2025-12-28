# JWT Authorizer 가이드

## 1. JWT란?

**JWT (JSON Web Token)**는 사용자 인증 정보를 담은 토큰입니다.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature
└──────── Header ────────┘└───── Payload ─────┘└── Signature ──┘
```

### 디코딩된 Payload

```json
{
  "sub": "user-123",
  "client_id": "my-app",
  "scope": "openid email",
  "exp": 1735027200,
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC",
  "department_name": "finance",   // 커스텀 클레임
  "groups": "[\"admins\"]"        // 커스텀 클레임
}
```

---

## 2. JWT Authorizer란?

**JWT Authorizer**는 API 요청이 들어올 때 JWT를 검증하여 요청자의 신원을 확인하는 컴포넌트입니다.

### 검증 항목

| 항목 | 설명 |
|------|------|
| 서명 (Signature) | 토큰이 위변조되지 않았는지 |
| 만료 (exp) | 토큰이 만료되지 않았는지 |
| 발급자 (iss) | 신뢰할 수 있는 발급자인지 |
| 클라이언트 (client_id) | 허용된 앱에서 발급했는지 |
| 범위 (scope) | 필요한 권한이 있는지 |

---

## 3. JWT Authorizer vs Policy Engine

Gateway에는 **두 단계**의 검증이 있습니다:

```
요청 ─────> JWT Authorizer ─────> Policy Engine ─────> 타겟
              (1단계)              (2단계)
           "토큰이 진짜인가?"    "이 작업을 할 수 있나?"
```

### 3.1 역할 비교

| 구분 | JWT Authorizer | Policy Engine (Cedar) |
|------|----------------|----------------------|
| **역할** | 토큰 검증 | 비즈니스 규칙 적용 |
| **검증 대상** | JWT 토큰 자체 | 토큰 내 클레임 + 요청 내용 |
| **검증 예시** | 서명, 만료, client_id | department=finance, amount<=1000 |
| **실패 응답** | `401 Unauthorized` | `403 Forbidden` |
| **질문** | "이 토큰이 진짜인가?" | "이 사용자가 이 작업을 할 수 있는가?" |

### 3.2 동작 흐름

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
       │                             │  ┌─────────────────┐    │           │
       │                             │  │  Policy Engine  │    │           │
       │                             │  │  (Cedar 정책)   │    │           │
       │                             │  └────────┬────────┘    │           │
       │                             │           │             │           │
       │  2b. 403 Forbidden          │        허용/거부        │           │
       │ <─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │           │             │           │
       │                             │           ▼             │           │
       │  2c. 요청 처리              │    ┌─────────┐          │           │
       │ <───────────────────────────│    │ Backend │          │           │
       │                             │    └─────────┘          │           │
└──────┴─────────────────────────────┴─────────────────────────┴───────────┘
```

---

## 4. JWT Authorizer 설정

### 4.1 설정 항목

```python
{
    "customJWTAuthorizer": {
        "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC/.well-known/openid-configuration",
        "allowedClients": ["client-id-123"],
        "allowedAudience": [],        # Cognito는 aud 없음 - 비워둘 것!
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

### 4.2 검증 순서

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

### 4.3 Gateway 내 Authorizer 위치

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

---

## 5. Scope의 한계

### 5.1 문제점

Gateway `allowedScopes`는 **Gateway 전체 접근**만 제어합니다. **개별 타겟별 제어**는 하지 않습니다.

```
allowedScopes: ["insurance-api/access"]

┌─────────────────────────────────────┐
│  모든 타겟에 동일하게 접근 가능       │
│  ├── ApplicationTool    ✅          │
│  ├── RiskModelTool      ✅          │
│  └── ApprovalTool       ✅  ← 구분 안 됨!
└─────────────────────────────────────┘
```

### 5.2 Cedar Policy로 해결

```cedar
// ApplicationTool: 모든 역할 허용
permit(...) when { principal.role in ["junior", "senior", "manager"] };

// RiskModelTool: 시니어 이상만 허용
permit(...) when { principal.role in ["senior", "manager"] };

// ApprovalTool: 매니저만 허용
permit(...) when { principal.role == "manager" };
```

### 5.3 비교 요약

| 기능 | JWT Scope | Cedar Policy |
|------|-----------|--------------|
| Gateway 전체 접근 | ✅ | ✅ |
| **타겟별 접근 제어** | ❌ | ✅ |
| **파라미터 기반 조건** | ❌ | ✅ |
| **사용자 역할 기반** | ❌ | ✅ |
| 실시간 정책 변경 | ❌ (토큰 재발급) | ✅ |

---

## 6. 주의사항

### 6.1 Cognito Access Token에는 `aud` 클레임이 없음

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

> **중요**: `allowedAudience`를 설정하면 **유효한 토큰도 거부**됩니다! 반드시 `[]`로 비워두세요.

### 6.2 Authorizer 설정 확인 방법

**Python 코드:**

```python
import boto3

gateway_client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

# Gateway 상세 정보 조회
gateway = gateway_client.get_gateway(gatewayIdentifier=GATEWAY_ID)

# Authorizer 설정 확인
authorizer_config = gateway.get("authorizerConfiguration", {})
jwt_config = authorizer_config.get("customJWTAuthorizer", {})

print("Authorizer Type:", gateway.get("authorizerType"))
print("Discovery URL:", jwt_config.get("discoveryUrl"))
print("Allowed Clients:", jwt_config.get("allowedClients"))
print("Allowed Audience:", jwt_config.get("allowedAudience"))
print("Allowed Scopes:", jwt_config.get("allowedScopes"))
```

**AWS CLI:**

```bash
aws bedrock-agentcore-control get-gateway \
  --gateway-identifier testgwforpolicyengine-**** \
  --region us-east-1 \
  --query 'authorizerConfiguration'
```

---

## 7. 요약

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   JWT Authorizer = 대문 열쇠 🔑                     │
│   "이 API에 접근할 수 있는 열쇠가 있나?"             │
│                                                     │
│   Cedar Policy = 각 방의 규칙 📋                    │
│   "이 조건에서 이 행동이 허용되나?"                  │
│                                                     │
│   둘 다 필요! → Defense in Depth (심층 방어)        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 8. 참고 자료

- [Amazon Cognito 가이드](cognito.md)
- [Cedar Policy 문법](cedar-policy.md)
- [JWT.io](https://jwt.io/) - JWT 디코더
