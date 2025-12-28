# Amazon Bedrock AgentCore Policy 튜토리얼

**AI 에이전트**가 **MCP(Model Context Protocol)** 도구를 호출하는 시스템을 구축하고 계신가요?

그렇다면 다음 질문에 답할 수 있어야 합니다:

> "Finance 팀만 환불 도구를 사용하게 하려면 어떻게 해야 하나요?"
>
> "관리자만 민감한 작업을 승인하도록 제한하려면요?"
>
> "$1,000 이상의 환불은 자동으로 차단하려면요?"

**OAuth 2.0**은 업계 표준 인증 프로토콜이지만, 단순히 "인증된 사용자"만 구분합니다.
**세분화된 인가(Fine-Grained Authorization)**가 없으면, 인증된 모든 사용자가 모든 도구를 호출할 수 있습니다.

> 많은 기업이 AI 에이전트를 도입하고 있지만, 적절한 접근 제어 없이는 보안 사고의 위험이 높아집니다.

**Amazon Bedrock AgentCore Policy**는 **Cedar 정책 언어**를 사용하여 이 문제를 해결합니다.
이 튜토리얼에서 AgentCore Policy를 활용한 세분화된 접근 제어를 직접 구현해 봅니다.

---

## 💼 해결할 비즈니스 문제

당신은 AI 에이전트가 고객 환불을 처리하는 시스템을 구축하고 있습니다.
다음 보안 요구사항을 구현해야 합니다:

### 문제 1: 부서 기반 접근 제어
> "환불 도구는 **Finance 팀**만 사용할 수 있어야 합니다.
> Engineering 팀이 실수로 환불을 처리하면 안 됩니다."

### 문제 2: 역할 기반 접근 제어
> "민감한 작업은 **관리자 그룹**에 속한 사용자만 수행할 수 있어야 합니다."

### 문제 3: 금액 제한
> "일반 직원은 **$1,000 이하**의 환불만 처리할 수 있습니다.
> 그 이상은 매니저 승인이 필요합니다."

---

## ✅ 해결책 미리보기

이 튜토리얼을 완료하면 다음과 같은 결과를 얻을 수 있습니다:

| 문제 | Cedar 정책 | 테스트 결과 |
|------|-----------|------------|
| Finance만 환불 | `principal.getTag("department") == "finance"` | finance ✅ / engineering ❌ |
| Admin만 승인 | `principal.getTag("groups") like "*admins*"` | admins ✅ / developers ❌ |
| $1,000 제한 | `context.input.amount <= 1000` | $500 ✅ / $1,500 ❌ |

**실제 테스트 화면:**
```
✓ 통과: Finance department should be allowed
   예상: ALLOWED
   실제: ALLOWED

✓ 통과: Engineering department should be denied
   예상: DENIED
   실제: DENIED
```

---

## 📋 이 튜토리얼의 범위

### ✅ 다루는 내용: Gateway → Tool 보안

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Gateway → Tool 보안 (이 튜토리얼)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐      ┌──────────────┐      ┌─────────────────────┐   │
│  │ Cognito  │ JWT  │   Gateway    │      │  Tool (타겟)         │   │
│  │ (인증)   │─────>│ + Policy     │─────>│  - Lambda           │   │
│  │          │      │   Engine     │      │  - MCP Server       │   │
│  └──────────┘      └──────────────┘      └─────────────────────┘   │
│       ▲                  ▲                        ▲                 │
│       │                  │                        │                 │
│   JWT 발급          Cedar 정책              도구 실행              │
│   (인증)           (세분화된 인가)          (허용된 경우)           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

| 단계 | 다루는 내용 |
|------|-------------|
| **1. 인증 (Authentication)** | Cognito → JWT 토큰 발급, 커스텀 클레임 추가 |
| **2. 인가 (Authorization)** | Cedar 정책으로 도구 호출 허용/거부 결정 |
| **3. 도구 실행** | 허용된 경우 Lambda 또는 MCP 서버 호출 |

### ❌ 다루지 않는 내용

| 주제 | 설명 | 참고 자료 |
|------|------|----------|
| AI Agent Inbound Auth | 외부에서 AI 에이전트로의 인증 | [AgentCore Identity](./docs/agentcore-identity.md) |
| AI Agent Outbound Auth | AI 에이전트가 외부 API 호출 시 인증 | [AgentCore Identity](./docs/agentcore-identity.md) |

---

## 🔧 핵심 구현 (For Engineers)

이 튜토리얼에서 직접 구현하는 내용:

### 인증 (Authentication)

- **Cognito User Pool** 생성 및 OAuth 2.0 설정
- **JWT Authorizer**를 Gateway에 연결하여 Inbound Auth 구현
- **Cognito Lambda 트리거 (V3_0)** 설정으로 커스텀 클레임 추가 (department, groups)
- JWT 토큰 발급 및 **커스텀 클레임 디코딩** 확인

### 인가 (Authorization)

- **Policy Engine** 생성 및 Gateway에 연결
- **Cedar 정책** 작성: Principal 태그, Input 파라미터 기반 조건
- 정책 모드 설정: `LOG_ONLY` (테스트) → `ENFORCE` (운영)

### Gateway 타겟

- **Lambda 타겟**: Lambda 함수를 Gateway에 연결, 인라인 스키마 정의
- **MCP 서버 타겟**: AgentCore Runtime에 MCP 서버 배포 후 Gateway에 연결
- MCP 서버에 **Outbound Auth** 설정 (OAuth2 Credential Provider)
- Gateway 타겟 동기화로 MCP 도구 자동 탐색

### MCP 서버 호스팅

- **FastMCP**로 MCP 서버 구현 (`stateless_http=True` 필수)
- **bedrock-agentcore-starter-toolkit**으로 AgentCore Runtime에 배포
- Runtime Inbound Auth용 Cognito 설정

### 테스트

- 부서 기반 접근 제어 (Finance ✅ / Engineering ❌)
- 그룹 기반 접근 제어 (Admins ✅ / Developers ❌)
- 복합 조건 (Principal + Input 파라미터)

---

## 🏗️ 아키텍처

```
                                ┌───────────────────────┐
                                │  Policy Engine        │
                                │  (Cedar 정책)         │
                                └───────────┬───────────┘
                                            │ 연결됨
                                            ▼
┌─────────────────┐             ┌───────────────────────┐             ┌─────────────────────┐
│   Amazon        │  JWT 토큰   │  AgentCore Gateway    │             │  타겟               │
│   Cognito       │────────────>│  + JWT Authorizer     │────────────>│  (Lambda 또는 MCP)  │
│                 │             │  + 정책 평가          │             │                     │
└─────────────────┘             └───────────────────────┘             └─────────────────────┘
```

---

## 📚 튜토리얼 선택 가이드

| 튜토리얼 | 타겟 유형 | 특징 | 추천 대상 |
|----------|-----------|------|-----------|
| [01-Lambda-Target](./01-Lambda-Target/) | Lambda 함수 | 간단한 설정, 금액 비교 가능 | 처음 시작하는 분 |
| [02-MCP-Server-Target](./02-MCP-Server-Target/) | MCP 서버 | AgentCore Runtime 사용, 컨테이너 배포 | MCP 프로토콜 학습 |

### Lambda vs MCP 비교

| 항목 | Lambda 타겟 | MCP 서버 타겟 |
|------|-------------|---------------|
| 백엔드 | AWS Lambda 함수 | AgentCore Runtime 컨테이너 |
| 설정 복잡도 | 낮음 | 중간 |
| 프로토콜 | Lambda Invoke | MCP over HTTP |

> **추천:** Lambda 타겟부터 시작한 후 MCP 서버 타겟으로 진행하세요.

---

## 🚀 빠른 시작

### 1. 환경 설정
```bash
git clone https://github.com/gonsoomoon-ml/amazon-bedrock-agentcore-policy-tutorials.git
cd amazon-bedrock-agentcore-policy-tutorials/00_setup
chmod +x create_uv_virtual_env.sh
./create_uv_virtual_env.sh AgentCorePolicy
```

### 2. VS Code에서 노트북 실행
1. `.ipynb` 파일 열기
2. 우상단 **'Select Kernel'** 클릭
3. **`AgentCorePolicy`** 선택

### 3. 튜토리얼 시작
- **Lambda 타겟:** [01-Lambda-Target/01-Setup-Gateway-Lambda.ipynb](./01-Lambda-Target/01-Setup-Gateway-Lambda.ipynb)
- **MCP 서버:** [02-MCP-Server-Target/01-Setup-MCP-Runtime-Gateway.ipynb](./02-MCP-Server-Target/01-Setup-MCP-Runtime-Gateway.ipynb)

---

## 📂 레포지토리 구조

```
amazon-bedrock-agentcore-policy-tutorials/
├── README.md                    # 이 파일
├── 00_setup/                    # 환경 설정
├── 01-Lambda-Target/            # Lambda 타겟 튜토리얼
│   ├── 01-Setup-Gateway-Lambda.ipynb
│   ├── 02-Policy-Enforcement.ipynb
│   └── 03-Cleanup-Lambda-Target.ipynb
├── 02-MCP-Server-Target/        # MCP 서버 타겟 튜토리얼
│   ├── 01-Setup-MCP-Runtime-Gateway.ipynb
│   └── 02-Policy-Enforcement.ipynb
├── common/                      # 공유 유틸리티
└── docs/                        # 문서
```

---

## 📖 문서

| 문서 | 설명 |
|------|------|
| [Cedar Policy](./docs/cedar-policy.md) | Cedar 정책 언어 문법 및 예제 |
| [Amazon Cognito](./docs/cognito.md) | Cognito User Pool, OAuth2, 커스텀 클레임 |
| [JWT Authorizer](./docs/jwt-authorizer.md) | JWT 검증 및 Gateway 연동 |
| [AgentCore Identity](./docs/agentcore-identity.md) | AI 에이전트 인증 (이 튜토리얼 범위 외) |

---

## 🧹 정리

튜토리얼 완료 후 리소스를 정리하려면:
- **Lambda 타겟:** [03-Cleanup-Lambda-Target.ipynb](./01-Lambda-Target/03-Cleanup-Lambda-Target.ipynb) 실행

---

## 📚 관련 자료

- [amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main)
- [agentcore-policy-sample](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/08-AgentCore-policy)
- [AWS: Fine-grained access control with AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/apply-fine-grained-access-control-with-bedrock-agentcore-gateway-interceptors/)
- [Cedar 공식 사이트](https://www.cedarpolicy.com/)
- [Amazon Verified Permissions](https://aws.amazon.com/verified-permissions/)


---

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
