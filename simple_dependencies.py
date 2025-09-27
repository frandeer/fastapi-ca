# 현재 프로젝트용 - 가장 실용적인 DI 패턴

from typing import Annotated
from functools import lru_cache
from fastapi import Depends

from user.infra.repository.user_repo import UserRepository
from user.application.user_service import UserService
from user.application.email_service import EmailService
from utils.crypto import Crypto
from ulid import ULID

# 1. 설정 캐싱
@lru_cache()
def get_crypto():
    return Crypto()

@lru_cache()
def get_ulid():
    return ULID()

# 2. 리포지토리 팩토리
def get_user_repository():
    return UserRepository()

# 3. 서비스 팩토리
def get_email_service():
    return EmailService()

def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    email_service: EmailService = Depends(get_email_service),
    crypto: Crypto = Depends(get_crypto),
    ulid: ULID = Depends(get_ulid),
):
    return UserService(
        user_repo=user_repo,
        email_service=email_service,
        crypto=crypto,
        ulid=ulid,
        send_welcome_email_task=None  # TODO: 나중에 추가
    )

# 4. 타입 앨리어스 - 이게 레전드급!
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]

# 5. 컨트롤러에서 사용 - 매우 깔끔!
"""
@router.post("/users")
def create_user(
    user_data: CreateUserBody,
    service: UserServiceDep  # 이것만 하면 끝!
):
    return service.create_user(...)
"""