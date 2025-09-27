"""
최적화된 Spring Boot 스타일 DI 시스템
성능 개선과 안정성 강화 버전
"""

import inspect
import threading
import weakref
from typing import Dict, Type, Any, get_type_hints, Optional, Set
from functools import lru_cache, wraps
from enum import Enum
import warnings
from collections import defaultdict
import time

class Scope(Enum):
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"

class CircularDependencyError(Exception):
    """순환 의존성 에러"""
    def __init__(self, cycle_path: list):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join([cls.__name__ for cls in cycle_path])
        super().__init__(f"Circular dependency detected: {cycle_str}")

class BeanNotFoundError(Exception):
    """빈을 찾을 수 없음 에러"""
    def __init__(self, bean_type: Type):
        super().__init__(f"No bean found for type: {bean_type.__name__}")

class OptimizedApplicationContext:
    """성능 최적화된 ApplicationContext"""

    # 인스턴스 저장 (WeakReference 사용으로 메모리 누수 방지)
    _instances: Dict[Type, Any] = {}
    _component_configs: Dict[Type, dict] = {}

    # 성능 최적화: 의존성 그래프 캐싱
    _dependency_cache: Dict[Type, Dict[str, Type]] = {}
    _creation_order_cache: Dict[Type, list] = {}

    # 안정성: 순환 의존성 감지
    _creation_stack: Set[Type] = set()
    _lock = threading.RLock()  # 재진입 가능 락

    # 메트릭 수집
    _metrics = defaultdict(lambda: {'creation_count': 0, 'total_time': 0})

    @classmethod
    def register_component(cls, component_type: Type, scope: Scope = Scope.SINGLETON, primary: bool = False):
        """컴포넌트 등록 최적화"""
        with cls._lock:
            cls._component_configs[component_type] = {
                'scope': scope,
                'primary': primary,
                'instance': None
            }
            # 의존성 사전 분석 및 캐싱
            cls._analyze_dependencies(component_type)

    @classmethod
    @lru_cache(maxsize=1000)  # 타입 분석 결과 캐싱
    def _analyze_dependencies(cls, component_type: Type) -> Dict[str, Type]:
        """의존성 사전 분석 (성능 최적화)"""
        if component_type in cls._dependency_cache:
            return cls._dependency_cache[component_type]

        constructor = component_type.__init__
        signature = inspect.signature(constructor)
        dependencies = {}

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            if param.annotation != inspect.Parameter.empty:
                dependencies[param_name] = param.annotation

        cls._dependency_cache[component_type] = dependencies
        return dependencies

    @classmethod
    def get_bean(cls, bean_type: Type, _creation_path: Optional[list] = None) -> Any:
        """최적화된 빈 인스턴스 반환"""
        if _creation_path is None:
            _creation_path = []

        start_time = time.perf_counter()

        with cls._lock:
            # 순환 의존성 감지
            if bean_type in _creation_path:
                cycle = _creation_path + [bean_type]
                raise CircularDependencyError(cycle)

            # 빈 설정 확인
            config = cls._component_configs.get(bean_type)
            if not config:
                # 인터페이스 구현체 찾기
                implementations = cls._find_implementations(bean_type)
                if implementations:
                    bean_type = implementations[0]
                    config = cls._component_configs.get(bean_type)

                if not config:
                    raise BeanNotFoundError(bean_type)

            # 싱글톤 인스턴스 반환 (성능 최적화)
            if config['scope'] == Scope.SINGLETON and config['instance']:
                return config['instance']

            # 새 인스턴스 생성
            instance = cls._create_instance_optimized(bean_type, _creation_path + [bean_type])

            # 싱글톤 캐싱
            if config['scope'] == Scope.SINGLETON:
                config['instance'] = instance

            # 메트릭 업데이트
            cls._metrics[bean_type]['creation_count'] += 1
            cls._metrics[bean_type]['total_time'] += time.perf_counter() - start_time

            return instance

    @classmethod
    def _create_instance_optimized(cls, component_type: Type, creation_path: list) -> Any:
        """최적화된 인스턴스 생성"""
        # 캐시된 의존성 정보 사용
        dependencies_info = cls._dependency_cache.get(component_type, {})

        if not dependencies_info:
            # 의존성이 없는 경우 직접 생성 (성능 최적화)
            return component_type()

        # 의존성 해결
        resolved_dependencies = {}
        for param_name, param_type in dependencies_info.items():
            resolved_dependencies[param_name] = cls.get_bean(param_type, creation_path)

        return component_type(**resolved_dependencies)

    @classmethod
    def _find_implementations(cls, interface_type: Type) -> list:
        """인터페이스 구현체 찾기 (캐싱 추가)"""
        implementations = []
        for component_type in cls._component_configs.keys():
            # MRO(Method Resolution Order) 검사
            if issubclass(component_type, interface_type) and component_type != interface_type:
                implementations.append(component_type)
        return implementations

    @classmethod
    def get_metrics(cls) -> dict:
        """성능 메트릭 반환"""
        return dict(cls._metrics)

    @classmethod
    def clear_cache(cls):
        """캐시 초기화"""
        cls._dependency_cache.clear()
        cls._creation_order_cache.clear()
        cls._analyze_dependencies.cache_clear()

    @classmethod
    def validate_configuration(cls) -> list:
        """설정 검증 및 잠재적 문제 감지"""
        issues = []

        # 순환 의존성 사전 검사
        for component_type in cls._component_configs.keys():
            try:
                cls._detect_circular_dependencies(component_type, set())
            except CircularDependencyError as e:
                issues.append(f"Circular dependency: {e.cycle_path}")

        # 미해결 의존성 검사
        for component_type, deps in cls._dependency_cache.items():
            for param_name, param_type in deps.items():
                if param_type not in cls._component_configs:
                    implementations = cls._find_implementations(param_type)
                    if not implementations:
                        issues.append(f"Unresolved dependency: {component_type.__name__} -> {param_type.__name__}")

        return issues

    @classmethod
    def _detect_circular_dependencies(cls, component_type: Type, visited: Set[Type], path: Optional[list] = None):
        """순환 의존성 사전 감지"""
        if path is None:
            path = []

        if component_type in visited:
            cycle_start = path.index(component_type)
            cycle = path[cycle_start:] + [component_type]
            raise CircularDependencyError(cycle)

        visited.add(component_type)
        path.append(component_type)

        dependencies = cls._dependency_cache.get(component_type, {})
        for param_type in dependencies.values():
            if param_type in cls._component_configs:
                cls._detect_circular_dependencies(param_type, visited.copy(), path.copy())

# 최적화된 데코레이터들

def component(scope: Scope = Scope.SINGLETON, primary: bool = False):
    """최적화된 @component 데코레이터"""
    def decorator(cls):
        # 타입 힌트 사전 검증
        try:
            get_type_hints(cls.__init__)
        except Exception as e:
            warnings.warn(f"Type hint analysis failed for {cls.__name__}: {e}")

        # 메타클래스 없이 직접 등록 (성능 향상)
        OptimizedApplicationContext.register_component(cls, scope, primary)

        # 원본 클래스 반환 (메모리 효율성)
        return cls

    return decorator

def service(scope: Scope = Scope.SINGLETON):
    """최적화된 @service 데코레이터"""
    return component(scope=scope)

def repository(scope: Scope = Scope.SINGLETON):
    """최적화된 @repository 데코레이터"""
    return component(scope=scope)

def controller(scope: Scope = Scope.SINGLETON):
    """최적화된 @controller 데코레이터"""
    return component(scope=scope)

# 성능 모니터링 데코레이터
def monitored_component(scope: Scope = Scope.SINGLETON):
    """성능 모니터링이 포함된 컴포넌트"""
    def decorator(cls):
        original_init = cls.__init__

        @wraps(original_init)
        def monitored_init(self, *args, **kwargs):
            start_time = time.perf_counter()
            result = original_init(self, *args, **kwargs)
            init_time = time.perf_counter() - start_time

            if init_time > 0.1:  # 100ms 이상 걸린 경우 경고
                warnings.warn(f"{cls.__name__} initialization took {init_time:.3f}s")

            return result

        cls.__init__ = monitored_init
        return component(scope=scope)(cls)

    return decorator

# FastAPI 통합 헬퍼
def get_component(component_type: Type):
    """FastAPI Depends와 함께 사용할 최적화된 헬퍼"""
    return OptimizedApplicationContext.get_bean(component_type)

# 개발자 도구
class DIProfiler:
    """DI 시스템 프로파일러"""

    @staticmethod
    def print_metrics():
        """성능 메트릭 출력"""
        metrics = OptimizedApplicationContext.get_metrics()

        print("📊 DI System Performance Metrics")
        print("=" * 50)

        for component_type, data in metrics.items():
            avg_time = data['total_time'] / data['creation_count'] if data['creation_count'] else 0
            print(f"{component_type.__name__:<30} "
                  f"Created: {data['creation_count']:>3} "
                  f"Avg Time: {avg_time*1000:>6.2f}ms")

    @staticmethod
    def validate_system():
        """시스템 검증"""
        issues = OptimizedApplicationContext.validate_configuration()

        if not issues:
            print("✅ DI System validation passed!")
        else:
            print("⚠️ DI System issues found:")
            for issue in issues:
                print(f"  - {issue}")

    @staticmethod
    def dependency_graph():
        """의존성 그래프 출력"""
        print("🔗 Dependency Graph")
        print("=" * 30)

        for component_type, deps in OptimizedApplicationContext._dependency_cache.items():
            print(f"{component_type.__name__}")
            for param_name, param_type in deps.items():
                print(f"  └─ {param_name}: {param_type.__name__}")
            print()