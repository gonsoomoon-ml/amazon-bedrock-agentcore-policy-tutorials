# Amazon Bedrock AgentCore Policy 튜토리얼

이 레포지토리는 **Amazon Bedrock AgentCore Policy**와 **Cedar 정책**을 사용하여 **세분화된 접근 제어**를 구현하는 튜토리얼을 포함합니다.

## 개요

Amazon Bedrock AgentCore Policy를 사용하면 다음을 기반으로 AI 에이전트가 수행할 수 있는 작업을 제어할 수 있습니다:
- **주체 속성** (ID 토큰의 JWT 클레임)
- **입력 파라미터** (도구 인자)
- **리소스 컨텍스트** (Gateway, 타겟)

## 튜토리얼

| 튜토리얼 | 설명 | 타겟 유형 |
|----------|------|-----------|
| [01-Lambda-Target](./01-Lambda-Target/) | AWS Lambda 백엔드를 사용한 정책 적용 | Lambda 함수 |
| [02-MCP-Server-Target](./02-MCP-Server-Target/) | AgentCore Runtime의 MCP 서버를 사용한 정책 적용 | MCP 서버 |

## 아키텍처

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

## 시작하기

### 사전 요구사항

- 적절한 권한이 있는 AWS 계정
- Python 3.10+
- [UV](https://github.com/astral-sh/uv) 패키지 매니저 (권장)

### 설정

1. **레포지토리 클론**
   ```bash
   git clone <repository-url>
   cd amazon-bedrock-agentcore-policy-tutorials
   ```

2. **가상환경 생성**
   ```bash
   cd 00_setup
   chmod +x create_uv_virtual_env.sh
   ./create_uv_virtual_env.sh AgentCorePolicy
   ```

3. **Jupyter에서 커널 선택**
   - Jupyter Lab/Notebook 열기
   - `AgentCorePolicy` 커널 선택

4. **튜토리얼 선택**
   - Lambda 타겟: [01-Lambda-Target](./01-Lambda-Target/)으로 시작
   - MCP 서버 타겟: [02-MCP-Server-Target](./02-MCP-Server-Target/)으로 시작

## 레포지토리 구조

```
amazon-bedrock-agentcore-policy-tutorials/
├── README.md                    # 이 파일
├── 00_setup/                    # 공유 환경 설정
│   ├── pyproject.toml           # Python 의존성
│   ├── uv.lock                  # Lock 파일
│   └── create_uv_virtual_env.sh # 설정 스크립트
├── docs/                        # 공유 문서
│   ├── cedar-policy.md          # Cedar 정책 문법 가이드
│   ├── cognito.md               # Amazon Cognito 개념
│   ├── jwt-authorizer.md        # JWT Authorizer 가이드
│   └── troubleshooting.md       # 일반적인 문제 및 해결책
├── common/                      # 공유 유틸리티 스크립트
│   ├── auth_utils.py            # 토큰 및 인증 유틸리티
│   ├── cognito_utils.py         # Cognito Lambda 트리거 유틸리티
│   ├── gateway_utils.py         # Gateway 관리 유틸리티
│   └── policy_utils.py          # Policy Engine 유틸리티
├── 01-Lambda-Target/            # Lambda 타겟 튜토리얼
│   ├── README.md
│   ├── img/                     # 스크린샷
│   ├── 01-Setup-Gateway-Lambda.ipynb
│   ├── 02-Policy-Enforcement.ipynb
│   └── setup-gateway.py
└── 02-MCP-Server-Target/        # MCP 서버 타겟 튜토리얼
    ├── README.md
    ├── img/                     # 스크린샷
    ├── mcp_server.py            # MCP 서버 구현
    ├── Dockerfile               # 컨테이너 설정
    ├── deploy_mcp_runtime.py    # 배포 스크립트
    ├── 01-Setup-MCP-Runtime-Gateway.ipynb
    └── 02-Policy-Enforcement.ipynb
```

## Cedar 정책 패턴

### 문자열 동등 비교
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level == "low"
};
```

### 패턴 매칭 (like)
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level like "*low*"
};
```

### OR 조건
```cedar
permit(principal, action, resource)
when {
    context.input.risk_level == "low" ||
    context.input.risk_level == "medium"
};
```

### 부정
```cedar
permit(principal, action, resource)
when {
    !(context.input.risk_level == "critical")
};
```

### JWT 클레임 (Principal 태그)
```cedar
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};
```

## 문서

| 문서 | 설명 |
|------|------|
| [Cedar Policy](./docs/cedar-policy.md) | Cedar 정책 언어 문법 및 예제 |
| [Amazon Cognito](./docs/cognito.md) | Cognito User Pool, OAuth2, 커스텀 클레임 |
| [JWT Authorizer](./docs/jwt-authorizer.md) | Gateway JWT 검증 및 principal 태그 |
| [문제 해결](./docs/troubleshooting.md) | 일반적인 문제 및 해결책 |

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다 - 자세한 내용은 LICENSE 파일을 참조하세요.

## 기여

기여를 환영합니다! Pull Request를 제출하기 전에 기여 가이드라인을 읽어주세요.
