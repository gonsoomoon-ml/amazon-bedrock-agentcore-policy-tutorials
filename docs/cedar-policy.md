# Cedar Policy 문법 가이드

## Cedar란?

**Cedar**는 AWS가 개발한 오픈소스 인가(Authorization) 정책 언어입니다.

"누가(Principal) 무엇을(Action) 어디에(Resource) 할 수 있는가?"를 선언적으로 정의합니다.

## 기본 구조

```cedar
permit(
  principal == User::"alice",           // 누가
  action == Action::"view",             // 무엇을
  resource == Document::"report.pdf"    // 어디에
);
```

## 키워드

| 키워드 | 설명 | 예시 |
|--------|------|------|
| `permit` | 허용 정책 | `permit(principal, action, resource)` |
| `forbid` | 차단 정책 | `forbid(principal, action, resource)` |
| `principal` | 요청하는 주체 | 사용자, 역할, 서비스 |
| `action` | 수행할 작업 | 도구 호출, API 요청 |
| `resource` | 대상 리소스 | Gateway, Lambda |
| `when` | 조건절 | 특정 조건에서만 적용 |
| `unless` | 예외 조건 | 특정 조건 제외 |

## AgentCore에서의 Cedar 사용

### 기본 패턴

```cedar
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  // 조건
};
```

### Principal Tags (JWT 클레임) 접근

JWT 토큰의 클레임은 `principal.hasTag()` 및 `principal.getTag()`로 접근합니다.

| 패턴 | Cedar 문법 |
|------|------------|
| 클레임 존재 확인 | `principal.hasTag("claim_name")` |
| 정확한 일치 | `principal.getTag("claim_name") == "value"` |
| 패턴 매칭 | `principal.getTag("claim_name") like "*value*"` |
| 입력값 검증 | `context.input.field <= value` |

## 예제

### 1. 부서 기반 접근 제어

```cedar
// finance 부서만 허용
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  principal.hasTag("department_name") &&
  principal.getTag("department_name") == "finance"
};
```

### 2. 그룹 기반 접근 제어

```cedar
// admins 그룹에 속한 사용자만 허용
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  principal.hasTag("groups") &&
  principal.getTag("groups") like "*admins*"
};
```

### 3. 금액 제한

```cedar
// $1000 이하만 허용
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  context.input.amount <= 1000
};
```

### 4. 복합 조건

```cedar
// finance 부서 AND $1000 이하
permit(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  principal.hasTag("department_name") &&
  principal.getTag("department_name") == "finance" &&
  context.input.amount <= 1000
};
```

### 5. 특정 사용자 차단

```cedar
// 특정 역할 차단
forbid(
  principal,
  action == AgentCore::Action::"RefundToolTarget___refund",
  resource == AgentCore::Gateway::"arn:aws:..."
) when {
  principal.hasTag("role") &&
  principal.getTag("role") == "intern"
};
```

## 패턴 매칭 (`like` 연산자)

| 패턴 | 설명 | 예시 매칭 |
|------|------|----------|
| `"*admin*"` | "admin" 포함 | "admin", "super-admin", "admin-team" |
| `"admin*"` | "admin"으로 시작 | "admin", "admin-team" |
| `"*admin"` | "admin"으로 끝남 | "super-admin", "admin" |
| `"team-*"` | "team-"으로 시작 | "team-finance", "team-hr" |

## JWT Scope vs Cedar Policy

### JWT Scope의 한계

```
JWT Scope: "insurance-api/approve"

→ ApprovalTool 호출 가능
→ $100 승인 ✅
→ $10,000,000 승인 ✅  ← 위험!
→ critical risk 승인 ✅  ← 위험!
```

### Cedar Policy로 해결

```cedar
permit(...) when {
  context.input.claim_amount < 1000000 &&
  context.input.risk_level != "critical"
};
```

```
→ $100 승인 ✅
→ $10,000,000 승인 ❌ (금액 초과)
→ critical risk 승인 ❌ (위험 등급)
```

## 모범 사례

1. **hasTag() 먼저 확인**: `getTag()` 전에 항상 `hasTag()`로 존재 확인
2. **구체적인 action 사용**: 와일드카드보다 구체적인 도구 이름 사용
3. **패턴 매칭 주의**: `like "*value*"`는 의도치 않은 매칭 가능
4. **ALLOW/DENY 모두 테스트**: 양쪽 시나리오 모두 검증
5. **정책 문서화**: 설명적인 이름과 description 사용

## 참고 자료

- [Cedar 공식 사이트](https://www.cedarpolicy.com/)
- [Cedar 플레이그라운드](https://www.cedarpolicy.com/en/playground)
