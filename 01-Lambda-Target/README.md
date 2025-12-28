# Lambda 타겟을 사용한 AgentCore Policy

## 왜 Lambda 타겟인가?

Lambda 타겟은 AgentCore Policy를 시작하기에 **가장 간단한 방법**입니다:

| 장점 | 설명 |
|------|------|
| 빠른 설정 | MCP 서버 배포 없이 바로 시작 |
| 숫자 비교 지원 | `amount <= 1000` 같은 정수 비교 가능 |
| IAM 기반 인증 | 별도 Outbound Auth 설정 불필요 |

> **권장**: 처음 시작하는 분은 이 튜토리얼부터 진행하세요.

---

## 학습 결과

이 튜토리얼을 완료하면:

```
✓ 통과: Finance department should be allowed
   예상: ALLOWED, 실제: ALLOWED

✓ 통과: Engineering department should be denied
   예상: DENIED, 실제: DENIED

✓ 통과: Amount under $1000 should be allowed
   예상: ALLOWED, 실제: ALLOWED
```

---

## 아키텍처

```
                                ┌───────────────────────┐
                                │  Policy Engine        │
                                │  (Cedar 정책)         │
                                │                       │
                                │  평가 항목:            │
                                │  - principal tags     │
                                │  - context.input      │
                                └───────────┬───────────┘
                                            │ 연결됨
                                            ▼
┌─────────────────┐             ┌───────────────────────┐             ┌─────────────┐
│   Amazon        │  JWT 토큰   │  AgentCore Gateway    │             │   Lambda    │
│   Cognito       │────────────>│  + JWT Authorizer     │────────────>│   함수      │
│   + Lambda      │  + 클레임   │  + Policy Engine      │  허용 시    │   (도구)    │
└─────────────────┘             └───────────────────────┘             └─────────────┘
```

---

## 테스트 시나리오

| 시나리오 | Cedar 정책 | 테스트 |
|----------|-----------|--------|
| 부서 기반 | `principal.getTag("department_name") == "finance"` | finance ✅ / engineering ❌ |
| 그룹 기반 | `principal.getTag("groups") like "*admins*"` | admins ✅ / developers ❌ |
| 금액 제한 | `context.input.amount <= 1000` | $500 ✅ / $1500 ❌ |
| 복합 조건 | 부서 + 금액 | finance+$500 ✅ / finance+$1500 ❌ |

---

## 폴더 구조

```
01-Lambda-Target/
├── README.md                      # 이 파일
├── 01-Setup-Gateway-Lambda.ipynb  # Step 1: Gateway, Cognito, Lambda 설정
├── 02-Policy-Enforcement.ipynb    # Step 2: Cedar 정책 테스트
├── 03-Cleanup-Lambda-Target.ipynb # Step 3: 리소스 정리
├── setup-gateway.py               # Gateway 설정 스크립트
├── gateway_config.json            # 설정 저장 (자동 생성)
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
1. `01-Setup-Gateway-Lambda.ipynb` 열기
2. 우상단 **Select Kernel** → `AgentCorePolicy` 선택
3. 셀 순서대로 실행
4. 완료 후 `02-Policy-Enforcement.ipynb` 실행

### 3. 리소스 정리

테스트 완료 후 `03-Cleanup-Lambda-Target.ipynb` 실행

---

## Cedar 정책 핵심 패턴

```cedar
// 부서 기반 접근 제어
permit(principal, action, resource)
when {
    principal.hasTag("department_name") &&
    principal.getTag("department_name") == "finance"
};

// 금액 제한 (Lambda 타겟에서만 작동)
permit(principal, action, resource)
when {
    context.input.amount <= 1000
};
```

---

## 사전 요구사항

- AWS 계정 및 적절한 IAM 권한
- Python 3.10+
- Amazon Cognito **Essentials** 또는 **Plus** 티어 (V3_0 Lambda 트리거 필요)

---

## 관련 자료

- [MCP 서버 타겟 튜토리얼](../02-MCP-Server-Target/) - MCP 프로토콜 학습
- [Cedar Policy 문법](../docs/cedar-policy.md)
- [Amazon Cognito 가이드](../docs/cognito.md)
