# Amazon Bedrock AgentCore Policy 가이드

## 개요

이 문서는 Amazon Bedrock AgentCore Policy의 핵심 개념과 사용 방법을 설명합니다.

## 목차

| 문서 | 내용 |
|------|------|
| [Amazon Cognito](cognito.md) | Cognito 개념 및 OAuth2 인증 플로우 |
| [Cedar Policy 문법](cedar-policy.md) | Cedar 정책 언어 문법 및 예제 |
| [JWT Authorizer](jwt-authorizer.md) | JWT Authorizer와 Scope 설명 |
| [문제 해결](troubleshooting.md) | 자주 발생하는 오류 및 해결 방법 |

## 아키텍처

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

## 핵심 개념

### Policy Engine

Cedar 정책을 저장하고 평가하는 엔진입니다. Gateway에 연결되어 모든 도구 호출 요청을 평가합니다.

### Cedar Policy

AWS가 개발한 오픈소스 인가(Authorization) 정책 언어입니다. "누가 무엇을 할 수 있는지" 선언적으로 정의합니다.

### JWT Authorizer

Gateway에서 JWT 토큰을 검증하는 컴포넌트입니다. 토큰의 서명, 만료, 발급자 등을 확인합니다.

### Principal Tags

JWT 토큰의 클레임이 Cedar에서 접근되는 방식입니다. `principal.getTag("claim_name")`으로 클레임 값에 접근합니다.

## 빠른 시작

1. **환경 설정**: `../03-Fine-Grained-Access-Control/setup-gateway.py` 실행
2. **튜토리얼 실행**: `tutorial.ipynb` 노트북 실행
3. **문서 참고**: 필요한 개념은 이 docs 폴더의 문서 참조

## 관련 링크

- [Cedar Policy 공식 사이트](https://www.cedarpolicy.com/)
- [Amazon Verified Permissions](https://aws.amazon.com/verified-permissions/)
- [Amazon Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/latest/developerguide/)
