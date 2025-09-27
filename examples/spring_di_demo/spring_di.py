"""
Spring Boot 수준의 자동 의존성 주입 시스템
메타클래스와 데코레이터를 활용한 완전 자동화
"""

import inspect
from typing import Dict, Type, Any, get_type_hints, Optional, get_origin, get_args
from functools import wraps
from enum import Enum
import threading

class Scope(Enum):
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"

class ComponentMeta(type):
    """컴포넌트 메타클래스 - 클래스 생성시 자동 등록"""
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        # @component 데코레이터가 적용된 경우에만 등록
        if hasattr(cls, '_is_component'):
            ApplicationContext.register_component(cls)

        return cls

class ApplicationContext:
    """Spring의 ApplicationContext 역할"""
    _components: Dict[Type, Any] = {}
    _component_configs: Dict[Type, dict] = {}
    _lock = threading.Lock()

    @classmethod
    def register_component(cls, component_type: Type, scope: Scope = Scope.SINGLETON, primary: bool = False):
        """컴포넌트 등록"""
        with cls._lock:
            cls._component_configs[component_type] = {
                'scope': scope,
                'primary': primary,
                'instance': None
            }

    @classmethod
    def get_bean(cls, bean_type: Type) -> Any:
        """빈 인스턴스 반환 (의존성 자동 주입)"""
        with cls._lock:
            config = cls._component_configs.get(bean_type)
            if not config:
                # 인터페이스인 경우 구현체 찾기
                implementations = cls._find_implementations(bean_type)
                if implementations:
                    bean_type = implementations[0]  # 첫 번째 구현체 사용
                    config = cls._component_configs.get(bean_type)

                if not config:
                    raise ValueError(f"No bean found for type: {bean_type.__name__}")

            # 싱글톤인 경우 기존 인스턴스 반환
            if config['scope'] == Scope.SINGLETON and config['instance']:
                return config['instance']

            # 새 인스턴스 생성 (의존성 자동 주입)
            instance = cls._create_instance(bean_type)

            if config['scope'] == Scope.SINGLETON:
                config['instance'] = instance

            return instance

    @classmethod
    def _create_instance(cls, component_type: Type) -> Any:
        """의존성 자동 주입으로 인스턴스 생성"""
        constructor = component_type.__init__
        signature = inspect.signature(constructor)
        dependencies = {}

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            param_type = param.annotation
            if param_type != inspect.Parameter.empty:
                # 재귀적으로 의존성 해결
                dependencies[param_name] = cls.get_bean(param_type)

        return component_type(**dependencies)

    @classmethod
    def _find_implementations(cls, interface_type: Type) -> list:
        """인터페이스의 구현체 찾기"""
        implementations = []
        for component_type in cls._component_configs.keys():
            if interface_type in component_type.__mro__:
                implementations.append(component_type)
        return implementations

    @classmethod
    def scan_and_autowire(cls):
        """모든 등록된 컴포넌트의 @Autowired 필드 처리"""
        for component_type, config in cls._component_configs.items():
            if config['instance']:
                cls._process_autowired_fields(config['instance'])

    @classmethod
    def _process_autowired_fields(cls, instance):
        """@Autowired 필드에 의존성 주입"""
        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if hasattr(attr, '_autowired'):
                field_type = attr._autowired_type
                setattr(instance, attr_name, cls.get_bean(field_type))

# 데코레이터들 - Spring Boot 스타일!

def component(scope: Scope = Scope.SINGLETON, primary: bool = False):
    """@Component - 범용 컴포넌트"""
    def decorator(cls):
        cls._is_component = True
        cls._scope = scope
        cls._primary = primary

        # 메타클래스 적용
        class ComponentClass(cls, metaclass=ComponentMeta):
            pass

        ComponentClass.__name__ = cls.__name__
        ComponentClass.__qualname__ = cls.__qualname__

        ApplicationContext.register_component(ComponentClass, scope, primary)
        return ComponentClass

    return decorator

def service(scope: Scope = Scope.SINGLETON):
    """@Service - 서비스 레이어"""
    return component(scope=scope)

def repository(scope: Scope = Scope.SINGLETON):
    """@Repository - 데이터 접근 레이어"""
    return component(scope=scope)

def controller(scope: Scope = Scope.SINGLETON):
    """@Controller - 컨트롤러 레이어"""
    return component(scope=scope)

class AutowiredDescriptor:
    """@Autowired 필드 디스크립터"""
    def __init__(self, field_type: Type):
        self.field_type = field_type
        self.field_name = None

    def __set_name__(self, owner, name):
        self.field_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if not hasattr(instance, self.field_name):
            # lazy 주입
            value = ApplicationContext.get_bean(self.field_type)
            setattr(instance, self.field_name, value)

        return getattr(instance, self.field_name)

    def __set__(self, instance, value):
        setattr(instance, self.field_name, value)

def autowired(field_type: Type):
    """@Autowired - 자동 주입 필드"""
    return AutowiredDescriptor(field_type)

# FastAPI 통합을 위한 헬퍼
def get_component(component_type: Type):
    """FastAPI Depends와 함께 사용할 헬퍼 함수"""
    return ApplicationContext.get_bean(component_type)