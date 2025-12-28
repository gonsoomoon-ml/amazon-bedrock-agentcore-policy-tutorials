# Cedar Policy 문법 가이드

## 1. Cedar란?

**Cedar**는 AWS가 개발한 오픈소스 인가(Authorization) 정책 언어입니다.

"누가(Principal) 무엇을(Action) 어디에(Resource) 할 수 있는가?"를 선언적으로 정의합니다.

---

## 2. 왜 Cedar가 필요한가?

### JWT Scope의 한계

```
JWT Scope: "insurance-api/approve"

→ ApprovalTool 호출 가능
→ $100 승인 ✅
→ $10,000,000 승인 ✅  ← 위험!
→ critical risk 승인 ✅  ← 위험!
```

### Cedar로 해결

```cedar
permit(...) when {
  context.input.amount < 1000000 &&
  context.input.risk_level != "critical"
};
```

```
→ $100 승인 ✅
→ $10,000,000 승인 ❌ (금액 초과)
→ critical risk 승인 ❌ (위험 등급)
```

---

## 3. 기본 구조

```cedar
permit(
  principal,                                              // 누가
  action == AgentCore::Action::"TargetName___tool_name",  // 무엇을
  resource == AgentCore::Gateway::"arn:aws:..."           // 어디에
) when {
  // 조건
};
```

### 키워드

| 키워드 | 설명 | 예시 |
|--------|------|------|
| `permit` | 허용 정책 | `permit(principal, action, resource)` |
| `forbid` | 차단 정책 | `forbid(principal, action, resource)` |
| `when` | 조건절 | 특정 조건에서만 적용 |
| `unless` | 예외 조건 | 특정 조건 제외 |

---

## 4. 두 가지 평가 대상

Cedar 정책은 **두 가지 유형의 데이터**를 평가합니다:

### 4.1 Principal (요청자) - JWT 클레임

JWT 토큰의 클레임에서 추출한 **요청자의 속성**입니다.

```cedar
// 누가 요청하는가?
principal.hasTag("department_name")                    // 클레임 존재 확인
principal.getTag("department_name") == "finance"      // 정확한 값 비교
principal.getTag("groups") like "*admins*"            // 패턴 매칭
```

| 문법 | 설명 | 예시 |
|------|------|------|
| `principal.hasTag("claim")` | 클레임 존재 확인 | `hasTag("department_name")` |
| `principal.getTag("claim")` | 클레임 값 조회 | `getTag("groups")` |

### 4.2 Input (요청 내용) - 도구 파라미터

도구 호출 시 전달되는 **입력 인자**입니다.

```cedar
// 무엇을 요청하는가?
context.input.amount <= 1000                          // 숫자 비교 (Lambda만)
context.input.risk_level == "low"                     // 문자열 비교
context.input.risk_level like "*low*"                 // 패턴 매칭
```

| 문법 | 설명 | 예시 |
|------|------|------|
| `context.input.field` | 도구 인자 값 조회 | `context.input.amount` |
| `context.input.field == value` | 정확한 값 비교 | `risk_level == "low"` |
| `context.input.field <= value` | 숫자 비교 | `amount <= 1000` |
| `context.input.field like pattern` | 패턴 매칭 | `risk_level like "*low*"` |

### 4.3 복합 조건 (Principal + Input)

두 가지를 결합하여 **누가 + 무엇을** 동시에 평가:

```cedar
permit(principal, action, resource)
when {
    // Principal: 요청자가 finance 부서인가?
    principal.getTag("department_name") == "finance" &&
    // Input: 요청 금액이 $1000 이하인가?
    context.input.amount <= 1000
};
```

| 시나리오 | 결과 |
|----------|------|
| Finance 부서 + $500 환불 | ✅ 허용 |
| Finance 부서 + $1500 환불 | ❌ 거부 (금액 초과) |
| Engineering 부서 + $500 환불 | ❌ 거부 (부서 불일치) |

---

## 5. 실전 예제

### 5.1 부서 기반 접근 제어

```cedar
// finance 부서만 환불 도구 사용 가능
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/my-gateway"
) when {
  principal.hasTag("department_name") &&
  principal.getTag("department_name") == "finance"
};
```

### 5.2 그룹 기반 접근 제어

```cedar
// admins 그룹에 속한 사용자만 허용
permit(principal, action, resource)
when {
  principal.hasTag("groups") &&
  principal.getTag("groups") like "*admins*"
};
```

### 5.3 금액 제한 (Lambda 타겟)

```cedar
// $1,000 이하 환불만 허용
permit(principal, action, resource)
when {
  context.input.amount <= 1000
};
```

### 5.4 위험 등급 제한 (MCP 타겟)

```cedar
// low 위험 등급만 허용 (문자열 비교)
permit(principal, action, resource)
when {
  context.input.risk_level like "*low*"
};
```

### 5.5 복합 조건

```cedar
// finance 부서 AND $1,000 이하
permit(principal, action, resource)
when {
  principal.hasTag("department_name") &&
  principal.getTag("department_name") == "finance" &&
  context.input.amount <= 1000
};
```

### 5.6 특정 역할 차단

```cedar
// intern 역할 차단
forbid(principal, action, resource)
when {
  principal.hasTag("role") &&
  principal.getTag("role") == "intern"
};
```

---

## 6. 패턴 매칭 (`like`)

| 패턴 | 설명 | 매칭 예시 |
|------|------|----------|
| `"*admin*"` | "admin" 포함 | admin, super-admin, admin-team |
| `"admin*"` | "admin"으로 시작 | admin, admin-team |
| `"*admin"` | "admin"으로 끝남 | super-admin |
| `"team-*"` | "team-"으로 시작 | team-finance, team-hr |

---

## 7. 주의사항

### 7.1 hasTag() 먼저 확인

```cedar
// ❌ 잘못된 코드 - 클레임이 없으면 오류
when { principal.getTag("department") == "finance" };

// ✅ 올바른 코드 - 존재 여부 먼저 확인
when {
  principal.hasTag("department") &&
  principal.getTag("department") == "finance"
};
```

### 7.2 MCP 타겟에서 숫자 비교

MCP 서버는 파라미터를 `float` 타입으로 전달하여 Cedar 숫자 비교가 실패할 수 있습니다.

```cedar
// ❌ MCP 타겟에서 실패할 수 있음
when { context.input.amount <= 1000 };

// ✅ 문자열 비교로 대체
when { context.input.risk_level like "*low*" };
```

### 7.3 패턴 매칭 주의

`like "*value*"`는 의도치 않은 매칭이 발생할 수 있습니다:

```cedar
// "admins" 그룹을 찾으려 했지만...
principal.getTag("groups") like "*admin*"

// 다음도 매칭됨: "system-admin", "admin-readonly", "not-admin-but-similar"
```

### 7.4 ALLOW/DENY 모두 테스트

정책을 배포하기 전에 **양쪽 시나리오**를 모두 검증하세요:

```python
# 허용 테스트
result = make_gateway_request(department="finance", amount=500)
assert analyze_response(result) == "ALLOWED"

# 거부 테스트
result = make_gateway_request(department="engineering", amount=500)
assert analyze_response(result) == "DENIED"
```

---

## 8. 참고 자료

- [Cedar 공식 사이트](https://www.cedarpolicy.com/)
- [Cedar 플레이그라운드](https://www.cedarpolicy.com/en/playground)
- [Amazon Verified Permissions](https://aws.amazon.com/verified-permissions/)
