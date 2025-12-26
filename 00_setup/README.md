# Amazon Bedrock AgentCore Policy - 환경 설정

이 디렉토리는 AgentCore Policy 튜토리얼을 위한 UV 기반 Python 가상환경을 설정합니다.

## 빠른 시작

```bash
# 1. 실행 권한 부여
chmod +x create_uv_virtual_env.sh

# 2. 가상환경 생성 (커널 이름 지정)
./create_uv_virtual_env.sh AgentCorePolicy

# 3. Jupyter Lab 실행
uv run jupyter lab
```

## 포함된 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| boto3 | >=1.42.0 | AWS SDK |
| botocore | >=1.34.0 | AWS SDK Core |
| bedrock-agentcore-starter-toolkit | >=0.2.4 | AgentCore 도구 |
| requests | >=2.31.0 | HTTP 요청 (OAuth 토큰) |
| jupyter / jupyterlab | >=1.0.0 / >=4.0.0 | 노트북 환경 |
| ipykernel | >=6.25.0 | Jupyter 커널 |

## 사용법

### 가상환경 활성화

```bash
source .venv/bin/activate
```

### Jupyter 커널 선택

스크립트 실행 후 Jupyter Lab에서:
1. 노트북 파일 열기
2. 우상단 커널 선택에서 `AgentCorePolicy` 선택

### 수동 설치 (UV 없이)

```bash
pip install boto3 requests bedrock-agentcore-starter-toolkit jupyter
```

## 튜토리얼 목록

| 폴더 | 내용 |
|------|------|
| 01-Getting-Started | AgentCore Policy 시작하기 |
| 02-Natural-Language-Policy-Authoring | 자연어로 Cedar 정책 생성 |
| 03-Fine-Grained-Access-Control | 세분화된 접근 제어 (영문) |
| 04-Fine-Grained-Access-Control-kr | 세분화된 접근 제어 (한글) |

## 주요 명령어

### 패키지 관리

```bash
# 새 패키지 추가
uv add package_name

# 패키지 제거
uv remove package_name

# 동기화 (lock 파일 기준)
uv sync
```

### 스크립트 실행

```bash
# UV를 통해 실행
uv run python your_script.py

# 가상환경 활성화 후 실행
source .venv/bin/activate
python your_script.py
```

## 문제 해결

### UV 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 가상환경 재생성

```bash
rm -rf .venv
uv venv --python 3.10
uv sync
```

### 패키지 설치 오류

```bash
uv cache clean
uv sync --force-reinstall
```

## 프로젝트 구조

```
00_setup/
├── README.md                    # 이 파일
├── create_uv_virtual_env.sh     # UV 가상환경 생성 스크립트
├── pyproject.toml               # Python 패키지 의존성
├── uv.lock                      # 의존성 잠금 파일
└── .venv/                       # 가상환경 (스크립트 실행 후 생성)
```

## 참고 링크

- [UV 공식 문서](https://docs.astral.sh/uv/)
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/)
- [Cedar Policy](https://www.cedarpolicy.com/)
