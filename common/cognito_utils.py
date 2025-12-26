"""
Cognito 유틸리티 모듈

Amazon Cognito Lambda Trigger 설정 함수를 제공합니다.
"""

import json
import time
import os
import zipfile
import tempfile
from typing import Dict, Any, Optional


def create_lambda_function(
    lambda_client,
    iam_client,
    claims: Dict[str, Any],
    account_id: str,
    user_pool_id: str,
    function_name: Optional[str] = None
) -> str:
    """
    Pre Token Generation Lambda 트리거용 Lambda 함수를 생성하거나 업데이트합니다.

    이 Lambda 함수는 Cognito가 토큰을 발급할 때 호출되어
    JWT에 커스텀 클레임을 추가합니다.

    Args:
        lambda_client: Lambda boto3 클라이언트
        iam_client: IAM boto3 클라이언트
        claims: 토큰에 추가할 클레임 딕셔너리
        account_id: AWS 계정 ID
        user_pool_id: Cognito User Pool ID
        function_name: Lambda 함수 이름 (선택사항)

    Returns:
        Lambda 함수 ARN

    Example:
        >>> lambda_arn = create_lambda_function(
        ...     lambda_client, iam_client,
        ...     claims={"department_name": "finance", "role": "senior"},
        ...     account_id="123456789012",
        ...     user_pool_id="us-east-1_ABC123"
        ... )
    """
    if function_name is None:
        function_name = f"cognito-custom-claims-{user_pool_id}"

    print(f"\nLambda 함수 설정: {function_name}")
    print("=" * 70)

    # 지정된 클레임으로 Lambda 코드 생성
    claims_json = json.dumps(claims, indent=12)

    lambda_code = f'''
import json

def lambda_handler(event, context):
    """
    Cognito Pre-token generation V3 Lambda 트리거.
    client_credentials 플로우를 포함한 모든 플로우에서 JWT에 커스텀 클레임을 추가합니다.
    """
    print(f"Event: {{json.dumps(event)}}")
    print(f"Trigger Source: {{event.get('triggerSource', 'unknown')}}")

    # 토큰에 커스텀 클레임 추가
    event['response'] = {{
        'claimsAndScopeOverrideDetails': {{
            'accessTokenGeneration': {{
                'claimsToAddOrOverride': {claims_json}
            }},
            'idTokenGeneration': {{
                'claimsToAddOrOverride': {claims_json}
            }}
        }}
    }}

    print(f"Modified event: {{json.dumps(event)}}")
    return event
'''

    # 배포 패키지 생성
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        zip_path = tmp_file.name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("lambda_function.py", lambda_code)

    try:
        with open(zip_path, "rb") as f:
            zip_content = f.read()

        # 기존 함수 업데이트 시도
        try:
            lambda_client.update_function_code(
                FunctionName=function_name, ZipFile=zip_content
            )
            print("✓ Lambda 함수 코드 업데이트됨")
            response = lambda_client.get_function(FunctionName=function_name)
            return response["Configuration"]["FunctionArn"]

        except lambda_client.exceptions.ResourceNotFoundException:
            # 새 함수 생성 (IAM 역할 포함)
            role_name = f"{function_name}-role"
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

            # 필요시 IAM 역할 생성
            try:
                iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                }
                            ],
                        }
                    ),
                )
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                )
                print(f"✓ IAM 역할 생성됨: {role_name}")
                print("  IAM 역할 전파 대기 중...")
                time.sleep(10)
            except iam_client.exceptions.EntityAlreadyExistsException:
                print(f"  IAM 역할이 이미 존재함: {role_name}")

            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.12",
                Role=role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zip_content},
                Timeout=30,
                MemorySize=128,
            )
            print("✓ Lambda 함수 생성됨")
            return response["FunctionArn"]
    finally:
        os.remove(zip_path)


def configure_cognito_trigger(
    cognito_client,
    lambda_client,
    user_pool_id: str,
    lambda_arn: str,
    region: str,
    account_id: str
) -> None:
    """
    Cognito User Pool에 Lambda 트리거 V3_0을 설정합니다.

    중요: M2M (machine-to-machine) client credentials 플로우에서는
    Lambda 트리거 버전 V3_0을 반드시 사용해야 합니다.
    V3_0은 Cognito Essentials 또는 Plus 티어가 필요합니다.

    Args:
        cognito_client: Cognito IDP boto3 클라이언트
        lambda_client: Lambda boto3 클라이언트
        user_pool_id: Cognito User Pool ID
        lambda_arn: Lambda 함수 ARN
        region: AWS 리전
        account_id: AWS 계정 ID
    """
    print("\nCognito User Pool 트리거 설정")
    print("=" * 70)

    # V3_0 트리거로 User Pool 업데이트 (M2M에 필수)
    cognito_client.update_user_pool(
        UserPoolId=user_pool_id,
        LambdaConfig={
            "PreTokenGenerationConfig": {
                "LambdaVersion": "V3_0",
                "LambdaArn": lambda_arn,
            }
        },
    )
    print("✓ User Pool 트리거 설정됨 (V3_0)")
    print(f"  User Pool ID: {user_pool_id}")
    print(f"  Lambda ARN: {lambda_arn}")

    # Cognito 호출 권한 추가
    try:
        lambda_client.add_permission(
            FunctionName=lambda_arn,
            StatementId=f"CognitoInvoke-{user_pool_id}",
            Action="lambda:InvokeFunction",
            Principal="cognito-idp.amazonaws.com",
            SourceArn=f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{user_pool_id}",
        )
        print("✓ Cognito Lambda 호출 권한 추가됨")
    except lambda_client.exceptions.ResourceConflictException:
        print("  Lambda 권한이 이미 존재함")

    print("\n⚠️  중요: V3_0 트리거는 Cognito Essentials 또는 Plus 티어가 필요합니다")
