# 문제 해결 가이드

## 자주 발생하는 오류

### 1. 401 Unauthorized

**증상**: Gateway 요청 시 401 에러 발생

**원인 및 해결**:

| 원인 | 해결 방법 |
|------|----------|
| 토큰 만료 | 새 토큰 발급 |
| allowedAudience 설정됨 | `allowedAudience: []`로 설정 (Cognito는 aud 없음) |
| client_id 불일치 | `allowedClients`에 client_id 추가 |
| Discovery URL 오류 | User Pool ID 확인 |

**확인 코드**:
```python
# 토큰 디코딩하여 확인
claims = decode_token(token)
print(f"exp: {claims.get('exp')}")
print(f"client_id: {claims.get('client_id')}")
```

### 2. ValidationException: AuthorizerConfiguration is required

**증상**: Gateway 업데이트 시 에러

```
ValidationException: AuthorizerConfiguration is required for CUSTOM_JWT authorizer type
```

**원인**: `update_gateway` 호출 시 `authorizerConfiguration` 누락

**해결**:
```python
# ❌ 잘못된 코드
gateway_control_client.update_gateway(
    gatewayIdentifier=GATEWAY_ID,
    policyEngineConfiguration={"..."}
)

# ✅ 올바른 코드
gateway_control_client.update_gateway(
    gatewayIdentifier=GATEWAY_ID,
    authorizerConfiguration=gateway_config.get("authorizerConfiguration"),
    policyEngineConfiguration={"..."}
)
```

### 3. 커스텀 클레임이 토큰에 없음

**증상**: `decode_token()`으로 확인 시 커스텀 클레임 없음

**원인 및 해결**:

| 원인 | 해결 방법 |
|------|----------|
| Lambda 트리거 V1/V2 사용 | V3_0으로 변경 (M2M 필수) |
| Cognito 티어 부족 | Essentials 또는 Plus 티어로 업그레이드 |
| Lambda 권한 없음 | Cognito가 Lambda 호출 권한 추가 |
| Lambda 코드 오류 | CloudWatch Logs 확인 |

**Lambda 버전 확인**:
```python
cognito_client.describe_user_pool(UserPoolId=USER_POOL_ID)
# LambdaConfig > PreTokenGenerationConfig > LambdaVersion 확인
```

### 4. 정책이 적용되지 않음

**증상**: 정책 생성 후에도 모든 요청이 허용되거나 거부됨

**확인 사항**:

1. **정책 상태 확인**:
```python
policy = get_policy(policy_client, POLICY_ENGINE_ID, policy_id)
print(f"상태: {policy.get('status')}")  # ACTIVE여야 함
```

2. **Policy Engine이 Gateway에 연결되었는지 확인**:
```python
gw = get_gateway_details(gateway_control_client, GATEWAY_ID)
pe_config = gw.get("policyEngineConfiguration", {})
print(f"Policy Engine ARN: {pe_config.get('arn')}")
print(f"모드: {pe_config.get('mode')}")  # ENFORCE여야 함
```

3. **기존 정책 충돌**:
```python
# 모든 정책 확인
policies = list_policies(policy_client, POLICY_ENGINE_ID)
for p in policies:
    print(f"{p.get('name')}: {p.get('status')}")
```

### 5. Gateway가 READY 상태가 되지 않음

**증상**: Gateway 업데이트 후 READY 상태에 도달하지 않음

**확인**:
```python
gw = get_gateway_details(gateway_control_client, GATEWAY_ID)
print(f"상태: {gw.get('status')}")
print(f"상태 이유: {gw.get('statusReason', 'N/A')}")
```

**일반적인 원인**:
- IAM 역할 권한 부족
- Policy Engine ARN 오류
- 네트워크 설정 문제

### 6. input() 대기로 노트북 멈춤

**증상**: 셀이 오래 실행되며 멈춤

**원인**: `require_confirmation=True`로 설정된 함수에서 사용자 입력 대기

**해결**:
```python
# ❌ 멈추는 코드
cleanup_existing_policies(require_confirmation=True)

# ✅ 자동 실행
cleanup_existing_policies(require_confirmation=False)
```

## 디버깅 팁

### 토큰 내용 확인

```python
token = get_bearer_token(...)
claims = decode_token(token)
print(json.dumps(claims, indent=2))
```

### Gateway 설정 확인

```python
gw = get_gateway_details(gateway_control_client, GATEWAY_ID)
print(json.dumps(gw, indent=2, default=str))
```

### Policy Engine 정책 목록 확인

```python
policies = list_policies(policy_client, POLICY_ENGINE_ID)
for p in policies:
    print(f"- {p.get('name')}: {p.get('status')}")
```

### CloudWatch Logs 확인

Lambda 트리거 오류는 CloudWatch Logs에서 확인:
1. AWS Console → CloudWatch → Log groups
2. `/aws/lambda/cognito-custom-claims-{USER_POOL_ID}` 선택
3. 최근 로그 스트림 확인

## 모범 사례

### 1. 정책 생성 전 기존 정책 정리

```python
cleanup_existing_policies(
    policy_client, POLICY_ENGINE_ID,
    require_confirmation=False
)
```

### 2. 정책 ACTIVE 상태 확인

```python
policy_id = create_cedar_policy(...)
if policy_id:
    wait_for_policy_active(policy_client, POLICY_ENGINE_ID, policy_id)
```

### 3. 테스트 전 토큰 갱신

```python
# 항상 새 토큰 사용
token = get_bearer_token(...)
```

### 4. ALLOW/DENY 양쪽 테스트

```python
# 허용 테스트
result = make_gateway_request(...)
assert analyze_response(result) == "ALLOWED"

# 거부 테스트 (다른 클레임으로)
result = make_gateway_request(...)
assert analyze_response(result) == "DENIED"
```

## 지원 받기

문제가 해결되지 않으면:
1. AWS 지원 티켓 생성
2. CloudWatch Logs 첨부
3. Gateway/Policy Engine 설정 스크린샷 첨부
