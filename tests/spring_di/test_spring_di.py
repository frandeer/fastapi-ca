"""
Spring Boot Style DI 시스템 테스트
"""

import pytest
import sys
import os

# 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../examples/spring_di_demo'))

from spring_di import (
    service, repository, controller, component, autowired,
    ApplicationContext, Scope
)
from typing import Protocol

class TestSpringDI:

    def setup_method(self):
        """각 테스트 전에 ApplicationContext 초기화"""
        ApplicationContext._components = {}
        ApplicationContext._component_configs = {}

    def test_component_registration(self):
        """컴포넌트 등록 테스트"""
        @component()
        class TestComponent:
            def get_message(self):
                return "Hello from component"

        # 컴포넌트가 등록되었는지 확인
        assert TestComponent in ApplicationContext._component_configs

        # 인스턴스 생성 테스트
        instance = ApplicationContext.get_bean(TestComponent)
        assert instance.get_message() == "Hello from component"

    def test_constructor_injection(self):
        """생성자 의존성 주입 테스트"""
        @repository()
        class TestRepository:
            def get_data(self):
                return "data from repository"

        @service()
        class TestService:
            def __init__(self, repo: TestRepository):
                self.repo = repo

            def process(self):
                return f"processed: {self.repo.get_data()}"

        # 서비스 인스턴스 생성 (의존성 자동 주입)
        service_instance = ApplicationContext.get_bean(TestService)
        result = service_instance.process()

        assert result == "processed: data from repository"

    def test_field_injection(self):
        """필드 의존성 주입 테스트"""
        @service()
        class DependencyService:
            def get_value(self):
                return "injected value"

        @service()
        class TestService:
            dependency: DependencyService = autowired(DependencyService)

            def use_dependency(self):
                return self.dependency.get_value()

        # 서비스 인스턴스 생성
        service_instance = ApplicationContext.get_bean(TestService)
        result = service_instance.use_dependency()

        assert result == "injected value"

    def test_interface_injection(self):
        """인터페이스 기반 의존성 주입 테스트"""
        class IDataSource(Protocol):
            def get_data(self) -> str:
                ...

        @repository()
        class DatabaseDataSource(IDataSource):
            def get_data(self) -> str:
                return "database data"

        @service()
        class DataProcessor:
            def __init__(self, data_source: IDataSource):
                self.data_source = data_source

            def process(self):
                return f"processing: {self.data_source.get_data()}"

        # 인터페이스로 의존성 주입
        processor = ApplicationContext.get_bean(DataProcessor)
        result = processor.process()

        assert result == "processing: database data"

    def test_singleton_scope(self):
        """싱글톤 스코프 테스트"""
        @service(scope=Scope.SINGLETON)
        class SingletonService:
            def __init__(self):
                self.counter = 0

            def increment(self):
                self.counter += 1
                return self.counter

        # 두 번 호출해서 같은 인스턴스인지 확인
        service1 = ApplicationContext.get_bean(SingletonService)
        service2 = ApplicationContext.get_bean(SingletonService)

        assert service1 is service2  # 같은 인스턴스

        # 상태 공유 확인
        assert service1.increment() == 1
        assert service2.increment() == 2  # 같은 인스턴스이므로 counter가 증가

    def test_prototype_scope(self):
        """프로토타입 스코프 테스트"""
        @service(scope=Scope.PROTOTYPE)
        class PrototypeService:
            def __init__(self):
                self.counter = 0

            def increment(self):
                self.counter += 1
                return self.counter

        # 두 번 호출해서 다른 인스턴스인지 확인
        service1 = ApplicationContext.get_bean(PrototypeService)
        service2 = ApplicationContext.get_bean(PrototypeService)

        assert service1 is not service2  # 다른 인스턴스

        # 상태 독립성 확인
        assert service1.increment() == 1
        assert service2.increment() == 1  # 다른 인스턴스이므로 독립적

    def test_complex_dependency_chain(self):
        """복잡한 의존성 체인 테스트"""
        @repository()
        class DataRepository:
            def get_raw_data(self):
                return "raw_data"

        @service()
        class DataTransformer:
            def __init__(self, repo: DataRepository):
                self.repo = repo

            def transform(self):
                return f"transformed_{self.repo.get_raw_data()}"

        @service()
        class BusinessLogic:
            def __init__(self, transformer: DataTransformer):
                self.transformer = transformer

            def execute(self):
                return f"business_{self.transformer.transform()}"

        @controller()
        class ApiController:
            def __init__(self, business: BusinessLogic):
                self.business = business

            def handle_request(self):
                return f"response_{self.business.execute()}"

        # 깊은 의존성 체인이 올바르게 해결되는지 테스트
        controller = ApplicationContext.get_bean(ApiController)
        result = controller.handle_request()

        assert result == "response_business_transformed_raw_data"

    def test_missing_dependency(self):
        """등록되지 않은 의존성 테스트"""
        class UnregisteredDependency:
            pass

        @service()
        class ServiceWithMissingDep:
            def __init__(self, dep: UnregisteredDependency):
                self.dep = dep

        # 등록되지 않은 의존성으로 인한 예외 발생
        with pytest.raises(ValueError, match="No bean found for type"):
            ApplicationContext.get_bean(ServiceWithMissingDep)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])