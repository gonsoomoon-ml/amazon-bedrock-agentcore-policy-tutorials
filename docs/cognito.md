# Amazon Cognito 가이드

## 1. Amazon Cognito란?

**Amazon Cognito**는 AWS의 완전관리형 사용자 인증 및 권한 부여 서비스입니다.

웹/모바일 앱에 로그인 기능을 쉽게 추가하고, OAuth2/OIDC 표준을 통해 안전한 인증을 제공합니다.

---

## 2. 왜 Cognito가 필요한가?

이 튜토리얼에서 Cognito는 두 가지 역할을 합니다:

| 역할 | 설명 |
|------|------|
| **JWT 토큰 발급** | Gateway에 접근하기 위한 인증 토큰 |
| **커스텀 클레임 추가** | Cedar 정책에서 사용할 department, groups 등 |

```
┌──────────────┐      JWT 토큰        ┌──────────────┐
│   Cognito    │ ───────────────────> │   Gateway    │
│              │  + department        │              │
│              │  + groups            │              │
└──────────────┘                      └──────────────┘
                                             │
                                             ▼
                                      Cedar 정책에서 사용:
                                      principal.getTag("department")
```

---

## 3. 핵심 구성 요소

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Pool                                 │
│                      (사용자 저장소)                              │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    App Clients                           │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│   │   │ Web App  │  │Mobile App│  │ M2M App  │ ← 이 튜토리얼  │   │
│   │   │(사용자용)│  │(사용자용)│  │ (서버용) │              │   │
│   │   └──────────┘  └──────────┘  └──────────┘              │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Resource Server: TestGateway                            │   │
│   │  └── Scope: TestGateway/invoke                           │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Lambda Trigger (Pre Token Generation V3_0)              │   │
│   │  └── 커스텀 클레임 추가: department_name, groups         │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 User Pool (사용자 풀)

**사용자 정보를 저장하는 디렉토리**입니다.

| 항목 | 설명 | 예시 |
|------|------|------|
| User Pool ID | 풀의 고유 식별자 | `us-east-1_ABC123` |
| 사용자 속성 | 저장할 사용자 정보 | email, phone, custom:department |
| 비밀번호 정책 | 최소 길이, 복잡도 등 | 8자 이상, 특수문자 포함 |

### 3.2 App Client (앱 클라이언트)

**User Pool에 접근하는 애플리케이션**입니다.

| 설정 | 설명 |
|------|------|
| Client ID | 앱의 고유 식별자 (공개) |
| Client Secret | 앱의 비밀 키 (M2M용, 비공개) |
| OAuth 플로우 | 인증 방식 (Authorization Code, Client Credentials 등) |
| Scopes | 요청 가능한 권한 범위 |

### 3.3 Resource Server (리소스 서버)

**커스텀 Scope를 정의**하는 곳입니다.

```
Resource Server: TestGateway
└── TestGateway/invoke    → Gateway 호출 권한
```

| 항목 | 값 | 설명 |
|------|-----|------|
| Identifier | `TestGateway` | Resource Server 식별자 |
| Scope Name | `invoke` | 권한 이름 |
| Full Scope | `TestGateway/invoke` | 토큰 요청 시 사용 |

### 3.4 User Pool Domain

**OAuth2 엔드포인트를 제공**하는 URL입니다.

```
https://agentcore-****.auth.us-east-1.amazoncognito.com
├── /oauth2/token      → 토큰 발급
├── /oauth2/authorize  → 로그인 페이지
└── /.well-known/...   → OIDC 설정 정보
```

---

## 4. OAuth2 인증 플로우

### 4.1 Client Credentials Flow (이 튜토리얼에서 사용)

**M2M (Machine-to-Machine)** 통신용입니다. 사용자 로그인 없이 서버 간 직접 통신합니다.

```
┌─────────────────┐                      ┌─────────────────┐
│   Backend App   │                      │     Cognito     │
│   (M2M Client)  │                      │   Token 엔드포인트 │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         │  POST /oauth2/token                    │
         │  client_id + client_secret             │
         │  grant_type=client_credentials         │
         │───────────────────────────────────────>│
         │                                        │
         │  Access Token 반환                     │
         │  (사용자 로그인 없이!)                  │
         │<───────────────────────────────────────│
```

**특징:**
- 사용자 로그인 **불필요** (서버 간 통신)
- Access Token만 발급 (ID Token 없음)
- AgentCore 튜토리얼에서 사용하는 방식

**Python 코드:**

```python
import requests
import base64

def get_bearer_token(token_url, client_id, client_secret, scope="openid"):
    """M2M Client Credentials Flow로 토큰 발급"""
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.post(
        token_url,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "client_credentials",
            "scope": scope
        }
    )
    return response.json().get("access_token")
```

### 4.2 Authorization Code Flow (참고)

**사용자 로그인용**입니다. 웹/모바일 앱에서 사용합니다.

```
사용자 ──> Web App ──> Cognito 로그인 페이지 ──> 사용자 인증 ──> Authorization Code ──> Access Token
```

---

## 5. Lambda 트리거 (커스텀 클레임)

### 5.1 왜 필요한가?

기본 Cognito 토큰에는 표준 클레임만 포함됩니다:

| 트리거 없음 | 트리거 설정 후 |
|------------|---------------|
| `sub`, `client_id`, `exp`, `iss` | + **`department_name`**, **`groups`** 등 |

Cedar 정책에서 사용할 **커스텀 클레임**을 추가하려면 Lambda 트리거가 필요합니다.

### 5.2 Pre Token Generation Trigger

토큰 발급 **직전에** Lambda를 실행하여 **커스텀 클레임을 추가**합니다.

```
┌──────────┐         ┌─────────────┐         ┌─────────────┐
│  Client  │         │   Cognito   │         │   Lambda    │
└────┬─────┘         └──────┬──────┘         └──────┬──────┘
     │                      │                       │
     │  1. 토큰 요청        │                       │
     │─────────────────────>│                       │
     │                      │                       │
     │                      │  2. Pre Token Trigger │
     │                      │──────────────────────>│
     │                      │                       │
     │                      │  3. 커스텀 클레임 반환 │
     │                      │     department: finance│
     │                      │     groups: [admins]  │
     │                      │<──────────────────────│
     │                      │                       │
     │  4. 토큰 + 커스텀 클레임                     │
     │<─────────────────────│                       │
```

### 5.3 Lambda 버전

| 버전 | 지원 플로우 | M2M 지원 | Cognito 티어 |
|------|------------|---------|--------------|
| V1_0 | 사용자 로그인만 | ❌ | Lite (무료) |
| V2_0 | 사용자 로그인만 | ❌ | Lite (무료) |
| **V3_0** | 사용자 로그인 + **Client Credentials** | ✅ | **Essentials/Plus** |

> **중요**: M2M (Client Credentials) 플로우에서 커스텀 클레임을 추가하려면 **V3_0 필수**!

### 5.4 Lambda 코드 예시

```python
def lambda_handler(event, context):
    """
    Cognito Pre-token generation V3 Lambda 트리거.
    client_credentials 플로우를 포함한 모든 플로우에서 JWT에 커스텀 클레임을 추가합니다.
    """
    print(f"Event: {json.dumps(event)}")
    print(f"Trigger Source: {event.get('triggerSource', 'unknown')}")

    # 토큰에 커스텀 클레임 추가
    event['response'] = {
        'claimsAndScopeOverrideDetails': {
            'accessTokenGeneration': {
                'claimsToAddOrOverride': {
                    "department_name": "finance",
                    "employee_level": "senior",
                    "groups": '["admins", "developers"]'  # 배열은 문자열로 직렬화
                }
            }
        }
    }

    return event
```

### 5.5 트리거 설정

```python
# V3_0 트리거 설정 (M2M 플로우 지원)
cognito_client.update_user_pool(
    UserPoolId=user_pool_id,
    LambdaConfig={
        "PreTokenGenerationConfig": {
            "LambdaVersion": "V3_0",  # M2M 플로우 지원을 위해 필수
            "LambdaArn": lambda_arn,
        }
    },
)
```

### 5.6 Cedar 정책에서 사용

```cedar
// 부서 기반 접근 제어
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};

// 그룹 기반 접근 제어 (배열은 문자열로 직렬화되므로 like 사용)
permit(principal, action, resource)
when {
    principal.hasTag("groups") &&
    principal.getTag("groups") like "*admins*"
};
```

---

## 6. Cognito 티어

| 티어 | Lambda Trigger V3_0 | 가격 |
|------|---------------------|------|
| Lite | ❌ | 무료 (제한적) |
| **Essentials** | ✅ | 유료 |
| **Plus** | ✅ | 유료 (추가 기능) |

> **중요**: M2M + 커스텀 클레임을 사용하려면 **Essentials** 또는 **Plus** 티어 필요!

---

## 7. 생성되는 리소스

`setup-gateway.py` 실행 시 다음 리소스가 생성됩니다:

```
┌─────────────────────────────────────────────────────────────────┐
│  Cognito 리소스 생성 순서                                        │
│                                                                  │
│  1. User Pool                                                    │
│     └── Name: agentcore-gateway-****                            │
│     └── ID: us-east-1_****                                      │
│                                                                  │
│  2. User Pool Domain                                             │
│     └── Prefix: agentcore-****                                  │
│     └── URL: https://agentcore-****.auth.{region}.amazoncognito.com │
│                                                                  │
│  3. Resource Server                                              │
│     └── Identifier: TestGateway                                 │
│     └── Scope: TestGateway/invoke                               │
│                                                                  │
│  4. App Client (M2M)                                             │
│     └── Client ID: ****                                         │
│     └── Client Secret: ****                                     │
│     └── OAuth Flow: Client Credentials                          │
│     └── Allowed Scope: TestGateway/invoke                       │
│                                                                  │
│  5. Lambda Trigger (V3_0)                                        │
│     └── Pre Token Generation                                    │
│     └── 커스텀 클레임: department_name, groups                   │
└─────────────────────────────────────────────────────────────────┘
```

### gateway_config.json 예시

```json
{
  "client_info": {
    "user_pool_id": "us-east-1_****",
    "client_id": "****",
    "client_secret": "****",
    "token_endpoint": "https://agentcore-****.auth.us-east-1.amazoncognito.com/oauth2/token",
    "scope": "TestGateway/invoke",
    "domain_prefix": "agentcore-****"
  }
}
```

---

## 8. 주의사항

### 8.1 Cognito Access Token에는 `aud` 클레임이 없음

```json
// 일반적인 JWT (aud 있음)
{ "aud": "my-client-id" }

// Cognito Access Token (aud 없음!)
{ "client_id": "my-client-id" }  // aud 대신 client_id 사용
```

→ Gateway JWT Authorizer에서 `allowedAudience`를 설정하면 **유효한 토큰도 거부**됩니다!

### 8.2 Lambda 호출 권한

Cognito가 Lambda를 호출하려면 권한이 필요합니다:

```python
lambda_client.add_permission(
    FunctionName=lambda_arn,
    StatementId=f"CognitoInvoke-{user_pool_id}",
    Action="lambda:InvokeFunction",
    Principal="cognito-idp.amazonaws.com",
    SourceArn=f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{user_pool_id}",
)
```

### 8.3 배열 클레임은 문자열로 직렬화

```python
# Lambda에서
"groups": '["admins", "developers"]'  # 문자열로 저장

# Cedar에서
principal.getTag("groups") like "*admins*"  # like로 검색
```

---

## 9. 참고 자료

- [Amazon Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [OAuth2 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
- [Cognito Lambda Triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html)
