# MCP 서버 타겟을 사용한 AgentCore Policy

## 왜 MCP 서버 타겟인가?

MCP(Model Context Protocol)는 AI 에이전트가 도구를 호출하는 **업계 표준 프로토콜**입니다:

| 장점 | 설명 |
|------|------|
| 표준 프로토콜 | MCP over HTTP로 다양한 AI 프레임워크와 호환 |
| AgentCore Runtime | AWS 관리형 컨테이너에서 MCP 서버 호스팅 |
| 도구 자동 탐색 | Gateway가 MCP 서버의 도구를 자동으로 동기화 |

> **참고**: Lambda 타겟 튜토리얼을 먼저 완료한 후 진행하세요.

---

## Lambda 타겟과의 차이

| 항목 | Lambda 타겟 | MCP 서버 타겟 |
|------|-------------|---------------|
| 백엔드 | AWS Lambda 함수 | AgentCore Runtime 컨테이너 |
| 프로토콜 | Lambda Invoke | MCP over HTTP |
| 인증 | IAM Role (자동) | OAuth2 Credential Provider |
| Cognito 개수 | 1개 (Gateway용) | 2개 (Gateway + Runtime) |
| 숫자 비교 | ✅ `amount <= 1000` | ⚠️ float 타입으로 제한적 |

---

## 학습 결과

이 튜토리얼을 완료하면:

```
✓ 통과: Finance department should be allowed
   예상: ALLOWED, 실제: ALLOWED

✓ 통과: Engineering department should be denied
   예상: DENIED, 실제: DENIED

✓ 통과: Low risk level should be allowed
   예상: ALLOWED, 실제: ALLOWED
```

---

## 아키텍처

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  클라이언트  │────>│  AgentCore Gateway  │────>│  AgentCore      │
│             │ JWT │  + JWT Authorizer   │ MCP │  Runtime        │
│             │     │  + Policy Engine    │     │  (MCP 서버)     │
└─────────────┘     └─────────────────────┘     └─────────────────┘
                              │                          │
                    ┌─────────┴─────────┐      ┌─────────┴─────────┐
                    │  Gateway Cognito  │      │  Runtime Cognito  │
                    │  (Inbound Auth)   │      │  (Outbound Auth)  │
                    └───────────────────┘      └───────────────────┘
```

**두 개의 Cognito가 필요한 이유:**
- **Gateway Cognito**: 클라이언트 → Gateway 인증 (JWT Authorizer)
- **Runtime Cognito**: Gateway → MCP Runtime 인증 (OAuth2 Credential Provider)

---

## 테스트 시나리오

| 시나리오 | Cedar 정책 | 테스트 |
|----------|-----------|--------|
| 부서 기반 | `principal.getTag("department_name") == "finance"` | finance ✅ / engineering ❌ |
| 그룹 기반 | `principal.getTag("groups") like "*admins*"` | admins ✅ / developers ❌ |
| 위험 등급 | `context.input.risk_level like "*low*"` | low ✅ / critical ❌ |

> **참고**: MCP 타겟에서는 `amount <= 1000` 같은 숫자 비교가 float 타입으로 인해 제한적입니다. 문자열 비교(`like`)를 권장합니다.

---

## 폴더 구조

```
02-MCP-Server-Target/
├── README.md                      # 이 파일
├── 01-Setup-MCP-Runtime-Gateway.ipynb  # Step 1: Runtime, Gateway 설정
├── 02-Policy-Enforcement.ipynb    # Step 2: Cedar 정책 테스트
├── 03-Cleanup-MCP-Server-Target.ipynb  # Step 3: 리소스 정리
├── mcp_server.py                  # FastMCP 서버 코드
├── setup_cognito_and_deploy_mcp_server_runtime.py  # 설정 스크립트
├── Dockerfile                     # 컨테이너 설정
├── requirements_runtime.txt       # MCP 서버 의존성
├── .bedrock_agentcore.yaml        # Runtime 배포 설정
└── img/                           # 스크린샷
```

---

## 시작하기

### 1. 환경 설정

```bash
cd ../00_setup
chmod +x create_uv_virtual_env.sh
./create_uv_virtual_env.sh AgentCorePolicy
```

### 2. 노트북 실행

VS Code에서:
1. `01-Setup-MCP-Runtime-Gateway.ipynb` 열기
2. 우상단 **Select Kernel** → `AgentCorePolicy` 선택
3. 셀 순서대로 실행 (Runtime 배포에 5-10분 소요)
4. 완료 후 `02-Policy-Enforcement.ipynb` 실행

### 3. 리소스 정리

튜토리얼 완료 후 AWS 리소스를 삭제하려면:
1. `03-Cleanup-MCP-Server-Target.ipynb` 실행

> **주의**: 이 노트북은 Gateway와 Gateway Cognito도 삭제합니다. Lambda 타겟 튜토리얼과 공유되는 리소스이므로, Lambda 타겟 튜토리얼도 재설정이 필요합니다.

---

## MCP 서버 도구

`mcp_server.py`에서 제공하는 도구:

| 도구 | 설명 | 파라미터 |
|------|------|----------|
| `refund` | 환불 처리 | `amount`, `order_id`, `reason` |
| `get_order` | 주문 조회 | `order_id` |
| `approve_claim` | 보험 청구 승인 | `claim_id`, `amount`, `risk_level` |

---

## Cedar 정책 핵심 패턴

```cedar
// 부서 기반 접근 제어
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};

// 위험 등급 기반 제어 (문자열 비교)
permit(principal, action, resource)
when {
    context.input.risk_level like "*low*"
};
```

---

## 주요 API

### MCP 서버 타겟 생성

```python
target_config = {
    "mcp": {
        "mcpServer": {
            "url": "https://your-runtime-url/mcp"
        }
    }
}

response = gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="RefundMCPServerTarget",
    targetConfiguration=target_config,
    credentialProviderConfigurations=[{
        "credentialProviderType": "OAUTH",
        "credentialProvider": {
            "oauthCredentialProvider": {
                "providerArn": credential_provider_arn,
                "scopes": ["mcp-server/invoke"]
            }
        }
    }]
)
```

### Gateway 타겟 동기화

```python
# MCP 서버의 도구를 Gateway에 동기화
gateway_client.synchronize_gateway_targets(
    gatewayIdentifier=gateway_id,
    targetId=target_id
)
```

---

## 사전 요구사항

- AWS 계정 및 적절한 IAM 권한
- Python 3.10+
- Amazon Cognito **Essentials** 또는 **Plus** 티어
- bedrock-agentcore-starter-toolkit (Runtime 배포용)

---

## 문제 해결

| 문제 | 해결 방법 |
|------|----------|
| Gateway가 MCP 서버에 연결 실패 | Runtime URL 확인, 보안 그룹 설정 |
| 도구 동기화 실패 | MCP 서버 실행 중인지 확인, `GetGatewayTarget`으로 상태 확인 |
| 정책 미적용 | Policy Engine이 ENFORCE 모드인지, 정책이 ACTIVE인지 확인 |

---

## 관련 자료

- [Lambda 타겟 튜토리얼](../01-Lambda-Target/) - 먼저 시작하기
- [AgentCore Identity 가이드](../docs/agentcore-identity.md) - Outbound Auth 상세
- [Cedar Policy 문법](../docs/cedar-policy.md)
