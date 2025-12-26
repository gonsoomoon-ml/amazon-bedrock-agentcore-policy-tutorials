"""
인증 유틸리티 모듈

OAuth2 토큰 발급 및 JWT 디코딩 관련 함수를 제공합니다.
"""

import json
import base64
from typing import Dict, Any

import requests


def get_bearer_token(
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    scope: str = ""
) -> str:
    """
    OAuth2 Client Credentials Flow를 사용하여 Bearer 토큰을 발급받습니다.

    Args:
        token_endpoint: Cognito 토큰 엔드포인트 URL
        client_id: Cognito App Client ID
        client_secret: Cognito App Client Secret
        scope: OAuth2 scope (선택사항)

    Returns:
        Access Token 문자열

    Example:
        >>> token = get_bearer_token(
        ...     token_endpoint="https://xxx.auth.us-east-1.amazoncognito.com/oauth2/token",
        ...     client_id="abc123",
        ...     client_secret="secret"
        ... )
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # scope가 설정된 경우 추가
    if scope:
        data["scope"] = scope

    response = requests.post(
        token_endpoint,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def decode_token(access_token: str) -> Dict[str, Any]:
    """
    JWT 토큰을 디코딩하여 클레임을 확인합니다 (서명 검증 없음).

    주의: 이 함수는 디버깅 용도로만 사용하세요.
          프로덕션에서는 반드시 서명을 검증해야 합니다.

    Args:
        access_token: JWT Access Token

    Returns:
        디코딩된 토큰 페이로드 (딕셔너리)

    Example:
        >>> claims = decode_token(token)
        >>> print(claims.get("sub"))  # 사용자 ID
        >>> print(claims.get("department_name"))  # 커스텀 클레임
    """
    parts = access_token.split(".")
    if len(parts) != 3:
        raise ValueError("잘못된 JWT 토큰 형식입니다")

    # 페이로드 디코딩 (필요시 패딩 추가)
    payload_encoded = parts[1]
    padding = 4 - len(payload_encoded) % 4
    if padding != 4:
        payload_encoded += "=" * padding

    return json.loads(base64.urlsafe_b64decode(payload_encoded))


def make_gateway_request(
    gateway_url: str,
    bearer_token: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Amazon Bedrock AgentCore Gateway에 JSON-RPC 요청을 보냅니다.

    Args:
        gateway_url: Gateway MCP 엔드포인트 URL
        bearer_token: OAuth2 Access Token
        tool_name: 호출할 도구 이름
        arguments: 도구 인자

    Returns:
        JSON-RPC 응답

    Example:
        >>> result = make_gateway_request(
        ...     gateway_url="https://xxx.gateway...",
        ...     bearer_token=token,
        ...     tool_name="RefundToolTarget___refund",
        ...     arguments={"amount": 500, "orderId": "test-001"}
        ... )
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    response = requests.post(
        gateway_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
        },
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def analyze_response(result: Dict[str, Any]) -> str:
    """
    Gateway 응답을 분석하여 결과를 판단합니다.

    Args:
        result: Gateway 응답 딕셔너리

    Returns:
        'ALLOWED', 'DENIED', 또는 'ERROR'
    """
    # JSON-RPC 에러 확인 (정책 거부는 특정 메시지와 함께 에러로 반환됨)
    if "error" in result:
        error_msg = result["error"].get("message", "").lower()
        # 정책 거부 메시지 패턴
        if any(
            phrase in error_msg
            for phrase in ["not allowed", "denied", "forbidden", "unauthorized action"]
        ):
            return "DENIED"
        return "ERROR"

    if "result" in result:
        # 결과가 에러를 나타내는지 확인
        if result["result"].get("isError", False):
            content = result["result"].get("content", [])
            if content:
                text = (
                    content[0].get("text", "").lower()
                    if isinstance(content[0], dict)
                    else str(content[0]).lower()
                )
                if any(
                    phrase in text for phrase in ["not allowed", "denied", "forbidden"]
                ):
                    return "DENIED"
            return "DENIED"
        return "ALLOWED"

    return "UNKNOWN"


def display_test_result(expected: str, actual: str, description: str) -> bool:
    """
    테스트 결과를 포맷팅하여 출력합니다.

    Args:
        expected: 예상 결과
        actual: 실제 결과
        description: 테스트 설명

    Returns:
        테스트 통과 여부
    """
    passed = expected == actual
    status = "✓ 통과" if passed else "✗ 실패"
    print(f"\n{status}: {description}")
    print(f"   예상: {expected}")
    print(f"   실제: {actual}")
    return passed
