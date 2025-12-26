# Amazon Cognito 가이드

## Amazon Cognito란?

**Amazon Cognito**는 AWS의 완전관리형 사용자 인증 및 권한 부여 서비스입니다.

웹/모바일 앱에 로그인 기능을 쉽게 추가하고, OAuth2/OIDC 표준을 통해 안전한 인증을 제공합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Amazon Cognito                              │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    User Pool                             │   │
│   │                  (사용자 저장소)                          │   │
│   │                                                          │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐                 │   │
│   │   │  User   │  │  User   │  │  User   │   ...           │   │
│   │   │  Alice  │  │   Bob   │  │ Charlie │                 │   │
│   │   └─────────┘  └─────────┘  └─────────┘                 │   │
│   │                                                          │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │              App Clients                         │   │   │
│   │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │   │
│   │   │  │ Web App  │  │Mobile App│  │ M2M App  │       │   │   │
│   │   │  │(사용자용)│  │(사용자용)│  │(서버용)  │       │   │   │
│   │   │  └──────────┘  └──────────┘  └──────────┘       │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 핵심 구성 요소

### 1. User Pool (사용자 풀)

**사용자 정보를 저장하는 디렉토리**입니다. 개별 사용자가 아닌, 사용자들의 **컨테이너**입니다.

| 항목 | 설명 | 예시 |
|------|------|------|
| User Pool ID | 풀의 고유 식별자 | `us-east-1_ABC123` |
| 사용자 속성 | 저장할 사용자 정보 | email, phone, custom:department |
| 비밀번호 정책 | 최소 길이, 복잡도 등 | 8자 이상, 특수문자 포함 |
| MFA 설정 | 다중 인증 요구 여부 | SMS, TOTP |

### 2. App Client (앱 클라이언트)

**User Pool에 접근하는 애플리케이션**입니다. 각 앱마다 별도의 Client를 생성합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                        User Pool                             │
│                      (us-east-1_ABC)                         │
│                                                              │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐ │
│   │  App Client 1 │   │  App Client 2 │   │  App Client 3 │ │
│   │  (Web App)    │   │  (Mobile)     │   │  (M2M)        │ │
│   │               │   │               │   │               │ │
│   │ client_id:    │   │ client_id:    │   │ client_id:    │ │
│   │ abc123...     │   │ def456...     │   │ ghi789...     │ │
│   │               │   │               │   │               │ │
│   │ OAuth 플로우: │   │ OAuth 플로우: │   │ OAuth 플로우: │ │
│   │ Auth Code     │   │ Auth Code     │   │ Client Creds  │ │
│   └───────────────┘   └───────────────┘   └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

| 설정 | 설명 |
|------|------|
| Client ID | 앱의 고유 식별자 (공개) |
| Client Secret | 앱의 비밀 키 (M2M용, 비공개) |
| OAuth 플로우 | 인증 방식 (Authorization Code, Client Credentials 등) |
| Scopes | 요청 가능한 권한 범위 |

### 3. User Pool Domain (사용자 풀 도메인)

**OAuth2 엔드포인트를 제공**하는 URL입니다. 토큰 요청 시 이 도메인을 사용합니다.

| 항목 | 설명 | 예시 |
|------|------|------|
| Domain Prefix | 도메인 접두사 (자동 생성) | `agentcore-****` |
| Full Domain | 전체 도메인 URL | `agentcore-****.auth.us-east-1.amazoncognito.com` |
| Token Endpoint | 토큰 발급 URL | `https://{domain}/oauth2/token` |

```
┌─────────────────────────────────────────────────────────────────┐
│  User Pool Domain                                                │
│  https://agentcore-****.auth.us-east-1.amazoncognito.com        │
│                                                                  │
│   /oauth2/token      → 토큰 발급 (Client Credentials 플로우)     │
│   /oauth2/authorize  → 로그인 페이지 (Authorization Code 플로우) │
│   /oauth2/userInfo   → 사용자 정보 조회                          │
│   /.well-known/...   → OIDC 설정 정보                            │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Resource Server (리소스 서버)

**커스텀 Scope를 정의**하는 곳입니다. API 리소스와 권한을 관리합니다.

#### Scope 구조

```
{Resource Server Identifier}/{Scope Name}
         │                       │
         └── 리소스 식별자        └── 권한 이름
```

#### 이 튜토리얼의 Resource Server

```
Resource Server: TestGateway
└── TestGateway/invoke    → Gateway 호출 권한
```

| 항목 | 값 | 설명 |
|------|-----|------|
| Identifier | `TestGateway` | Resource Server 식별자 |
| Scope Name | `invoke` | 권한 이름 |
| Full Scope | `TestGateway/invoke` | 토큰 요청 시 사용하는 전체 scope |

#### 일반적인 Resource Server 예시

```
Resource Server: insurance-api
├── insurance-api/read        → 조회 권한
├── insurance-api/write       → 수정 권한
├── insurance-api/approve     → 승인 권한
└── insurance-api/admin       → 관리자 권한
```

#### 토큰 요청 시 Scope 사용

```bash
curl -X POST https://agentcore-****.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=****" \
  -d "client_secret=****" \
  -d "scope=TestGateway/invoke"
```

## OAuth2 인증 플로우

### 1. Authorization Code Flow (사용자 로그인용)

```
┌──────────┐         ┌─────────────┐         ┌─────────────┐
│  사용자   │         │   Web App   │         │   Cognito   │
│ (브라우저)│         │   (Client)  │         │ (User Pool) │
└────┬─────┘         └──────┬──────┘         └──────┬──────┘
     │                      │                       │
     │  1. 로그인 클릭      │                       │
     │─────────────────────>│                       │
     │                      │                       │
     │  2. Cognito 로그인 페이지로 리다이렉트        │
     │<─────────────────────────────────────────────│
     │                      │                       │
     │  3. 이메일/비밀번호 입력                     │
     │─────────────────────────────────────────────>│
     │                      │                       │
     │  4. Authorization Code 반환                  │
     │<─────────────────────────────────────────────│
     │                      │                       │
     │                      │  5. Code → Token 교환 │
     │                      │──────────────────────>│
     │                      │                       │
     │                      │  6. Access Token 반환 │
     │                      │<──────────────────────│
     │                      │                       │
     │  7. 로그인 완료      │                       │
     │<─────────────────────│                       │
```

**특징**:
- 사용자가 직접 로그인
- ID Token + Access Token + Refresh Token 발급
- 웹/모바일 앱에서 사용

### 2. Client Credentials Flow (M2M용)

```
┌─────────────────┐                      ┌─────────────────┐
│   Backend App   │                      │     Cognito     │
│   (M2M Client)  │                      │   Token 엔드포인트 │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         │  1. POST /oauth2/token                 │
         │     client_id + client_secret          │
         │     grant_type=client_credentials      │
         │     scope=openid                       │
         │───────────────────────────────────────>│
         │                                        │
         │  2. Access Token 반환                  │
         │     (사용자 로그인 없이!)              │
         │<───────────────────────────────────────│
         │                                        │
```

**특징**:
- 사용자 로그인 **불필요** (서버 간 통신)
- Access Token만 발급 (ID Token 없음)
- AgentCore 튜토리얼에서 사용하는 방식

**Python 코드 예시**:
```python
import requests
import base64

def get_bearer_token(token_url, client_id, client_secret, scope="openid"):
    """M2M Client Credentials Flow로 토큰 발급"""

    # Basic Auth 헤더 생성
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

## Lambda Triggers (Lambda 트리거)

### Pre Token Generation Trigger

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

### Lambda 버전별 차이

| 버전 | 지원 플로우 | M2M 지원 |
|------|------------|---------|
| V1_0 | 사용자 로그인 | ❌ |
| V2_0 | 사용자 로그인 | ❌ |
| **V3_0** | 사용자 로그인 + **Client Credentials** | ✅ |

**중요**: M2M (Client Credentials) 플로우에서 커스텀 클레임을 추가하려면 **V3_0 필수**!

### Lambda 코드 예시 (V3_0)

```python
def lambda_handler(event, context):
    """Pre Token Generation V3_0 Trigger"""

    # 트리거 소스 확인
    trigger_source = event.get('triggerSource', '')

    # Client Credentials 플로우인 경우
    if trigger_source == 'TokenGeneration_ClientCredentials':
        # 커스텀 클레임 추가
        event['response']['claimsAndScopeOverrideDetails'] = {
            'accessTokenGeneration': {
                'claimsToAddOrOverride': {
                    'department_name': 'finance',
                    'groups': 'admins,users'
                }
            }
        }

    return event
```

## Cognito 티어

| 티어 | Lambda Trigger V3_0 | 가격 |
|------|---------------------|------|
| Lite | ❌ | 무료 (제한적) |
| **Essentials** | ✅ | 유료 |
| **Plus** | ✅ | 유료 (추가 기능) |

**중요**: M2M + 커스텀 클레임을 사용하려면 **Essentials** 또는 **Plus** 티어 필요!

## AgentCore Gateway와 통합

### 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌──────────────┐                                                           │
│  │   Cognito    │                                                           │
│  │  User Pool   │                                                           │
│  │              │                                                           │
│  │ ┌──────────┐ │    ┌─────────────┐                                       │
│  │ │M2M Client│─┼───>│ Lambda      │ Pre Token V3_0                        │
│  │ └──────────┘ │    │ Trigger     │ (커스텀 클레임 추가)                   │
│  └──────┬───────┘    └─────────────┘                                       │
│         │                                                                    │
│         │ Access Token                                                       │
│         │ + 커스텀 클레임                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AgentCore Gateway                               │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐         ┌─────────────────────────────────┐   │   │
│  │  │  JWT Authorizer │         │        Policy Engine            │   │   │
│  │  │                 │         │        (Cedar 정책)              │   │   │
│  │  │ 검증:           │         │                                 │   │   │
│  │  │ - 서명          │   OK    │  principal.getTag("department") │   │   │
│  │  │ - 만료          │────────>│  principal.getTag("groups")     │   │   │
│  │  │ - client_id     │         │  context.input.amount           │   │   │
│  │  │ - scope         │         │                                 │   │   │
│  │  └─────────────────┘         └────────────────┬────────────────┘   │   │
│  │                                               │                     │   │
│  │                                        ┌──────┴──────┐              │   │
│  │                                        │             │              │   │
│  │                                     허용 ✓        거부 ✗            │   │
│  │                                        │             │              │   │
│  │                                        ▼             │              │   │
│  │                                 ┌───────────┐        │              │   │
│  │                                 │  Lambda   │        │              │   │
│  │                                 │  Target   │        │              │   │
│  │                                 └───────────┘        │              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gateway JWT Authorizer 설정

```python
{
    "customJWTAuthorizer": {
        "discoveryUrl": "https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration",
        "allowedClients": ["{client_id}"],
        "allowedAudience": [],        # Cognito는 aud 없음!
        "allowedScopes": ["openid"]
    }
}
```

### 클레임 → Principal Tags 매핑

JWT 토큰의 클레임이 Cedar에서 `principal.getTag()`로 접근됩니다.

| JWT 클레임 | Cedar 접근 방식 |
|-----------|-----------------|
| `client_id` | `principal.id` |
| `department_name` (커스텀) | `principal.getTag("department_name")` |
| `groups` (커스텀) | `principal.getTag("groups")` |
| `scope` | `principal.getTag("scope")` |

## 일반적인 구성 패턴

### 단일 User Pool, 다중 App Client

```
User Pool (us-east-1_ABC123)
│
├── App Client: Web Application
│   └── Authorization Code Flow (사용자 로그인)
│
├── App Client: Mobile App
│   └── Authorization Code Flow + PKCE
│
├── App Client: Agent Service (M2M)
│   └── Client Credentials Flow
│
└── App Client: Admin Tool (M2M)
    └── Client Credentials Flow + 추가 scope
```

### 환경별 분리

```
Production User Pool (us-east-1_PROD)
└── Production App Clients

Staging User Pool (us-east-1_STAGE)
└── Staging App Clients

Development User Pool (us-east-1_DEV)
└── Development App Clients
```

## 요약

| 구성 요소 | 역할 | 비유 |
|----------|------|------|
| User Pool | 사용자 저장소 | 회원 명부 |
| App Client | 접근 애플리케이션 | 출입증 발급기 |
| Resource Server | 권한 정의 | 권한 목록표 |
| Lambda Trigger | 토큰 커스터마이징 | 출입증에 스티커 붙이기 |
| JWT Token | 인증 증명서 | 출입증 |

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   Cognito User Pool  = 회원 관리 시스템                      │
│                                                              │
│   App Client         = 앱별 설정 (어떤 앱이 접근하는지)       │
│                                                              │
│   Lambda Trigger     = 토큰에 추가 정보 삽입                 │
│                                                              │
│   JWT Token          = 발급된 출입증 (클레임 포함)            │
│                                                              │
│   Gateway Authorizer = 출입증 검사                           │
│                                                              │
│   Cedar Policy       = 세부 출입 규칙 (어디까지 갈 수 있는지) │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## setup-gateway.py에서 생성되는 Cognito 리소스

`create_oauth_authorizer_with_cognito("TestGateway")` 호출 시 다음 리소스가 생성됩니다:

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
└─────────────────────────────────────────────────────────────────┘
```

### 생성된 리소스 요약

| 리소스 | 이름/값 | 저장 위치 |
|--------|---------|-----------|
| User Pool Name | `agentcore-gateway-****` | (AWS 콘솔에서 확인) |
| User Pool ID | `us-east-1_****` | `gateway_config.json` → `client_info.user_pool_id` |
| Domain | `agentcore-****` | `gateway_config.json` → `client_info.domain_prefix` |
| Token Endpoint | `https://{domain}.auth.{region}.amazoncognito.com/oauth2/token` | `gateway_config.json` → `client_info.token_endpoint` |
| Resource Server | `TestGateway` | (AWS 콘솔에서 확인) |
| Scope | `TestGateway/invoke` | `gateway_config.json` → `client_info.scope` |
| Client ID | `****` | `gateway_config.json` → `client_info.client_id` |
| Client Secret | `****` | `gateway_config.json` → `client_info.client_secret` |

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

## 참고 자료

- [Amazon Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [OAuth2 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
- [Cognito Lambda Triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html)
