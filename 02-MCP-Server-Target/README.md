# MCP 서버 타겟을 사용한 AgentCore Policy

## 개요

이 튜토리얼은 Lambda 타겟 대신 **MCP 서버 타겟**과 함께 **Amazon Bedrock AgentCore Policy**를 사용하는 방법을 설명합니다.

### 아키텍처

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   에이전트   │────>│  AgentCore Gateway  │────>│  MCP 서버       │
│  (클라이언트) │ JWT │  + Cedar Policy     │ MCP │  (FastMCP)      │
└─────────────┘     └─────────────────────┘     └─────────────────┘
```

### Lambda 타겟 vs MCP 서버 타겟

| 항목 | Lambda 타겟 | MCP 서버 타겟 |
|------|-------------|---------------|
| 백엔드 | AWS Lambda 함수 | MCP 서버 (HTTP) |
| 프로토콜 | Lambda Invoke | MCP over HTTP |
| 도구 탐색 | 인라인 스키마 | SynchronizeGatewayTargets API |
| 호스팅 | AWS 관리형 | 자체 호스팅 / AgentCore Runtime |

## 사전 요구사항

- 적절한 IAM 권한이 있는 AWS 계정
- OAuth Authorizer가 설정된 AgentCore Gateway
- Python 3.10+
- bedrock-agentcore-starter-toolkit (Runtime 배포용)

## 폴더 구조

```
02-MCP-Server-Target/
├── README.md                      # 이 파일
├── 01-Setup-MCP-Runtime-Gateway.ipynb  # Gateway 및 MCP Runtime 설정
├── 02-Policy-Enforcement.ipynb    # 정책 적용 테스트
├── mcp_server.py                  # FastMCP 서버 (환불 도구 포함)
├── deploy_mcp_runtime.py          # AgentCore Runtime 배포 스크립트
├── Dockerfile                     # 컨테이너 설정
├── requirements_runtime.txt       # MCP 서버 의존성
└── img/                           # 스크린샷
```

## 빠른 시작

### 옵션 A: AgentCore Runtime에 배포 (권장)

MCP 서버를 AWS AgentCore Runtime에 배포하면 퍼블릭 URL이 자동으로 제공됩니다.

```bash
# 1단계: 환경 설정 (00_setup 폴더에서)
cd ../00_setup
./create_uv_virtual_env.sh AgentCorePolicy

# 2단계: Jupyter Lab 실행
uv run jupyter lab

# 3단계: 01-Setup-MCP-Runtime-Gateway.ipynb 노트북 실행
# 4단계: 02-Policy-Enforcement.ipynb 노트북 실행
```

### 옵션 B: ngrok을 사용한 로컬 서버

```bash
# 터미널 1: MCP 서버 실행
python mcp_server.py

# 터미널 2: ngrok으로 외부 노출 (Gateway 접근용)
ngrok http 8000

# ngrok URL을 Gateway 타겟 생성 시 사용
```

## MCP 서버 도구

포함된 MCP 서버 (`mcp_server.py`)가 제공하는 도구:

| 도구 | 설명 | 파라미터 |
|------|------|----------|
| `refund` | 환불 처리 | `amount`, `order_id`, `reason` |
| `get_order` | 주문 상세 조회 | `order_id` |
| `approve_claim` | 보험 청구 승인 | `claim_id`, `amount`, `risk_level` |

## 주요 API

### MCP 서버 타겟 생성

```python
target_config = {
    "mcp": {
        "mcpServer": {
            "url": "https://your-mcp-server.com/mcp"
        }
    }
}

response = gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="MyMCPTarget",
    targetConfiguration=target_config,
    credentialProviderConfigurations=[{"credentialProviderType": "NONE"}]
)
```

### Gateway 타겟 동기화

```python
gateway_client.synchronize_gateway_targets(
    gatewayIdentifier=gateway_id,
    targetId=target_id
)
```

## Cedar 정책 예제

### 금액 기반 제어

```cedar
permit(principal,
    action == AgentCore::Action::"RefundMCPServerTarget___refund",
    resource == AgentCore::Gateway::"arn:aws:...")
when {
    context.input.amount <= 1000
};
```

### 위험 등급 기반 제어

```cedar
permit(principal,
    action == AgentCore::Action::"RefundMCPServerTarget___approve_claim",
    resource == AgentCore::Gateway::"arn:aws:...")
when {
    context.input.risk_level != "critical"
};
```

## 문제 해결

### Gateway가 MCP 서버에 연결할 수 없음

- MCP 서버에 퍼블릭 URL이 있는지 확인 (ngrok 사용 또는 EC2에 배포)
- 보안 그룹에서 8000 포트 인바운드 트래픽 허용 확인
- URL이 올바르게 URL 인코딩되었는지 확인

### 도구 동기화 실패

- MCP 서버가 실행 중이고 접근 가능한지 확인
- MCP 프로토콜 버전이 지원되는지 확인 (2025-06-18 또는 2025-03-26)
- `GetGatewayTarget` API로 동기화 상태 확인

### 정책이 적용되지 않음

- Policy Engine이 ENFORCE 모드로 Gateway에 연결되었는지 확인
- 정책이 ACTIVE 상태인지 확인
- 도구 이름이 일치하는지 확인: `{TargetName}___{tool_name}`

## 참고 자료

- [AWS 문서: MCP 서버 타겟](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html)
- [MCP 프로토콜 사양](https://modelcontextprotocol.io/)
- [FastMCP 문서](https://github.com/modelcontextprotocol/servers)
- [Cedar Policy 언어](https://www.cedarpolicy.com/)
