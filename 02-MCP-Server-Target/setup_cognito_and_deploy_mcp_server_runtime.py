"""
MCP 서버를 AgentCore Runtime에 배포하는 스크립트

이 스크립트는 RefundMCPServer를 Amazon Bedrock AgentCore Runtime에 배포합니다.
bedrock_agentcore_starter_toolkit을 사용하여 Docker 이미지 빌드, ECR 푸시,
Runtime 생성을 자동으로 수행합니다.

주요 기능:
    - Cognito User Pool 및 App Client 생성 (OAuth 인증용)
    - Resource Server 및 OAuth Scope 설정
    - MCP 서버 Docker 이미지 빌드 및 ECR 푸시
    - AgentCore Runtime 생성 및 배포

사용법:
    # 새로 배포
    python setup_cognito_and_deploy_mcp_server_runtime.py

    # 기존 Runtime 삭제 후 재배포
    python setup_cognito_and_deploy_mcp_server_runtime.py --delete

사전 요구사항:
    - bedrock_agentcore_starter_toolkit 설치
    - mcp_server.py 파일 (동일 디렉토리)
    - AWS 자격 증명 설정
    - Docker 실행 환경

생성되는 파일:
    - cognito_config.json: Cognito 설정 정보
    - runtime_config.json: Runtime 배포 정보
    - requirements_runtime.txt: MCP 서버 의존성

아키텍처:
    ┌─────────────────────┐
    │   이 스크립트        │
    │   (setup_cognito_   │
    │    and_deploy...)   │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐     ┌─────────────────────┐
    │  Cognito User Pool  │     │  AgentCore Runtime  │
    │  - OAuth 인증 설정    │     │  - MCP 서버 호스팅   │
    │  - Client Credentials │    │  - Public Endpoint  │
    └─────────────────────┘     └─────────────────────┘
"""

import sys
import os
import time
import json
import boto3
from pathlib import Path
from urllib.parse import quote


# ============================================================================
# 설정값 (Configuration)
# ============================================================================
# 이 값들을 수정하여 배포 환경을 변경할 수 있습니다.

RUNTIME_NAME = "refund_mcp_server"      # Runtime 이름 (고유해야 함)
ENTRYPOINT = "mcp_server.py"            # MCP 서버 진입점 파일
REGION = "us-east-1"                    # AWS 리전
COGNITO_POOL_NAME = "RefundMCPServerPool"  # Cognito User Pool 이름

# 스크립트 디렉토리 경로
SCRIPT_DIR = Path(__file__).parent
MCP_SERVER_FILE = SCRIPT_DIR / "mcp_server.py"


# ============================================================================
# 출력 헬퍼 함수 (Print Helpers)
# ============================================================================
# 콘솔 출력을 위한 유틸리티 함수들

def print_header(message: str):
    """섹션 헤더를 출력합니다."""
    print(f"\n{'=' * 60}")
    print(message)
    print('=' * 60)


def print_success(message: str):
    """성공 메시지를 출력합니다."""
    print(f"✓ {message}")


def print_error(message: str):
    """오류 메시지를 출력합니다."""
    print(f"✗ {message}")


def print_info(message: str):
    """정보 메시지를 출력합니다."""
    print(f"  {message}")


# ============================================================================
# Cognito 설정 함수 (Cognito Setup Functions)
# ============================================================================
# Runtime의 OAuth 인증을 위한 Cognito 리소스 생성

def setup_cognito_for_runtime() -> dict:
    """
    Runtime OAuth 인증을 위한 Cognito 리소스를 설정합니다.

    이 함수는 다음 리소스들을 생성하거나 재사용합니다:
    1. User Pool - OAuth 인증의 기반
    2. Domain - 토큰 엔드포인트 URL 제공
    3. Resource Server - OAuth Scope 정의
    4. App Client - Client Credentials 플로우용 클라이언트

    AgentCore Runtime은 이 Cognito를 사용하여 들어오는 요청을 인증합니다.
    Gateway가 Runtime에 접근할 때 이 Cognito에서 발급받은 토큰을 사용합니다.

    Returns:
        dict: Cognito 설정 정보
            - pool_id: User Pool ID
            - client_id: App Client ID
            - client_secret: App Client Secret
            - discovery_url: OIDC Discovery URL
            - token_endpoint: OAuth 토큰 엔드포인트
            - domain: Cognito 도메인
            - scope: OAuth Scope
            - region: AWS 리전
    """
    print_header("Runtime OAuth를 위한 Cognito 설정")

    cognito_client = boto3.client("cognito-idp", region_name=REGION)

    # -------------------------------------------------------------------------
    # 1단계: User Pool 생성 또는 재사용
    # -------------------------------------------------------------------------
    # User Pool은 사용자/클라이언트 인증의 기반입니다.
    # 이미 존재하면 재사용하고, 없으면 새로 생성합니다.

    pools = cognito_client.list_user_pools(MaxResults=60).get("UserPools", [])
    existing_pool = next((p for p in pools if p["Name"] == COGNITO_POOL_NAME), None)

    if existing_pool:
        pool_id = existing_pool["Id"]
        print_info(f"기존 User Pool 사용: {pool_id}")
    else:
        print_info("새 Cognito User Pool 생성 중...")
        response = cognito_client.create_user_pool(
            PoolName=COGNITO_POOL_NAME,
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": False,
                }
            },
            AutoVerifiedAttributes=["email"],
            UsernameAttributes=["email"],
            MfaConfiguration="OFF",
        )
        pool_id = response["UserPool"]["Id"]
        print_success(f"User Pool 생성됨: {pool_id}")

    # -------------------------------------------------------------------------
    # 2단계: Cognito Domain 설정
    # -------------------------------------------------------------------------
    # Domain은 OAuth 토큰 엔드포인트 URL을 제공합니다.
    # 형식: https://{domain}.auth.{region}.amazoncognito.com

    domain = f"refund-mcp-{pool_id.split('_')[1].lower()}"

    # describe_user_pool_domain은 도메인이 없어도 예외를 발생시키지 않고
    # 빈 DomainDescription을 반환합니다. 따라서 내용을 확인해야 합니다.
    domain_response = cognito_client.describe_user_pool_domain(Domain=domain)
    domain_exists = bool(domain_response.get("DomainDescription", {}).get("Domain"))

    if domain_exists:
        print_info(f"기존 도메인 사용: {domain}")
    else:
        try:
            cognito_client.create_user_pool_domain(
                Domain=domain,
                UserPoolId=pool_id
            )
            print_success(f"도메인 생성됨: {domain}")
            # 도메인 DNS 전파 대기 (최대 30초)
            print_info("도메인 DNS 전파 대기 중...")
            import time
            time.sleep(10)
        except Exception as e:
            if "already exists" in str(e).lower():
                print_info(f"도메인 이미 존재: {domain}")
            else:
                raise

    # -------------------------------------------------------------------------
    # 3단계: Resource Server 생성
    # -------------------------------------------------------------------------
    # Resource Server는 OAuth Scope를 정의합니다.
    # 여기서는 'refund-mcp/invoke' scope를 정의하여
    # MCP 도구 호출 권한을 제어합니다.

    resource_server_id = "refund-mcp"
    try:
        cognito_client.create_resource_server(
            UserPoolId=pool_id,
            Identifier=resource_server_id,
            Name="Refund MCP Server",
            Scopes=[
                {
                    "ScopeName": "invoke",
                    "ScopeDescription": "MCP 도구 호출 권한"
                }
            ]
        )
        print_success("Resource Server 생성됨")
    except cognito_client.exceptions.ResourceExistsException:
        print_info("Resource Server 이미 존재")

    # -------------------------------------------------------------------------
    # 4단계: App Client 생성
    # -------------------------------------------------------------------------
    # App Client는 OAuth Client Credentials 플로우에 사용됩니다.
    # Gateway의 Resource Credential Provider가 이 클라이언트를 사용하여
    # Runtime 접근용 토큰을 발급받습니다.

    clients = cognito_client.list_user_pool_clients(
        UserPoolId=pool_id, MaxResults=60
    ).get("UserPoolClients", [])

    client_name = "refund-mcp-client"
    existing_client = next((c for c in clients if c["ClientName"] == client_name), None)

    if existing_client:
        client_id = existing_client["ClientId"]
        # 기존 클라이언트의 Secret 조회
        client_details = cognito_client.describe_user_pool_client(
            UserPoolId=pool_id, ClientId=client_id
        )["UserPoolClient"]
        client_secret = client_details.get("ClientSecret")
        print_info(f"기존 App Client 사용: {client_id}")
    else:
        # Client Credentials 플로우를 지원하는 새 클라이언트 생성
        response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=client_name,
            GenerateSecret=True,  # M2M 플로우에 필요
            AllowedOAuthFlows=["client_credentials"],
            AllowedOAuthScopes=[f"{resource_server_id}/invoke"],
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=["COGNITO"],
        )
        client_id = response["UserPoolClient"]["ClientId"]
        client_secret = response["UserPoolClient"]["ClientSecret"]
        print_success(f"App Client 생성됨: {client_id}")

    # -------------------------------------------------------------------------
    # 5단계: 설정 정보 구성 및 저장
    # -------------------------------------------------------------------------
    # OIDC Discovery URL과 토큰 엔드포인트 URL을 구성합니다.
    # 이 정보들은 Runtime 배포 시 JWT Authorizer 설정에 사용됩니다.

    discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
    token_endpoint = f"https://{domain}.auth.{REGION}.amazoncognito.com/oauth2/token"

    cognito_config = {
        "pool_id": pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "discovery_url": discovery_url,
        "token_endpoint": token_endpoint,
        "domain": domain,
        "scope": f"{resource_server_id}/invoke",
        "region": REGION,
    }

    # 설정 파일로 저장
    config_file = SCRIPT_DIR / "cognito_config.json"
    config_file.write_text(json.dumps(cognito_config, indent=2))
    print_success(f"Cognito 설정 저장됨: {config_file}")

    return cognito_config


def _get_bearer_token_internal(cognito_config: dict) -> str:
    """
    Client Credentials 플로우로 Bearer 토큰을 발급받습니다. (내부용)

    이 함수는 테스트 목적으로 Cognito에서 Access Token을 발급받습니다.
    실제 운영 환경에서는 AgentCore Identity의 Resource Credential Provider가
    이 과정을 자동으로 처리합니다.

    Note:
        common.auth_utils.get_bearer_token()과 충돌을 피하기 위해 _internal 접미사 사용

    Args:
        cognito_config: setup_cognito_for_runtime()에서 반환된 설정

    Returns:
        str: Access Token (Bearer 토큰으로 사용)
    """
    import requests

    data = {
        "grant_type": "client_credentials",
        "client_id": cognito_config["client_id"],
        "client_secret": cognito_config["client_secret"],
        "scope": cognito_config["scope"],
    }

    response = requests.post(
        cognito_config["token_endpoint"],
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
    )
    response.raise_for_status()
    return response.json()["access_token"]


# ============================================================================
# Runtime 배포 함수 (Runtime Deployment Functions)
# ============================================================================
# AgentCore Runtime 생성 및 관리

def get_agentcore_client():
    """
    bedrock-agentcore-control boto3 클라이언트를 반환합니다.

    이 클라이언트로 AgentCore의 모든 리소스를 관리할 수 있습니다:
    - Runtime (에이전트 실행 환경)
    - Gateway (API 게이트웨이)
    - Policy Engine (Cedar 정책 엔진)
    - Identity (자격 증명 관리)
    """
    return boto3.client("bedrock-agentcore-control", region_name=REGION)


def list_runtimes(client):
    """
    모든 AgentCore Runtime 목록을 조회합니다.

    Returns:
        list: Runtime 요약 정보 목록
    """
    response = client.list_agent_runtimes()
    return response.get("agentRuntimeSummaries", [])


def get_runtime_by_name(client, name: str):
    """
    이름으로 Runtime을 검색합니다.

    Args:
        client: boto3 AgentCore 클라이언트
        name: 검색할 Runtime 이름

    Returns:
        dict 또는 None: Runtime 정보 (없으면 None)
    """
    runtimes = list_runtimes(client)
    for runtime in runtimes:
        if runtime.get("agentRuntimeName") == name:
            return runtime
    return None


def get_runtime_details(client, runtime_id: str):
    """
    Runtime의 상세 정보를 조회합니다.

    Args:
        client: boto3 AgentCore 클라이언트
        runtime_id: Runtime ID

    Returns:
        dict: Runtime 상세 정보 (상태, 엔드포인트, ARN 등)
    """
    return client.get_agent_runtime(agentRuntimeId=runtime_id)


def delete_runtime(client, runtime_id: str):
    """
    AgentCore Runtime을 삭제합니다.

    삭제는 비동기로 진행되며, 이 함수는 삭제가 완료될 때까지 대기합니다.
    최대 3분간 대기하며, 10초 간격으로 상태를 확인합니다.

    Args:
        client: boto3 AgentCore 클라이언트
        runtime_id: 삭제할 Runtime ID

    Returns:
        bool: 삭제 성공 여부
    """
    print(f"Runtime 삭제 중: {runtime_id}")
    client.delete_agent_runtime(agentRuntimeId=runtime_id)

    # 삭제 완료 대기 (최대 3분)
    max_wait = 180
    start = time.time()
    while time.time() - start < max_wait:
        try:
            client.get_agent_runtime(agentRuntimeId=runtime_id)
            print("  삭제 대기 중...")
            time.sleep(10)
        except client.exceptions.ResourceNotFoundException:
            print_success("Runtime 삭제됨")
            return True
        except Exception as e:
            if "ResourceNotFoundException" in str(type(e).__name__):
                print_success("Runtime 삭제됨")
                return True
            time.sleep(10)

    print_error("삭제 타임아웃")
    return False


def create_requirements_file():
    """
    MCP 서버 의존성 파일(requirements_runtime.txt)을 생성합니다.

    이 파일은 Runtime 컨테이너 빌드 시 pip install에 사용됩니다.
    MCP 서버 실행에 필요한 최소 패키지만 포함합니다.

    Returns:
        Path: 생성된 requirements 파일 경로
    """
    requirements_file = SCRIPT_DIR / "requirements_runtime.txt"
    requirements = [
        "mcp>=1.0.0",        # Model Context Protocol 라이브러리
        "uvicorn>=0.30.0",   # ASGI 서버
        "starlette>=0.45.0", # ASGI 프레임워크
    ]
    requirements_file.write_text("\n".join(requirements))
    print_info(f"생성됨: {requirements_file}")
    return requirements_file


def deploy_with_starter_toolkit(cognito_config: dict):
    """
    bedrock_agentcore_starter_toolkit을 사용하여 MCP 서버를 배포합니다.

    이 함수는 다음 작업을 자동으로 수행합니다:
    1. Dockerfile 생성
    2. Docker 이미지 빌드
    3. ECR 레포지토리 생성 및 이미지 푸시
    4. IAM 실행 역할 생성
    5. AgentCore Runtime 생성

    배포된 Runtime은 PUBLIC 네트워크 모드로 실행되어
    AgentCore Gateway에서 접근할 수 있습니다.

    Args:
        cognito_config: Cognito 설정 정보 (JWT Authorizer 설정에 사용)

    Returns:
        dict 또는 None: 배포 결과
            - runtime_id: Runtime ID
            - runtime_arn: Runtime ARN
    """
    print_header("Starter Toolkit으로 배포")

    # Starter Toolkit 임포트 확인
    try:
        from bedrock_agentcore_starter_toolkit import Runtime
    except ImportError:
        print_error("bedrock_agentcore_starter_toolkit이 설치되지 않았습니다")
        print_info("설치: pip install bedrock-agentcore-starter-toolkit")
        return None

    # MCP 서버 파일 확인
    if not MCP_SERVER_FILE.exists():
        print_error(f"MCP 서버 파일 없음: {MCP_SERVER_FILE}")
        return None

    print_info(f"Runtime 이름: {RUNTIME_NAME}")
    print_info(f"진입점: {ENTRYPOINT}")
    print_info(f"리전: {REGION}")

    # 의존성 파일 생성
    requirements_file = create_requirements_file()

    # Runtime 객체 초기화
    runtime = Runtime()

    # -------------------------------------------------------------------------
    # JWT Authorizer 설정
    # -------------------------------------------------------------------------
    # Runtime으로 들어오는 요청을 인증하기 위한 설정입니다.
    # Gateway의 Resource Credential Provider가 발급한 토큰을
    # 이 설정으로 검증합니다.

    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config["client_id"]],
            "discoveryUrl": cognito_config["discovery_url"],
        }
    }

    print("\n[1/2] Runtime 설정 중...")

    # 상대 경로 처리를 위해 스크립트 디렉토리로 이동
    original_dir = os.getcwd()
    os.chdir(SCRIPT_DIR)

    try:
        # Runtime 설정
        config_response = runtime.configure(
            agent_name=RUNTIME_NAME,
            entrypoint=ENTRYPOINT,
            requirements_file=str(requirements_file.name),
            region=REGION,
            auto_create_ecr=True,              # ECR 레포지토리 자동 생성
            auto_create_execution_role=True,   # IAM 역할 자동 생성
            protocol="MCP",                    # MCP 프로토콜 (Gateway 호환용)
            authorizer_configuration=auth_config,  # OAuth 인증 설정
            vpc_enabled=False,                 # PUBLIC 모드 (Gateway 접근용)
            non_interactive=True               # 비대화형 모드
        )

        print_success("설정 완료")
        print_info(f"설정 파일: {config_response.config_path}")
        print_info(f"Dockerfile: {config_response.dockerfile_path}")

        # -------------------------------------------------------------------------
        # Runtime 배포
        # -------------------------------------------------------------------------
        # Docker 빌드 → ECR 푸시 → Runtime 생성
        # 이 과정은 5-10분 정도 소요됩니다.

        print("\n[2/2] Runtime 배포 중 (Docker 빌드 + ECR 푸시 + 생성)...")
        print_info("약 5-10분 소요됩니다...")

        launch_response = runtime.launch()

        print_success("Runtime 배포됨!")
        print_info(f"Runtime ARN: {launch_response.agent_arn}")
        print_info(f"Runtime ID: {launch_response.agent_id}")

        return {
            "runtime_id": launch_response.agent_id,
            "runtime_arn": launch_response.agent_arn
        }

    finally:
        os.chdir(original_dir)


def wait_for_runtime_ready(client, runtime_id: str, max_wait: int = 600):
    """
    Runtime이 READY 상태가 될 때까지 대기합니다.

    Runtime 생성 후 실제 사용 가능한 상태가 되기까지 시간이 걸립니다.
    이 함수는 10초 간격으로 상태를 확인하며,
    READY 상태가 되면 Runtime 정보를 반환합니다.

    Args:
        client: boto3 AgentCore 클라이언트
        runtime_id: Runtime ID
        max_wait: 최대 대기 시간 (초, 기본값 10분)

    Returns:
        dict 또는 None: READY 상태의 Runtime 정보 (실패 시 None)
    """
    print(f"\nRuntime READY 상태 대기 중...")
    start = time.time()
    attempt = 0

    while time.time() - start < max_wait:
        attempt += 1
        try:
            runtime = get_runtime_details(client, runtime_id)
            status = runtime.get("status")
            print(f"  [{attempt}] 상태: {status}")

            if status == "READY":
                return runtime
            elif status in ["FAILED", "CREATE_FAILED", "UPDATE_FAILED"]:
                reason = runtime.get("statusReason", "알 수 없음")
                print_error(f"Runtime 실패: {reason}")
                return None

        except Exception as e:
            print_error(f"상태 확인 오류: {e}")

        time.sleep(10)

    print_error("대기 시간 초과")
    return None


def save_config(runtime_id: str, runtime_arn: str, cognito_config: dict, endpoint: str = None):
    """
    Runtime 설정 정보를 파일로 저장합니다.

    저장된 정보는 다음 용도로 사용됩니다:
    - Gateway Target 생성 시 Runtime URL 참조
    - 노트북에서 Runtime 정보 조회
    - 테스트 스크립트에서 설정 로드

    Args:
        runtime_id: Runtime ID
        runtime_arn: Runtime ARN
        cognito_config: Cognito 설정 정보
        endpoint: Runtime 엔드포인트 (선택사항)
    """
    config_file = SCRIPT_DIR / "runtime_config.json"

    # -------------------------------------------------------------------------
    # Runtime Invocation URL 구성
    # -------------------------------------------------------------------------
    # Gateway가 Runtime에 접근할 때 사용하는 URL입니다.
    # ARN을 URL 인코딩하여 경로에 포함합니다.

    encoded_arn = quote(runtime_arn, safe='')
    runtime_invocation_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

    config = {
        "runtime_id": runtime_id,
        "runtime_arn": runtime_arn,
        "runtime_name": RUNTIME_NAME,
        "endpoint": endpoint,
        "runtime_url": runtime_invocation_url,
        "region": REGION,
        "cognito": {
            "pool_id": cognito_config["pool_id"],
            "client_id": cognito_config["client_id"],
            "discovery_url": cognito_config["discovery_url"],
            "token_endpoint": cognito_config["token_endpoint"],
        }
    }

    config_file.write_text(json.dumps(config, indent=2))
    print_info(f"설정 저장됨: {config_file}")
    print_info(f"Runtime URL: {runtime_invocation_url}")


# ============================================================================
# 메인 함수 (Main Function)
# ============================================================================

def main():
    """
    메인 배포 함수입니다.

    실행 흐름:
    1. 기존 Runtime 확인
       - 있으면: --delete 플래그에 따라 삭제 또는 재사용
       - 없으면: 새로 생성
    2. Cognito 설정 (User Pool, App Client)
    3. Starter Toolkit으로 Runtime 배포
    4. READY 상태 대기
    5. 설정 파일 저장
    6. OAuth 토큰 테스트

    Returns:
        int: 종료 코드 (0=성공, 1=실패)
    """
    print_header("AgentCore Runtime 배포 - MCP 서버")
    print_info(f"Runtime 이름: {RUNTIME_NAME}")
    print_info(f"리전: {REGION}")
    print_info(f"MCP 서버: {MCP_SERVER_FILE}")

    # --delete 플래그 확인
    delete_existing = "--delete" in sys.argv

    # AgentCore 클라이언트 생성
    client = get_agentcore_client()

    # -------------------------------------------------------------------------
    # 기존 Runtime 확인
    # -------------------------------------------------------------------------

    existing = get_runtime_by_name(client, RUNTIME_NAME)
    if existing:
        runtime_id = existing.get("agentRuntimeId")
        status = existing.get("status")
        print(f"\n기존 Runtime 발견:")
        print_info(f"ID: {runtime_id}")
        print_info(f"상태: {status}")

        if delete_existing:
            # 삭제 후 재생성
            print("\n기존 Runtime 삭제 중...")
            if not delete_runtime(client, runtime_id):
                return 1
            # 설정 파일 정리
            config_yaml = SCRIPT_DIR / ".bedrock_agentcore.yaml"
            if config_yaml.exists():
                config_yaml.unlink()
                print_info(".bedrock_agentcore.yaml 정리됨")
        else:
            # 기존 Runtime 재사용
            details = get_runtime_details(client, runtime_id)
            endpoint = details.get("agentRuntimeEndpoint")

            if status == "READY":
                print_success("Runtime이 READY 상태입니다")

                # Cognito 설정 로드 또는 생성
                cognito_file = SCRIPT_DIR / "cognito_config.json"
                if cognito_file.exists():
                    cognito_config = json.loads(cognito_file.read_text())
                else:
                    cognito_config = setup_cognito_for_runtime()

                save_config(runtime_id, details.get("agentRuntimeArn"), cognito_config, endpoint)
                return 0
            else:
                print_info("Runtime이 준비되지 않았습니다. --delete로 재생성하세요.")
                return 1

    # -------------------------------------------------------------------------
    # 새 Runtime 배포
    # -------------------------------------------------------------------------

    # Cognito 설정
    cognito_config = setup_cognito_for_runtime()

    # Starter Toolkit으로 배포
    result = deploy_with_starter_toolkit(cognito_config)
    if not result:
        print_error("Runtime 배포 실패")
        return 1

    runtime_id = result["runtime_id"]
    runtime_arn = result["runtime_arn"]

    # READY 상태 대기
    runtime = wait_for_runtime_ready(client, runtime_id)
    if not runtime:
        print_error("Runtime이 READY 상태에 도달하지 못했습니다")
        return 1

    # 설정 저장
    endpoint = runtime.get("agentRuntimeEndpoint")
    print_header("배포 완료!")
    print_success("Runtime이 READY 상태입니다")
    print_info(f"Runtime ID: {runtime_id}")
    print_info(f"Runtime ARN: {runtime_arn}")

    save_config(runtime_id, runtime_arn, cognito_config, endpoint)

    # -------------------------------------------------------------------------
    # OAuth 토큰 테스트
    # -------------------------------------------------------------------------
    # 배포된 Cognito 설정이 올바른지 토큰 발급을 테스트합니다.

    print("\n[OAuth 테스트]")
    try:
        token = _get_bearer_token_internal(cognito_config)
        print_success(f"Bearer 토큰 발급됨 ({len(token)} 문자)")
    except Exception as e:
        print_error(f"토큰 오류: {e}")

    # 다음 단계 안내
    print("\n다음 단계:")
    print("  1. MCP URL과 Bearer 토큰으로 호출 테스트")
    print("  2. 노트북에서 Gateway Target 생성")

    return 0


if __name__ == "__main__":
    sys.exit(main())
