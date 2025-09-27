"""
Spring Boot 스타일 자동 주입 사용 예제
진짜 Spring Boot처럼 동작합니다!
"""

from .spring_di import service, repository, controller, autowired, ApplicationContext, get_component
from fastapi import FastAPI, Depends
from typing import Protocol
from abc import ABC, abstractmethod

# 1. 인터페이스 정의 (Java의 interface 같은 역할)
class IUserRepository(Protocol):
    def find_by_email(self, email: str) -> str:
        ...

    def save(self, user_data: dict) -> str:
        ...

# 2. Repository Layer - @Repository로 자동 등록
@repository()
class UserRepository(IUserRepository):
    def find_by_email(self, email: str) -> str:
        return f"User found: {email}"

    def save(self, user_data: dict) -> str:
        return f"User saved: {user_data}"

# 3. 또 다른 의존성 서비스
@service()
class EmailService:
    def send_welcome_email(self, email: str) -> str:
        return f"Welcome email sent to {email}"

# 4. Service Layer - 의존성 자동 주입!
@service()
class UserService:
    def __init__(self, user_repo: IUserRepository, email_service: EmailService):
        self.user_repo = user_repo
        self.email_service = email_service

    def create_user(self, email: str) -> dict:
        # 비즈니스 로직
        user = self.user_repo.save({"email": email})
        welcome_msg = self.email_service.send_welcome_email(email)

        return {
            "user": user,
            "welcome_message": welcome_msg
        }

    def find_user(self, email: str) -> str:
        return self.user_repo.find_by_email(email)

# 5. Controller Layer - 완전 자동!
@controller()
class UserController:
    # 방법 1: 생성자 주입 (Spring Boot 권장)
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def create_user_endpoint(self, email: str):
        return self.user_service.create_user(email)

# 6. 또는 필드 주입도 가능! (Spring Boot의 @Autowired)
@controller()
class UserControllerWithFieldInjection:
    # 방법 2: 필드 주입 - @Autowired 사용
    user_service: UserService = autowired(UserService)

    def create_user_endpoint(self, email: str):
        return self.user_service.create_user(email)

# 7. FastAPI 앱 생성 및 라우팅
app = FastAPI(title="Spring Boot Style DI")

@app.on_event("startup")
async def startup():
    """앱 시작시 컴포넌트 스캔 및 자동 주입"""
    ApplicationContext.scan_and_autowire()
    print("🚀 All components autowired!")

# 8. FastAPI 엔드포인트 - Spring Boot처럼 간단!
@app.post("/users")
async def create_user(
    email: str,
    controller: UserController = Depends(lambda: get_component(UserController))
):
    return controller.create_user_endpoint(email)

@app.get("/users/{email}")
async def find_user(
    email: str,
    service: UserService = Depends(lambda: get_component(UserService))
):
    return {"result": service.find_user(email)}

# 9. 더 간단한 방법 - 직접 주입
@app.get("/users/{email}/simple")
async def find_user_simple(email: str):
    # 컨테이너에서 직접 가져오기 - Spring의 @Autowired 같은 효과
    service = ApplicationContext.get_bean(UserService)
    return {"result": service.find_user(email)}

# 10. 테스트 코드
if __name__ == "__main__":
    print("=== Spring Boot Style DI 테스트 ===")

    # 1. 자동 주입 테스트
    user_service = ApplicationContext.get_bean(UserService)
    result = user_service.create_user("test@example.com")
    print("✅ 생성자 주입:", result)

    # 2. 필드 주입 테스트
    controller = ApplicationContext.get_bean(UserControllerWithFieldInjection)
    result2 = controller.create_user_endpoint("field@example.com")
    print("✅ 필드 주입:", result2)

    # 3. 인터페이스 주입 테스트
    repo = ApplicationContext.get_bean(IUserRepository)
    result3 = repo.find_by_email("interface@example.com")
    print("✅ 인터페이스 주입:", result3)

    print("\n🎉 Spring Boot 수준의 자동 주입 완성!")
    print("uvicorn spring_example:app --reload 로 서버 실행 가능")