# AgentCore Identity - Outbound Auth 3LO (Google Calendar)

Amazon Bedrock AgentCore의 **3-Legged OAuth (3LO)** 를 사용하여 Google Calendar에 접근하는 튜토리얼입니다.

---

# Part 1: 개념 및 아키텍처 (How It Works)

이 파트에서는 3LO 인증의 개념과 전체 아키텍처를 설명합니다.

---

## 1.1 개요

### 튜토리얼 목적

| 항목 | 설명 |
|------|------|
| **목적** | Agent가 사용자의 Google Calendar 데이터에 접근 |
| **인증 방식** | OAuth 2.0 3LO (사용자 동의 필요) |
| **핵심 기능** | Session Binding을 통한 보안 강화 |

### 기술 스택

| 컴포넌트 | 기술 |
|----------|------|
| Agent Framework | Strands Agents |
| LLM Model | Claude Haiku 4.5 |
| 배포 환경 | Amazon Bedrock AgentCore Runtime |
| Inbound Auth | Amazon Cognito |
| Outbound Auth | Google OAuth 2.0 |

---

## 1.2 2LO vs 3LO 비교

### OAuth 2.0 Two-Legged (2LO)

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Agent     │───────▶│  AgentCore  │───────▶│  External   │
│             │        │  Identity   │        │  API        │
└─────────────┘        └─────────────┘        └─────────────┘
                              │
                              ▼
                       API Key / Secret
                       (애플리케이션 소유)
```

**특징:**
- 사용자 동의 **불필요**
- 애플리케이션이 자체 자격 증명 사용
- 예: API Key로 서비스 호출

### OAuth 2.0 Three-Legged (3LO)

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   User      │◀──────▶│  AgentCore  │───────▶│  Google     │
│  (동의)     │        │  Identity   │        │  Calendar   │
└─────────────┘        └─────────────┘        └─────────────┘
      │                       │                      │
      │                       ▼                      │
      │                Token Vault                   │
      │                (사용자별 토큰)                │
      │                       │                      │
      └───────── 사용자 데이터 접근 ─────────────────┘
```

**특징:**
- 사용자 동의 **필수**
- 사용자 대신(On-Behalf-Of) 데이터 접근
- 예: 사용자의 Google Calendar 조회

### 비교표

| | 2LO (Two-Legged) | 3LO (Three-Legged) |
|---|---|---|
| **사용자 동의** | 없음 | **있음** (핵심 차이) |
| **용도** | 서버-서버 통신 | 사용자 데이터 접근 |
| **예시** | API Key로 날씨 조회 | 사용자 Google Calendar |
| **토큰 소유자** | 애플리케이션 | 개별 사용자 |
| **auth_flow** | `M2M` | `USER_FEDERATION` |

---

## 1.3 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              전체 시스템 아키텍처                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────────────┐    │
│  │              │     │                  │     │                          │    │
│  │  User        │────▶│  Application     │────▶│  AgentCore Runtime       │    │
│  │  (Browser)   │     │  (Streamlit)     │     │  (Strands Agent)         │    │
│  │              │     │                  │     │                          │    │
│  └──────────────┘     └──────────────────┘     └────────────┬─────────────┘    │
│         │                      │                            │                   │
│         │                      │                            ▼                   │
│         │              ┌───────┴───────┐         ┌──────────────────────┐      │
│         │              │               │         │                      │      │
│         │              │  OAuth2       │         │  AgentCore Identity  │      │
│         │              │  Callback     │◀───────▶│  Service             │      │
│         │              │  Server       │         │                      │      │
│         │              │               │         │  - Credential        │      │
│         │              └───────────────┘         │    Provider          │      │
│         │                                        │  - Token Vault       │      │
│         │                                        │  - Workload Identity │      │
│         │                                        │                      │      │
│         │                                        └──────────┬───────────┘      │
│         │                                                   │                   │
│         │              ┌──────────────────┐                 │                   │
│         │              │                  │                 │                   │
│         └─────────────▶│  Google OAuth    │◀────────────────┘                   │
│                        │  Server          │                                     │
│                        │                  │                                     │
│                        └────────┬─────────┘                                     │
│                                 │                                               │
│                                 ▼                                               │
│                        ┌──────────────────┐                                     │
│                        │                  │                                     │
│                        │  Google Calendar │                                     │
│                        │  API             │                                     │
│                        │                  │                                     │
│                        └──────────────────┘                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 컴포넌트 역할

| 컴포넌트 | 역할 |
|----------|------|
| **User (Browser)** | Google 로그인 및 동의 |
| **Application (Streamlit)** | 사용자 인터페이스, Cognito 인증 |
| **AgentCore Runtime** | Agent 실행 환경 |
| **OAuth2 Callback Server** | Session Binding 처리 |
| **AgentCore Identity** | 토큰 관리, Credential Provider |
| **Google OAuth Server** | OAuth 인증 처리 |
| **Google Calendar API** | 캘린더 데이터 제공 |

---

## 1.4 OAuth 2.0 3LO 흐름

### 4단계 흐름

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OAuth 2.0 3LO 흐름                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║  [1단계] Agent 호출                                                       ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                           ║  │
│  ║   User ──▶ "오늘 일정 뭐야?" ──▶ Application ──▶ Agent                    ║  │
│  ║                                                                           ║  │
│  ║   • Agent가 Google Calendar 접근 필요 인식                                ║  │
│  ║   • OAuth2 토큰 요청 시작                                                 ║  │
│  ║                                                                           ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                     │                                           │
│                                     ▼                                           │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║  [2단계] Authorization URL 생성                                           ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                           ║  │
│  ║   Agent ──▶ AgentCore Identity ──▶ Google OAuth Server                    ║  │
│  ║                    │                                                      ║  │
│  ║                    ▼                                                      ║  │
│  ║   ◀── Authorization URL + Session URI 반환                                ║  │
│  ║                                                                           ║  │
│  ║   • Workload Access Token 발급                                            ║  │
│  ║   • Session URI 생성 (보안용)                                             ║  │
│  ║                                                                           ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                     │                                           │
│                                     ▼                                           │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║  [3단계] 사용자 동의 및 토큰 획득 ⭐ 핵심 단계                            ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                           ║  │
│  ║   User ──▶ Google 로그인 ──▶ "허용" 클릭                                  ║  │
│  ║                    │                                                      ║  │
│  ║                    ▼                                                      ║  │
│  ║   Google ──▶ Callback Server (authorization code)                         ║  │
│  ║                    │                                                      ║  │
│  ║                    ▼                                                      ║  │
│  ║   Callback Server ──▶ CompleteResourceTokenAuth()                         ║  │
│  ║                    │     (session_id + user_token)                        ║  │
│  ║                    ▼                                                      ║  │
│  ║   AgentCore Identity ──▶ Token Vault에 저장                               ║  │
│  ║                                                                           ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                     │                                           │
│                                     ▼                                           │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║  [4단계] Agent 재호출 및 토큰 사용                                        ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                           ║  │
│  ║   Agent ──▶ Token Vault에서 Access Token 조회                             ║  │
│  ║                    │                                                      ║  │
│  ║                    ▼                                                      ║  │
│  ║   Agent ──▶ Google Calendar API ──▶ 캘린더 데이터                         ║  │
│  ║                    │                                                      ║  │
│  ║                    ▼                                                      ║  │
│  ║   User ◀── "오늘 일정: 10시 회의, 2시 미팅..."                            ║  │
│  ║                                                                           ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1.5 Session Binding (세션 바인딩)

### 왜 필요한가?

OAuth 흐름에서 **세션 하이재킹**을 방지하기 위해 필요합니다.

### 공격 시나리오 (Session Binding 없이)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ⚠️ 공격 시나리오 (Session Binding 없이)                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   [1] 악의적 사용자 A                                                           │
│       └── OAuth 흐름 시작                                                       │
│       └── Authorization URL 획득                                                │
│                                                                                 │
│   [2] 공격자 A가 피해자 B에게 URL 전송                                          │
│       └── "이 링크 클릭해주세요"                                                │
│                                                                                 │
│   [3] 피해자 B                                                                  │
│       └── 자신의 Google 계정으로 로그인                                         │
│       └── "허용" 클릭                                                           │
│                                                                                 │
│   [4] 결과: 공격자 A가 피해자 B의 Google 데이터에 접근 가능! 🚨                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Session Binding으로 해결

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ✅ Session Binding으로 보호                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   [1] OAuth 시작 시                                                             │
│       └── Session URI 생성 + 요청한 사용자 정보 기록                            │
│                                                                                 │
│   [2] OAuth 완료 시 (Callback)                                                  │
│       └── CompleteResourceTokenAuth(session_uri, user_token) 호출              │
│                                                                                 │
│   [3] AgentCore Identity 검증                                                   │
│       └── "OAuth 시작한 사용자" vs "동의한 사용자" 비교                         │
│                                                                                 │
│   [4] 결과                                                                      │
│       ├── 일치 → 토큰 발급 ✅                                                   │
│       └── 불일치 → 토큰 발급 거부 ❌                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1.6 Authorization URL vs Callback URL

OAuth 흐름에서 사용되는 두 가지 핵심 URL입니다.

### Authorization URL (인증 URL)

**사용자가 클릭하여 로그인/동의하러 가는 URL**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Authorization URL = "Google 로그인 페이지로 가는 링크"                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Agent ──▶ "이 URL을 클릭하세요"                                                │
│                    │                                                            │
│                    ▼                                                            │
│  https://accounts.google.com/o/oauth2/auth?                                     │
│    client_id=882989917280-xxx.apps.googleusercontent.com&                       │
│    redirect_uri=https://bedrock-agentcore.../callback&                          │
│    scope=https://www.googleapis.com/auth/calendar.readonly&                     │
│    response_type=code&                                                          │
│    state=session-abc123                                                         │
│                    │                                                            │
│                    ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      Google 로그인 페이지                               │    │
│  │                                                                         │    │
│  │   "MyAgent 앱이 Google Calendar 접근을 요청합니다"                      │    │
│  │                                                                         │    │
│  │              [ 허용 ]      [ 거부 ]                                     │    │
│  │                                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Authorization URL 구성 요소:**

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| `client_id` | Google에서 발급받은 앱 ID | `882989917280-xxx.apps.googleusercontent.com` |
| `redirect_uri` | 동의 후 돌아올 URL (Callback URL) | `https://bedrock-agentcore.../callback` |
| `scope` | 요청하는 권한 | `calendar.readonly` |
| `response_type` | 응답 타입 | `code` (Authorization Code) |
| `state` | Session URI (보안용) | `session-abc123` |

### Callback URL (콜백 URL)

**사용자가 "허용" 클릭 후 돌아오는 URL**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Callback URL = "동의 완료 후 돌아오는 주소"                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  사용자가 [ 허용 ] 클릭                                                         │
│                    │                                                            │
│                    ▼                                                            │
│  Google이 자동으로 리다이렉트                                                   │
│                    │                                                            │
│                    ▼                                                            │
│  http://localhost:9090/oauth2/callback?                                         │
│    code=4/0AY0e-g7xxxxxx&           ← Authorization Code                        │
│    state=session-abc123&            ← Session URI (확인용)                      │
│    session_id=session-abc123        ← Session ID                                │
│                    │                                                            │
│                    ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  OAuth2 Callback Server (localhost:9090)                                │    │
│  │                                                                         │    │
│  │  1. session_id 확인                                                     │    │
│  │  2. complete_resource_token_auth() 호출                                 │    │
│  │  3. "OAuth2 3LO flow completed!" 표시                                   │    │
│  │                                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 전체 흐름에서 보기

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Authorization URL & Callback URL 흐름                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [1] Agent가 Authorization URL 생성                                             │
│      ┌─────────────────────────────────────────────────────────────────────┐    │
│      │ Authorization URL:                                                  │    │
│      │ https://accounts.google.com/o/oauth2/auth?                          │    │
│      │   redirect_uri=http://localhost:9090/oauth2/callback                │    │
│      └─────────────────────────────────────────────────────────────────────┘    │
│                               │                                                 │
│                               ▼                                                 │
│  [2] 사용자가 Authorization URL 클릭                                            │
│                               │                                                 │
│                               ▼                                                 │
│  [3] Google 로그인 + 동의 페이지                                                │
│                               │                                                 │
│                               ▼                                                 │
│  [4] 사용자가 "허용" 클릭                                                       │
│                               │                                                 │
│                               ▼                                                 │
│  [5] Google이 Callback URL로 리다이렉트                                         │
│      ┌─────────────────────────────────────────────────────────────────────┐    │
│      │ Callback URL:                                                       │    │
│      │ http://localhost:9090/oauth2/callback?                              │    │
│      │   code=4/0AY0e...&session_id=abc123                                 │    │
│      └─────────────────────────────────────────────────────────────────────┘    │
│                               │                                                 │
│                               ▼                                                 │
│  [6] Callback Server가 처리 → Access Token 발급                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 비유로 이해하기

| OAuth | 실생활 비유 (택배) |
|-------|-------------------|
| **Authorization URL** | 택배 접수 페이지 URL |
| 클릭하면 | 택배 접수 페이지로 이동 |
| 정보 입력 | 보내는 사람, 받는 사람 정보 입력 |
| "허용" 클릭 | "접수 완료" 버튼 클릭 |
| **Callback URL** | 접수 완료 후 보여주는 확인 페이지 |
| 돌아오는 정보 | 송장번호 (Authorization Code) |

### 요약 비교표

| | Authorization URL | Callback URL |
|---|---|---|
| **방향** | 앱 → Google (보내는 곳) | Google → 앱 (돌아오는 곳) |
| **언제** | OAuth 시작 시 | "허용" 클릭 후 |
| **누가 생성** | AgentCore Identity | 개발자가 미리 설정 |
| **목적** | 사용자를 로그인/동의 페이지로 보냄 | 인증 코드를 받아서 처리 |
| **예시** | `https://accounts.google.com/...` | `http://localhost:9090/oauth2/callback` |

---

## 1.7 Workload Access Token

**Workload Access Token**은 Agent(워크로드)가 AgentCore Identity 서비스와 통신하기 위해 사용하는 **내부 인증 토큰**입니다.

### 두 가지 토큰 비교

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             토큰 종류 비교                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────┐  ┌───────────────────────────────────┐   │
│  │  User Access Token (Bearer)       │  │  Workload Access Token            │   │
│  │  (사용자 토큰)                    │  │  (워크로드 토큰)                  │   │
│  ├───────────────────────────────────┤  ├───────────────────────────────────┤   │
│  │                                   │  │                                   │   │
│  │  발급: Cognito                    │  │  발급: AgentCore Identity         │   │
│  │                                   │  │                                   │   │
│  │  용도: "사용자가 누구인지"        │  │  용도: "Agent가 누구인지"         │   │
│  │                                   │  │                                   │   │
│  │  사용처: Agent 호출 시            │  │  사용처: AgentCore 내부 통신      │   │
│  │          (Inbound Auth)           │  │          (Outbound Auth)          │   │
│  │                                   │  │                                   │   │
│  └───────────────────────────────────┘  └───────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Workload Access Token 발급 흐름

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Workload Access Token 발급 및 사용                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [1] Agent가 AgentCore Runtime에서 실행됨                                       │
│                    │                                                            │
│                    ▼                                                            │
│  [2] Agent가 외부 API 접근 필요 (Google Calendar)                               │
│      └── @requires_access_token 데코레이터 호출                                 │
│                    │                                                            │
│                    ▼                                                            │
│  [3] AgentCore SDK가 Workload Access Token 요청                                 │
│      ┌─────────────────────────────────────────────────────────────────────┐    │
│      │  Agent ──▶ AgentCore Identity                                       │    │
│      │            "나는 strands_agent_google_3lo 워크로드야"                │    │
│      │            "Workload Access Token 줘"                                │    │
│      └─────────────────────────────────────────────────────────────────────┘    │
│                    │                                                            │
│                    ▼                                                            │
│  [4] AgentCore Identity가 Workload Identity 확인                                │
│      └── "strands_agent_google_3lo" 워크로드가 등록되어 있는지 확인             │
│      └── IAM Role 권한 확인                                                     │
│                    │                                                            │
│                    ▼                                                            │
│  [5] Workload Access Token 발급                                                 │
│      ┌─────────────────────────────────────────────────────────────────────┐    │
│      │  {                                                                  │    │
│      │    "token": "eyJhbGciOiJSUzI1NiIs...",                              │    │
│      │    "workload_identity": "strands_agent_google_3lo",                 │    │
│      │    "expires_in": 3600                                               │    │
│      │  }                                                                  │    │
│      └─────────────────────────────────────────────────────────────────────┘    │
│                    │                                                            │
│                    ▼                                                            │
│  [6] Agent가 Workload Access Token으로 Google OAuth2 토큰 요청                  │
│      └── AgentCore Identity에 "google-cal-provider"의 토큰 요청                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 왜 필요한가?

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Workload Access Token이 필요한 이유                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  문제: Agent가 AgentCore Identity에 요청할 때                                   │
│        "나는 정당한 Agent야" 라는 것을 어떻게 증명할까?                         │
│                                                                                 │
│  해결: Workload Access Token                                                    │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                                                                         │    │
│  │  Agent (Container)                                                      │    │
│  │       │                                                                 │    │
│  │       │ "Google OAuth2 토큰 줘"                                         │    │
│  │       │ + Workload Access Token (증명서)                                │    │
│  │       │                                                                 │    │
│  │       ▼                                                                 │    │
│  │  AgentCore Identity                                                     │    │
│  │       │                                                                 │    │
│  │       ├── Workload Access Token 검증 ✅                                 │    │
│  │       ├── Workload Identity 확인 ✅                                     │    │
│  │       ├── 권한 확인 (allowedResourceOauth2ReturnUrls 등) ✅             │    │
│  │       │                                                                 │    │
│  │       ▼                                                                 │    │
│  │  Google OAuth2 토큰 발급                                                │    │
│  │                                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 비유로 이해하기

| 실생활 비유 | OAuth 흐름 |
|-------------|------------|
| **회사 사원증** | Workload Access Token |
| 사원증 발급 | Agent가 AgentCore Runtime에 배포될 때 |
| 사원증 제시 | Agent가 AgentCore Identity에 요청할 때 |
| 사원증 확인 | AgentCore Identity가 토큰 검증 |
| 권한 확인 | "이 Agent가 Google Calendar Provider 사용 가능한가?" |

### 코드에서 (자동 처리)

Workload Access Token은 **AgentCore SDK가 자동으로 처리**합니다:

```python
@requires_access_token(
    provider_name="google-cal-provider",
    scopes=SCOPES,
    auth_flow='USER_FEDERATION',
    ...
)
async def need_token_3lo_async(*, access_token: str) -> str:
    # 내부적으로:
    # 1. SDK가 Workload Access Token 자동 획득
    # 2. Workload Access Token으로 AgentCore Identity 호출
    # 3. Google OAuth2 Access Token 획득
    # 4. access_token 파라미터로 전달
    return access_token
```

### 요약

| 항목 | 설명 |
|------|------|
| **무엇** | Agent(워크로드)를 인증하는 내부 토큰 |
| **발급자** | AgentCore Identity Service |
| **사용자** | Agent (Container) |
| **용도** | AgentCore Identity와 통신할 때 Agent 신원 증명 |
| **개발자가 관리?** | 아니오, SDK가 자동 처리 |

---

## 1.8 파일 구조 및 역할

```
05-Outbound_Auth_3lo/
│
├── runtime_with_strands_and_egress_3lo.ipynb   # 📓 메인 노트북 (전체 튜토리얼)
│
├── strands_claude_google_3lo.py                # 🤖 Agent 코드 (자동 생성)
│   └── @tool: Get_calendar_events_today
│   └── @requires_access_token: 3LO 토큰 요청
│   └── @app.entrypoint: AgentCore 진입점
│
├── oauth2_callback_server.py                   # 🔐 OAuth2 콜백 서버
│   └── POST /userIdentifier/token: 사용자 토큰 저장
│   └── GET /oauth2/callback: OAuth 완료 처리
│   └── GET /ping: Health Check
│
├── chatbot_app_cognito.py                      # 💬 Streamlit UI
│   └── Cognito 로그인
│   └── Agent 스트리밍 호출
│
├── runtime.py                                  # 🛠️ AgentCore 클라이언트 유틸리티
│
└── requirements.txt                            # 📦 의존성 패키지
```

---

## 1.9 노트북 실행 흐름 (High Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           노트북 실행 순서 (10단계)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  [준비 단계]                                                            │   │
│   ├─────────────────────────────────────────────────────────────────────────┤   │
│   │  [1] Cognito 설정 ─────────▶ Inbound Auth (사용자 인증)                 │   │
│   │  [2] Google OAuth2 Provider ▶ Outbound Auth (외부 API 인증)             │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                           │
│                                     ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  [배포 단계]                                                            │   │
│   ├─────────────────────────────────────────────────────────────────────────┤   │
│   │  [3] Agent 코드 생성 ──────▶ strands_claude_google_3lo.py               │   │
│   │  [4] AgentCore 설정 ───────▶ .bedrock_agentcore.yaml                    │   │
│   │  [5] Agent 배포 ───────────▶ CodeBuild → ECR → Runtime                  │   │
│   │  [6] Workload Identity ────▶ Callback URL 등록                          │   │
│   │  [7] IAM 정책 추가 ────────▶ GetResourceToken 권한                      │   │
│   │  [8] 상태 확인 ────────────▶ READY 대기                                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                           │
│                                     ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  [테스트 단계]                                                          │   │
│   ├─────────────────────────────────────────────────────────────────────────┤   │
│   │  [9] Agent 호출 ───────────▶ 3LO 흐름 테스트                            │   │
│   │  [10] Streamlit 앱 ────────▶ 웹 UI 테스트 (선택)                        │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

---

# Part 2: 상세 구현 (Implementation Details)

이 파트에서는 각 컴포넌트의 상세 코드와 구현 방법을 설명합니다.

---

## 2.1 Cognito 설정 (Inbound Auth)

### 토큰 종류

| 토큰 | 설명 | 유효 기간 |
|------|------|-----------|
| **Access Token (Bearer)** | API 호출 시 인증에 사용 | 기본 1시간 |
| **Refresh Token** | Access Token 만료 시 재발급용 | 기본 30일 |
| **ID Token** | 사용자 정보 포함 | 기본 1시간 |

### 토큰 생성 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User Pool 생성                                              │
│     cognito_client.create_user_pool(PoolName=...)               │
│                         ↓                                       │
│  2. App Client 생성                                             │
│     cognito_client.create_user_pool_client(...)                 │
│                         ↓                                       │
│  3. 사용자 생성                                                 │
│     cognito_client.admin_create_user(Username='testuser')       │
│                         ↓                                       │
│  4. 비밀번호 설정                                               │
│     cognito_client.admin_set_user_password(Password=...)        │
│                         ↓                                       │
│  5. 인증 → 토큰 발급                                            │
│     cognito_client.initiate_auth(AuthFlow='USER_PASSWORD_AUTH') │
│                         ↓                                       │
│     반환: AccessToken (Bearer), RefreshToken, IdToken           │
└─────────────────────────────────────────────────────────────────┘
```

### 코드: Cognito 설정

**파일:** `utils.py`

```python
from utils import setup_cognito_user_pool, reauthenticate_user

# Cognito User Pool 생성 및 테스트 사용자 설정
cognito_config = setup_cognito_user_pool("Cognito_3LO_Google")

# 결과
pool_id = cognito_config["pool_id"]           # us-west-2_xxxxx
client_id = cognito_config["client_id"]       # App Client ID
bearer_token = cognito_config["bearer_token"] # JWT Access Token
discovery_url = cognito_config["discovery_url"] # OIDC Discovery URL
```

### 코드: 토큰 재발급

```python
def reauthenticate_user(client_id, username='testuser', password='MyPassword123!'):
    """만료된 토큰을 재발급"""
    cognito_client = boto3.client('cognito-idp', region_name='us-west-2')

    auth_response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )

    return auth_response['AuthenticationResult']['AccessToken']

# 사용 예시 (토큰 만료 시)
bearer_token = reauthenticate_user(cognito_config.get("client_id"))
```

---

## 2.2 Google OAuth2 Credential Provider 생성

### 코드: Provider 생성

```python
from bedrock_agentcore.services.identity import IdentityClient

identity_client = IdentityClient(region)

# Google OAuth2 Provider 생성
google_provider = identity_client.create_oauth2_credential_provider({
    "name": "google-cal-provider",
    "credentialProviderVendor": "GoogleOauth2",
    "oauth2ProviderConfigInput": {
        "googleOauth2ProviderConfig": {
            "clientId": "<your-google-client-id>",
            "clientSecret": "<your-google-client-secret>"
        }
    }
})

print(f"Provider ARN: {google_provider['credentialProviderArn']}")
print(f"Callback URL: {google_provider['callbackUrl']}")
```

### 지원되는 Provider Vendors

| Vendor | credentialProviderVendor |
|--------|--------------------------|
| Google | `GoogleOauth2` |
| GitHub | `GithubOauth2` |
| Slack | `SlackOauth2` |
| Salesforce | `SalesforceOauth2` |
| Custom | `CustomOauth2` |

### 중요: Google Console 설정

`callbackUrl`을 Google Developer Console에 등록해야 합니다:

1. [Google Developer Console](https://console.developers.google.com/) 접속
2. **APIs & Services** → **Credentials**
3. OAuth 2.0 Client ID 클릭
4. **Authorized redirect URIs**에 추가:
   ```
   https://bedrock-agentcore.us-west-2.amazonaws.com/identities/oauth2/callback/<provider-id>
   ```
5. **Save** 클릭

---

## 2.3 Agent 코드 (strands_claude_google_3lo.py)

### 2.3.1 Tool 정의

```python
from strands import Agent, tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import datetime

# OAuth2 스코프
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# 전역 변수: 3LO로 획득한 토큰
google_access_token: Optional[str] = None

@tool(
    name="Get_calendar_events_today",
    description="Retrieves the calendar events for the day from your Google Calendar"
)
def get_calendar_events_today() -> str:
    """오늘의 Google Calendar 일정을 조회"""
    global google_access_token

    # 토큰이 없으면 인증 필요 응답
    if not google_access_token:
        return json.dumps({
            "auth_required": True,
            "message": "Google Calendar authentication is required.",
            "events": []
        })

    # Google Calendar API 호출
    creds = Credentials(token=google_access_token, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

    # 오늘 날짜 범위 계산
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    time_min = today_start.strftime('%Y-%m-%dT00:00:00-05:00')
    time_max = today_end.strftime('%Y-%m-%dT23:59:59-05:00')

    # API 호출
    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return json.dumps({"events": events_result.get("items", [])})
```

### 2.3.2 3LO 토큰 요청 (@requires_access_token)

```python
from bedrock_agentcore.identity.auth import requires_access_token

# Authorization URL 콜백 함수
async def on_auth_url(url: str) -> None:
    """Authorization URL을 사용자에게 전달"""
    print(f"Authorization url: {url}")
    await queue.put(f"Authorization url: {url}")

@requires_access_token(
    provider_name="google-cal-provider",      # Credential Provider 이름
    scopes=SCOPES,                            # OAuth2 권한 범위
    auth_flow='USER_FEDERATION',              # 3LO 흐름 (사용자 동의 필요)
    on_auth_url=on_auth_url,                  # Authorization URL 콜백
    force_authentication=True,                # 매번 재인증 (테스트용)
    callback_url="http://localhost:9090/oauth2/callback"  # Session Binding 콜백
)
async def need_token_3lo_async(*, access_token: str) -> str:
    """3LO 흐름으로 access_token 획득"""
    global google_access_token
    google_access_token = access_token
    return access_token
```

### @requires_access_token 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `provider_name` | str | Credential Provider 이름 |
| `scopes` | list | OAuth2 권한 범위 |
| `auth_flow` | str | `USER_FEDERATION` (3LO) 또는 `M2M` (2LO) |
| `on_auth_url` | callable | Authorization URL 콜백 함수 |
| `force_authentication` | bool | True면 매번 재인증 |
| `callback_url` | str | OAuth 완료 후 리다이렉트 URL |

### 2.3.3 Agent Entry Point

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import asyncio
from typing import Dict, Any, AsyncGenerator

app = BedrockAgentCoreApp()

# Agent 인스턴스 생성
agent = Agent(
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=[get_calendar_events_today]
)

@app.entrypoint
async def agent_invocation(payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """AgentCore Runtime 진입점"""
    user_message = payload.get("prompt", "No prompt found")

    # Agent 실행 태스크 생성
    task = asyncio.create_task(agent_task(user_message))

    # 스트리밍 응답 반환
    async def stream_with_task():
        async for item in queue.stream():
            yield item
        await task

    return stream_with_task()

if __name__ == "__main__":
    app.run()
```

### 2.3.4 Agent Task (인증 흐름 처리)

```python
async def agent_task(user_message: str) -> None:
    """Agent 실행 및 인증 처리"""
    try:
        await queue.put("Begin agent execution")

        # 첫 번째 Agent 호출
        response = agent(user_message)

        # 응답에서 텍스트 추출
        response_text = extract_text_from_response(response)

        # 인증 필요 여부 확인
        auth_keywords = ["authentication", "authorize", "auth", "sign in", "login"]
        needs_auth = any(kw in response_text.lower() for kw in auth_keywords)

        if needs_auth:
            await queue.put("Authentication required. Starting 3LO flow...")

            # 3LO 인증 시작
            global google_access_token
            google_access_token = await need_token_3lo_async(access_token='')
            await queue.put("Authentication successful!")

            # 인증 후 재시도
            response = agent(user_message)

        await queue.put(response.message)
        await queue.put("End agent execution")

    except Exception as e:
        await queue.put(f"Error: {str(e)}")
    finally:
        await queue.finish()
```

---

## 2.4 OAuth2 Callback Server (oauth2_callback_server.py)

### 2.4.1 서버 구조

```python
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from bedrock_agentcore.services.identity import IdentityClient, UserTokenIdentifier

OAUTH2_CALLBACK_SERVER_PORT = 9090

class OAuth2CallbackServer:
    def __init__(self, region: str):
        self.identity_client = IdentityClient(region=region)
        self.user_token_identifier = None  # Session Binding용 사용자 토큰
        self.app = FastAPI()
        self._setup_routes()
```

### 2.4.2 엔드포인트

```python
def _setup_routes(self):
    # 1. 사용자 토큰 저장 (Agent 호출 전 실행)
    @self.app.post("/userIdentifier/token")
    async def store_user_token(user_token_identifier_value: UserTokenIdentifier):
        """JWT 토큰을 저장하여 Session Binding에 사용"""
        self.user_token_identifier = user_token_identifier_value

    # 2. Health Check
    @self.app.get("/ping")
    async def handle_ping():
        return {"status": "success"}

    # 3. OAuth2 콜백 처리 (핵심!)
    @self.app.get("/oauth2/callback")
    async def handle_oauth2_callback(session_id: str):
        """Google OAuth 완료 후 리다이렉트 처리"""

        # session_id 검증
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing session_id query parameter"
            )

        # user_token_identifier 검증
        if not self.user_token_identifier:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No configured user token identifier"
            )

        # Session Binding: 사용자와 OAuth 세션 연결
        self.identity_client.complete_resource_token_auth(
            session_uri=session_id,
            user_identifier=self.user_token_identifier
        )

        return HTMLResponse(content="""
            <html><body>
                <h1>OAuth2 3LO flow completed successfully!</h1>
            </body></html>
        """)
```

### 2.4.3 유틸리티 함수

```python
def get_oauth2_callback_url() -> str:
    """OAuth2 콜백 URL 반환"""
    return f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}/oauth2/callback"

def store_token_in_oauth2_callback_server(user_token_value: str):
    """사용자 토큰을 Callback 서버에 저장 (Session Binding용)"""
    if user_token_value:
        requests.post(
            f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}/userIdentifier/token",
            json={"user_token": user_token_value},
            timeout=2
        )

def wait_for_oauth2_server_to_be_ready(duration=timedelta(seconds=40)) -> bool:
    """Callback 서버 준비 대기"""
    start_time = time.time()
    while time.time() - start_time < duration.seconds:
        try:
            response = requests.get(
                f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}/ping",
                timeout=2
            )
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)
    return False
```

---

## 2.5 AgentCore Runtime 설정 및 배포

### 2.5.1 설정 (configure)

```python
from bedrock_agentcore_starter_toolkit import Runtime

agentcore_runtime = Runtime()

# AgentCore Runtime 설정
response = agentcore_runtime.configure(
    entrypoint="strands_claude_google_3lo.py",    # Agent 코드 파일
    auto_create_execution_role=True,               # IAM Role 자동 생성
    auto_create_ecr=True,                          # ECR Repository 자동 생성
    requirements_file="requirements.txt",          # 의존성 파일
    region=region,
    memory_mode="NO_MEMORY",                       # Stateless 모드
    agent_name="strands_agent_google_3lo",
    authorizer_configuration={                     # Inbound Auth 설정
        "customJWTAuthorizer": {
            "discoveryUrl": discovery_url,         # Cognito OIDC Discovery URL
            "allowedClients": [client_id]          # Cognito App Client ID
        }
    }
)
```

### 2.5.2 배포 (launch)

```python
# Agent 배포 (CodeBuild → ECR → Runtime)
launch_result = agentcore_runtime.launch()

# 결과
print(f"Agent ID: {launch_result.agent_id}")
print(f"Agent ARN: {launch_result.agent_arn}")
print(f"ECR URI: {launch_result.ecr_uri}")
```

### 2.5.3 Workload Identity 업데이트

```python
# Callback URL을 Workload Identity에 등록
workload_identity = identity_client.get_workload_identity(
    name=launch_result.agent_id
)

updated_workload_identity = identity_client.update_workload_identity(
    name=launch_result.agent_id,
    allowed_resource_oauth_2_return_urls=[
        *workload_identity.get("allowedResourceOauth2ReturnUrls", []),
        "http://localhost:9090/oauth2/callback"  # 로컬 Callback URL 추가
    ]
)
```

### 2.5.4 IAM 정책 추가

```python
# GetResourceToken 권한 추가 (3LO에 필요)
iam_client = boto3.client('iam')

policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": "bedrock-agentcore:GetResourceToken",
        "Resource": "*"
    }]
}

iam_client.put_role_policy(
    RoleName=execution_role_name,
    PolicyName="GetResourceTokenPolicy",
    PolicyDocument=json.dumps(policy_document)
)
```

### 2.5.5 상태 확인

```python
import time

# READY 상태 대기
while True:
    status = agentcore_runtime.status()
    print(f"Status: {status}")

    if status == "READY":
        print("Agent is ready!")
        break
    elif status == "FAILED":
        print("Deployment failed!")
        break

    time.sleep(30)
```

---

## 2.6 Agent 호출

### 코드: Agent 호출

```python
import subprocess
import sys
from oauth2_callback_server import (
    store_token_in_oauth2_callback_server,
    wait_for_oauth2_server_to_be_ready
)

# 1. 토큰 재발급 (2시간 만료)
bearer_token = reauthenticate_user(cognito_config.get("client_id"))

# 2. OAuth2 Callback 서버 시작
oauth2_callback_server_process = subprocess.Popen([
    sys.executable, "oauth2_callback_server.py", "--region", region
])

# 3. 서버 준비 대기
if not wait_for_oauth2_server_to_be_ready():
    raise Exception("OAuth2 callback server failed to start")

# 4. 사용자 토큰을 Callback 서버에 저장 (Session Binding용)
store_token_in_oauth2_callback_server(bearer_token)

# 5. Agent 호출
invoke_response = agentcore_runtime.invoke(
    {"prompt": "What is in my agenda for today?"},
    bearer_token=bearer_token
)

# 6. 응답 출력
for chunk in invoke_response:
    print(chunk, end="", flush=True)

# 7. Callback 서버 종료
oauth2_callback_server_process.terminate()
```

---

## 2.7 Streamlit Chatbot UI (chatbot_app_cognito.py)

### 2.7.1 Cognito 로그인

```python
import streamlit as st
import boto3

# Cognito 인증
if st.session_state["cognito_access_token"] is None:
    with st.form("cognito_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        client = boto3.client("cognito-idp", region_name=region)
        resp = client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password}
        )
        st.session_state["cognito_access_token"] = resp["AuthenticationResult"]["AccessToken"]
        st.rerun()
```

### 2.7.2 Agent 스트리밍 호출

```python
from oauth2_callback_server import store_token_in_oauth2_callback_server

# Session Binding을 위해 토큰 저장
bearer_token = st.session_state.get("cognito_access_token")
store_token_in_oauth2_callback_server(bearer_token)

# 스트리밍 클라이언트
streaming_client = StreamingHttpBedrockAgentCoreClient(region)

# Agent 호출 및 스트리밍 표시
for chunk in streaming_client.invoke_endpoint_streaming(
    agent_arn=agentRuntimeArn,
    payload=json.dumps({"prompt": user_input}),
    session_id=session_id,
    bearer_token=bearer_token
):
    st.write(chunk)
```

### 테스트 계정

| 항목 | 값 |
|------|-----|
| Username | `testuser` |
| Password | `MyPassword123!` |

---

## 2.8 requirements.txt

```
strands-agents
google-api-python-client
google-auth-oauthlib
bedrock-agentcore
bedrock-agentcore-starter-toolkit
fastapi
uvicorn
streamlit
boto3
requests
```

---

## 참고 자료

- [Amazon Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [AgentCore Identity 문서](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [OAuth 2.0 Session Binding](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/oauth2-authorization-url-session-binding.html)
- [Google Calendar API](https://developers.google.com/calendar/api/guides/overview)
- [Google OAuth 2.0 설정](https://developers.google.com/identity/protocols/oauth2)
- [Strands Agents](https://github.com/strands-agents/strands-agents)
- [AgentCore Samples - Outbound Auth 3LO](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/03-AgentCore-identity/05-Outbound_Auth_3lo)
