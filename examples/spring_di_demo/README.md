# Spring Boot Style Dependency Injection for Python/FastAPI

이 예제는 Python과 FastAPI에서 Spring Boot 수준의 자동 의존성 주입을 구현한 데모입니다.

## 주요 기능

### 1. Spring Boot 스타일 데코레이터
- `@service()` - 서비스 레이어 컴포넌트
- `@repository()` - 데이터 액세스 레이어 컴포넌트
- `@controller()` - 컨트롤러 레이어 컴포넌트
- `@component()` - 범용 컴포넌트

### 2. 자동 의존성 주입
- **생성자 주입**: 클래스 생성자 파라미터 타입 힌트 기반 자동 주입
- **필드 주입**: `@autowired(Type)` 데코레이터로 필드 자동 주입
- **인터페이스 주입**: Protocol/ABC 인터페이스 자동 구현체 매칭

### 3. Spring Boot 기능들
- **싱글톤 스코프**: 기본적으로 모든 빈은 싱글톤으로 관리
- **프로토타입 스코프**: 매번 새 인스턴스 생성
- **순환 의존성 해결**: 지연 로딩으로 순환 의존성 방지
- **타입 안전성**: 타입 힌트 기반 컴파일 타임 검증

## 파일 구조

```
spring_di_demo/
├── __init__.py
├── README.md
├── spring_di.py        # 핵심 DI 시스템
├── demo_app.py         # FastAPI 데모 앱
└── test_spring_di.py   # 테스트 코드
```

## 사용법

### 1. 기본 사용법

```python
from spring_di import service, repository

@repository()
class UserRepository:
    def find_by_id(self, user_id: int):
        return f"User {user_id}"

@service()
class UserService:
    def __init__(self, user_repo: UserRepository):  # 자동 주입!
        self.user_repo = user_repo

    def get_user(self, user_id: int):
        return self.user_repo.find_by_id(user_id)
```

### 2. FastAPI 통합

```python
from fastapi import FastAPI, Depends
from spring_di import get_component

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(lambda: get_component(UserService))
):
    return service.get_user(user_id)
```

### 3. 데모 실행

```bash
# 데모 앱 실행
cd examples/spring_di_demo
python -c "from demo_app import *; print('Demo loaded successfully!')"

# FastAPI 서버 실행
uvicorn demo_app:app --reload
```

## 테스트

```bash
# 테스트 실행
python -m pytest examples/spring_di_demo/test_spring_di.py -v
```

## Spring Boot와의 비교

| Spring Boot | Python DI System |
|-------------|------------------|
| `@Service` | `@service()` |
| `@Repository` | `@repository()` |
| `@Controller` | `@controller()` |
| `@Autowired` | `autowired(Type)` |
| `ApplicationContext.getBean()` | `ApplicationContext.get_bean()` |
| Constructor Injection | 생성자 타입 힌트 자동 주입 |
| Field Injection | `@autowired` 필드 자동 주입 |

이 시스템을 통해 Python에서도 Spring Boot 수준의 개발 경험을 얻을 수 있습니다!