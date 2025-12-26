# Amazon Bedrock AgentCore Policy - 세분화된 접근 제어 튜토리얼

## 개요

이 튜토리얼은 **Amazon Bedrock AgentCore Policy**를 사용하여 AI 에이전트의 도구 호출에 대한 세분화된 접근 제어를 구현하는 방법을 설명합니다.

### 아키텍처

```
                                ┌───────────────────────┐
                                │  Policy Engine        │
                                │  (Cedar 정책)         │
                                │                       │
                                │  평가 항목:            │
                                │  - principal tags     │
                                │  - context.input      │
                                │  - resource           │
                                └───────────┬───────────┘
                                            │ 연결됨
                                            ▼
┌─────────────────┐             ┌───────────────────────┐             ┌─────────────┐
│   Amazon        │  JWT 토큰   │  AgentCore Gateway    │             │   Lambda    │
│   Cognito       │────────────>│                       │────────────>│   Target    │
│   + Lambda      │  + 클레임   │                       │  허용 시    │   (도구)    │
└─────────────────┘             └───────────────────────┘             └─────────────┘
```

### 튜토리얼 정보

| 항목 | 내용 |
|------|------|
| AgentCore 컴포넌트 | Gateway, Identity, Policy |
| 난이도 | 중급 |
| 사용 SDK | boto3, requests |

## 폴더 구조

```
04-Fine-Grained-Access-Control-kr/
├── README.md                 # 이 파일
├── tutorial.ipynb            # 메인 튜토리얼 노트북
├── setup-gateway.py          # Gateway/Cognito 설정 스크립트
├── gateway_config.json       # Gateway/Cognito 설정 (자동 생성)
│
├── scripts/                  # 유틸리티 모듈
│   ├── __init__.py
│   ├── auth_utils.py         # 토큰 발급/디코딩
│   ├── gateway_utils.py      # Gateway 설정/관리
│   ├── policy_utils.py       # Policy Engine/Cedar 정책
│   └── cognito_utils.py      # Cognito Lambda Trigger
│
└── docs/                     # 상세 문서
    ├── README.md             # 문서 개요
    ├── cognito.md            # Amazon Cognito 가이드
    ├── cedar-policy.md       # Cedar 정책 문법
    ├── jwt-authorizer.md     # JWT Authorizer 설명
    └── troubleshooting.md    # 문제 해결 가이드
```

## 사전 요구사항

- AWS 계정 및 적절한 IAM 권한
- Amazon Bedrock AgentCore Gateway (OAuth Authorizer 설정됨)
- Amazon Cognito User Pool (M2M 클라이언트, **Essentials** 또는 **Plus** 티어)
- Python 3.10+

## 시작하기

### 1. 환경 설정

#### 옵션 A: UV 가상환경 사용 (권장)

```bash
# 00_setup 폴더로 이동
cd ../00_setup

# 실행 권한 부여
chmod +x create_uv_virtual_env.sh

# 가상환경 생성 (커널 이름 지정)
./create_uv_virtual_env.sh AgentCorePolicy

# Jupyter Lab 실행
uv run jupyter lab
```

Jupyter Lab에서 노트북을 열고 `AgentCorePolicy` 커널을 선택하세요.

#### 옵션 B: pip 직접 설치

```bash
pip install boto3 requests bedrock-agentcore-starter-toolkit jupyter
```

### 2. Gateway 설정

Gateway와 Cognito가 아직 설정되지 않은 경우:

```bash
python setup-gateway.py --region us-east-1
```

### 3. 튜토리얼 실행

```bash
# UV 환경에서 실행
cd ../00_setup
uv run jupyter lab

# 또는 직접 실행
jupyter lab ../04-Fine-Grained-Access-Control-kr/tutorial.ipynb
```

### 4. 문서 참고

상세한 개념 설명은 `docs/` 폴더를 참고하세요:

- [Amazon Cognito](docs/cognito.md)
- [Cedar Policy 문법](docs/cedar-policy.md)
- [JWT Authorizer](docs/jwt-authorizer.md)
- [문제 해결](docs/troubleshooting.md)

## 학습 내용

### 테스트 시나리오

| 시나리오 | 설명 |
|----------|------|
| 부서 기반 | finance 부서만 접근 허용 |
| 그룹 기반 | admins 그룹만 접근 허용 (패턴 매칭) |
| 복합 조건 | 부서 + 금액 제한 조합 |

### Cedar 정책 핵심 패턴

| 패턴 | Cedar 문법 |
|------|------------|
| 클레임 존재 확인 | `principal.hasTag("claim_name")` |
| 정확한 일치 | `principal.getTag("claim_name") == "value"` |
| 패턴 매칭 | `principal.getTag("claim_name") like "*value*"` |
| 입력값 검증 | `context.input.field <= value` |

## 모범 사례

1. **hasTag() 먼저 확인**: `getTag()` 전에 항상 `hasTag()`로 존재 확인
2. **패턴 매칭 주의**: `like "*value*"`는 의도치 않은 매칭 가능
3. **ALLOW/DENY 모두 테스트**: 양쪽 시나리오 검증
4. **V3_0 Lambda 트리거**: M2M client credentials 플로우에 필수

## 관련 자료

- [원본 영문 튜토리얼](../03-Fine-Grained-Access-Control/)
- [Cedar 공식 사이트](https://www.cedarpolicy.com/)
- [Amazon Verified Permissions](https://aws.amazon.com/verified-permissions/)
- [Amazon Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/latest/developerguide/)
