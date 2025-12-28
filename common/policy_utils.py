"""
Policy 유틸리티 모듈

Policy Engine 및 Cedar 정책 관리 함수를 제공합니다.
"""

import time
import uuid
from typing import Dict, Any, Optional, List

from botocore.exceptions import ClientError


def create_policy_engine(
    policy_client,
    name: str,
    description: str = ""
) -> Optional[str]:
    """
    새로운 Policy Engine을 생성합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        name: Policy Engine 이름
        description: 설명 (선택사항)

    Returns:
        생성된 Policy Engine ID, 실패 시 None
    """
    print(f"\nPolicy Engine 생성: {name}")
    print("=" * 70)

    try:
        response = policy_client.create_policy_engine(
            name=name,
            description=description or f"생성 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            clientToken=str(uuid.uuid4()),
        )

        policy_engine_id = response["policyEngineId"]
        print("✓ Policy Engine 생성됨")
        print(f"  Policy Engine ID: {policy_engine_id}")

        return policy_engine_id

    except ClientError as e:
        print(f"✗ Policy Engine 생성 오류: {e}")
        return None


def get_policy_engine(policy_client, policy_engine_id: str) -> Optional[Dict[str, Any]]:
    """
    Policy Engine 상세 정보를 조회합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID

    Returns:
        Policy Engine 상세 정보, 없으면 None
    """
    try:
        return policy_client.get_policy_engine(policyEngineId=policy_engine_id)
    except ClientError:
        return None


def wait_for_policy_engine_active(
    policy_client,
    policy_engine_id: str,
    timeout: int = 300
) -> bool:
    """
    Policy Engine이 ACTIVE 상태가 될 때까지 대기합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        timeout: 최대 대기 시간 (초)

    Returns:
        ACTIVE 상태 도달 여부
    """
    print("\nPolicy Engine ACTIVE 상태 대기 중...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        engine = get_policy_engine(policy_client, policy_engine_id)
        if not engine:
            time.sleep(5)
            continue

        status = engine.get("status")
        print(f"  상태: {status}")

        if status == "ACTIVE":
            print("✓ Policy Engine이 ACTIVE 상태입니다")
            return True

        if status in ["CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED"]:
            print(f"✗ Policy Engine 실패: {engine.get('statusReason', '알 수 없음')}")
            return False

        time.sleep(5)

    print("✗ Policy Engine 대기 시간 초과")
    return False


def create_cedar_policy(
    policy_client,
    policy_engine_id: str,
    policy_name: str,
    cedar_statement: str,
    description: str = ""
) -> Optional[str]:
    """
    Policy Engine에 Cedar 정책을 생성합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        policy_name: 정책 이름
        cedar_statement: Cedar 정책 문
        description: 정책 설명 (선택사항)

    Returns:
        생성된 정책 ID, 실패 시 None
    """
    print(f"\nCedar 정책 생성: {policy_name}")
    print("=" * 70)
    print("\nCedar 정책문:")
    print("-" * 60)
    print(cedar_statement)
    print("-" * 60)

    try:
        response = policy_client.create_policy(
            policyEngineId=policy_engine_id,
            name=policy_name,
            description=description or f"정책: {policy_name}",
            definition={"cedar": {"statement": cedar_statement}},
        )

        policy_id = response["policyId"]
        policy_status = response["status"]

        print("\n✓ 정책이 성공적으로 생성되었습니다")
        print(f"  정책 ID: {policy_id}")
        print(f"  상태: {policy_status}")

        return policy_id

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        print(f"\n✗ 정책 생성 오류: {error_code}")
        print(f"  {error_msg}")
        return None


def get_policy(
    policy_client,
    policy_engine_id: str,
    policy_id: str
) -> Optional[Dict[str, Any]]:
    """
    정책 상세 정보를 조회합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        policy_id: 정책 ID

    Returns:
        정책 상세 정보, 없으면 None
    """
    try:
        return policy_client.get_policy(
            policyEngineId=policy_engine_id, policyId=policy_id
        )
    except ClientError:
        return None


def wait_for_policy_active(
    policy_client,
    policy_engine_id: str,
    policy_id: str,
    timeout: int = 60
) -> bool:
    """
    정책이 ACTIVE 상태가 될 때까지 대기합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        policy_id: 정책 ID
        timeout: 최대 대기 시간 (초)

    Returns:
        ACTIVE 상태 도달 여부
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        policy = get_policy(policy_client, policy_engine_id, policy_id)
        if not policy:
            print(f"  ⚠️  정책을 찾을 수 없음: {policy_id}")
            return False

        status = policy.get("status")
        print(f"  정책 상태: {status}")

        if status == "ACTIVE":
            return True

        if status in ["CREATE_FAILED", "UPDATE_FAILED"]:
            reason = policy.get('statusReason') or policy.get('failureReason') or '알 수 없음'
            print(f"  ✗ 정책 실패: {reason}")
            # Print full response for debugging
            import json
            debug_info = {k: v for k, v in policy.items() if k not in ['document', 'createdAt', 'lastUpdatedAt']}
            print(f"  디버그 정보: {json.dumps(debug_info, default=str)}")
            return False

        time.sleep(3)

    print("  ✗ 정책 ACTIVE 대기 시간 초과")
    return False


def delete_policy(
    policy_client,
    policy_engine_id: str,
    policy_id: str
) -> bool:
    """
    Policy Engine에서 정책을 삭제합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        policy_id: 정책 ID

    Returns:
        삭제 성공 여부
    """
    try:
        policy_client.delete_policy(policyEngineId=policy_engine_id, policyId=policy_id)
        print(f"✓ 정책 삭제됨: {policy_id}")
        return True
    except ClientError as e:
        print(f"⚠️  정책 삭제 실패 {policy_id}: {e}")
        return False


def list_policies(
    policy_client,
    policy_engine_id: str
) -> List[Dict[str, Any]]:
    """
    Policy Engine의 모든 정책을 조회합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID

    Returns:
        정책 목록
    """
    try:
        response = policy_client.list_policies(policyEngineId=policy_engine_id)
        return response.get("policies", [])
    except ClientError:
        return []


def cleanup_existing_policies(
    policy_client,
    policy_engine_id: str,
    require_confirmation: bool = False
) -> int:
    """
    Policy Engine의 기존 정책을 모두 삭제합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: Policy Engine ID
        require_confirmation: True인 경우 삭제 전 확인 요청

    Returns:
        삭제된 정책 수
    """
    print("\n🧹 기존 정책 확인 중...")
    print("=" * 70)

    policies = list_policies(policy_client, policy_engine_id)

    if not policies:
        print("✓ 기존 정책이 없습니다. 진행 준비 완료.")
        return 0

    print(f"\n⚠️  {len(policies)}개의 기존 정책 발견:")
    for p in policies:
        print(
            f"   - {p.get('name', '이름 없음')} (ID: {p.get('policyId')}, 상태: {p.get('status')})"
        )

    if require_confirmation:
        print("\n" + "-" * 70)
        confirm = (
            input("모든 기존 정책을 삭제하시겠습니까? (yes/no): ")
            .strip()
            .lower()
        )
        if confirm != "yes":
            print("\n⏭️  정리를 건너뜁니다. 기존 정책이 유지됩니다.")
            print("   참고: 예상치 못한 정책 평가 결과가 발생할 수 있습니다.")
            return 0

    print("\n🗑️  기존 정책 삭제 중...")
    deleted_count = 0
    for p in policies:
        policy_id = p.get("policyId")
        if policy_id and delete_policy(policy_client, policy_engine_id, policy_id):
            deleted_count += 1

    print(f"\n✓ {deleted_count}/{len(policies)}개 정책 삭제됨")
    return deleted_count


def ensure_policy_engine(
    policy_client,
    policy_engine_id: Optional[str] = None,
    create_if_missing: bool = True
) -> Optional[str]:
    """
    Policy Engine이 존재하고 ACTIVE 상태인지 확인합니다.
    필요시 새로 생성합니다.

    Args:
        policy_client: bedrock-agentcore-control boto3 클라이언트
        policy_engine_id: 기존 Policy Engine ID (선택사항)
        create_if_missing: 없을 경우 생성 여부

    Returns:
        Policy Engine ID, 실패 시 None
    """
    print("\nPolicy Engine 확인")
    print("=" * 70)

    # 기존 Policy Engine ID가 있는 경우 확인
    if policy_engine_id:
        engine = get_policy_engine(policy_client, policy_engine_id)
        if engine and engine.get("status") == "ACTIVE":
            print(f"✓ 기존 Policy Engine 사용: {policy_engine_id}")
            return policy_engine_id

    # 기존 Policy Engine 목록 확인
    try:
        response = policy_client.list_policy_engines()
        engines = response.get("policyEngines", [])

        for engine in engines:
            if engine.get("status") == "ACTIVE":
                found_id = engine["policyEngineId"]
                print(f"✓ 기존 ACTIVE Policy Engine 발견: {found_id}")
                return found_id
    except ClientError:
        pass

    # 새로 생성
    if create_if_missing:
        engine_name = f"PolicyEngine_{int(time.time())}"
        new_id = create_policy_engine(policy_client, engine_name)

        if new_id and wait_for_policy_engine_active(policy_client, new_id):
            return new_id

    return None
