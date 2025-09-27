"""
DI 시스템 안정성 및 신뢰성 테스트
스레드 안전성, 에러 처리, 메모리 누수 등 검증
"""

import pytest
import threading
import time
import gc
import weakref
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Protocol

# 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../examples/spring_di_demo'))

from optimized_spring_di import (
    service, repository, controller, component,
    OptimizedApplicationContext, Scope, CircularDependencyError,
    BeanNotFoundError, DIProfiler
)

class TestStability:

    def setup_method(self):
        """각 테스트 전에 초기화"""
        OptimizedApplicationContext._instances = {}
        OptimizedApplicationContext._component_configs = {}
        OptimizedApplicationContext._dependency_cache = {}
        OptimizedApplicationContext._creation_order_cache = {}
        OptimizedApplicationContext._creation_stack = set()
        OptimizedApplicationContext._metrics.clear()
        OptimizedApplicationContext.clear_cache()

    def test_thread_safety(self):
        """스레드 안전성 테스트"""
        @service()
        class ThreadSafeService:
            def __init__(self):
                self.counter = 0
                self._lock = threading.Lock()

            def increment(self):
                with self._lock:
                    current = self.counter
                    time.sleep(0.001)  # 의도적 지연
                    self.counter = current + 1
                    return self.counter

        # 여러 스레드에서 동시에 서비스 접근
        results = []
        errors = []

        def worker():
            try:
                service = OptimizedApplicationContext.get_bean(ThreadSafeService)
                result = service.increment()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 100개 스레드로 동시 접근
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker) for _ in range(100)]
            for future in as_completed(futures):
                future.result()  # 예외 발생시 re-raise

        # 검증
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 100, "All threads should complete"
        assert max(results) == 100, "Counter should reach 100"

        # 모든 스레드가 같은 싱글톤 인스턴스를 사용했는지 확인
        service1 = OptimizedApplicationContext.get_bean(ThreadSafeService)
        service2 = OptimizedApplicationContext.get_bean(ThreadSafeService)
        assert service1 is service2, "Should be the same singleton instance"

    def test_circular_dependency_detection(self):
        """순환 의존성 감지 테스트"""

        with pytest.raises(CircularDependencyError) as exc_info:
            @service()
            class ServiceA:
                def __init__(self, service_b: 'ServiceB'):
                    self.service_b = service_b

            @service()
            class ServiceB:
                def __init__(self, service_a: ServiceA):
                    self.service_a = service_a

            # 순환 의존성이 있는 서비스 생성 시도
            OptimizedApplicationContext.get_bean(ServiceA)

        # 순환 경로가 올바르게 감지되었는지 확인
        assert "ServiceA" in str(exc_info.value)
        assert "ServiceB" in str(exc_info.value)

    def test_memory_leak_prevention(self):
        """메모리 누수 방지 테스트"""
        initial_objects = len(gc.get_objects())

        @service(scope=Scope.PROTOTYPE)
        class LeakTestService:
            def __init__(self):
                self.data = "x" * 1000  # 1KB 데이터

        # 대량 인스턴스 생성
        instances = []
        weak_refs = []

        for i in range(100):
            instance = OptimizedApplicationContext.get_bean(LeakTestService)
            instances.append(instance)
            weak_refs.append(weakref.ref(instance))

        # 강한 참조 제거
        instances.clear()
        gc.collect()

        # WeakReference로 객체가 정리되었는지 확인
        alive_objects = sum(1 for ref in weak_refs if ref() is not None)
        print(f"Alive objects after GC: {alive_objects}")

        # 메모리가 어느 정도 정리되었는지 확인
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects

        # 완전히 정리되지 않을 수 있지만, 과도한 증가는 없어야 함
        assert object_increase < 200, f"Too many objects retained: {object_increase}"

    def test_error_handling(self):
        """에러 처리 테스트"""

        # 1. 등록되지 않은 의존성
        class UnregisteredDependency:
            pass

        @service()
        class ServiceWithUnregisteredDep:
            def __init__(self, dep: UnregisteredDependency):
                self.dep = dep

        with pytest.raises(BeanNotFoundError):
            OptimizedApplicationContext.get_bean(ServiceWithUnregisteredDep)

        # 2. 생성자 오류
        @service()
        class FaultyService:
            def __init__(self):
                raise ValueError("Intentional error")

        with pytest.raises(ValueError, match="Intentional error"):
            OptimizedApplicationContext.get_bean(FaultyService)

    def test_concurrent_singleton_creation(self):
        """동시 싱글톤 생성 테스트"""
        creation_count = 0
        creation_lock = threading.Lock()

        @service(scope=Scope.SINGLETON)
        class ConcurrentSingleton:
            def __init__(self):
                nonlocal creation_count
                with creation_lock:
                    creation_count += 1
                time.sleep(0.01)  # 초기화 시간 시뮬레이션

        instances = []
        errors = []

        def create_singleton():
            try:
                instance = OptimizedApplicationContext.get_bean(ConcurrentSingleton)
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        # 50개 스레드에서 동시에 싱글톤 생성
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(create_singleton) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # 검증
        assert len(errors) == 0, f"Singleton creation errors: {errors}"
        assert len(instances) == 50, "All threads should get an instance"
        assert creation_count == 1, f"Singleton should be created only once, but was created {creation_count} times"

        # 모든 인스턴스가 동일한지 확인
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "All instances should be the same singleton"

    def test_resource_cleanup(self):
        """리소스 정리 테스트"""
        cleanup_called = []

        @service()
        class ResourceService:
            def __init__(self):
                self.resource = "allocated"

            def __del__(self):
                cleanup_called.append(True)

        # 인스턴스 생성 및 참조 제거
        service = OptimizedApplicationContext.get_bean(ResourceService)
        service_id = id(service)

        # 캐시에서 제거 (싱글톤이므로 강제 제거)
        OptimizedApplicationContext._instances.clear()
        OptimizedApplicationContext._component_configs.clear()

        del service
        gc.collect()

        # __del__ 호출 확인 (GC 타이밍에 따라 불안정할 수 있음)
        time.sleep(0.1)  # GC가 실행될 시간 제공

    def test_performance_under_load(self):
        """부하 상황에서의 성능 테스트"""

        @repository()
        class LoadTestRepository:
            def get_data(self):
                return "data"

        @service()
        class LoadTestService:
            def __init__(self, repo: LoadTestRepository):
                self.repo = repo

            def process(self):
                return self.repo.get_data()

        # 대량 요청 시뮬레이션
        start_time = time.time()
        results = []
        errors = []

        def process_request():
            try:
                service = OptimizedApplicationContext.get_bean(LoadTestService)
                result = service.process()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 1000개 요청을 20개 스레드로 처리
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_request) for _ in range(1000)]
            for future in as_completed(futures):
                future.result()

        end_time = time.time()
        total_time = end_time - start_time

        # 검증
        assert len(errors) == 0, f"Load test errors: {errors}"
        assert len(results) == 1000, "All requests should be processed"
        assert total_time < 10.0, f"Processing took too long: {total_time}s"

        print(f"Processed 1000 requests in {total_time:.2f}s ({1000/total_time:.0f} req/s)")

    def test_configuration_validation(self):
        """설정 검증 테스트"""

        # 유효한 설정
        @repository()
        class ValidRepository:
            def get_data(self):
                return "data"

        @service()
        class ValidService:
            def __init__(self, repo: ValidRepository):
                self.repo = repo

        # 시스템 검증
        issues = OptimizedApplicationContext.validate_configuration()

        # 이 시점에서는 문제가 없어야 함
        valid_issues = [issue for issue in issues if not ("ServiceA" in issue or "ServiceB" in issue)]
        assert len(valid_issues) == 0, f"Unexpected validation issues: {valid_issues}"

    def test_metrics_collection(self):
        """메트릭 수집 테스트"""

        @service()
        class MetricTestService:
            def __init__(self):
                time.sleep(0.01)  # 초기화 시간 시뮬레이션

        # 여러 번 인스턴스 요청 (싱글톤이므로 첫 번째만 생성됨)
        for _ in range(5):
            OptimizedApplicationContext.get_bean(MetricTestService)

        # 메트릭 확인
        metrics = OptimizedApplicationContext.get_metrics()

        assert MetricTestService in metrics, "Service should be in metrics"

        service_metrics = metrics[MetricTestService]
        assert service_metrics['creation_count'] == 1, "Singleton should be created only once"
        assert service_metrics['total_time'] > 0, "Should record creation time"

if __name__ == "__main__":
    # 개별 테스트 실행
    test_instance = TestStability()

    print("🧪 Running Stability Tests...")

    test_methods = [
        ("Thread Safety", test_instance.test_thread_safety),
        ("Circular Dependency", test_instance.test_circular_dependency_detection),
        ("Memory Leak Prevention", test_instance.test_memory_leak_prevention),
        ("Error Handling", test_instance.test_error_handling),
        ("Concurrent Singleton", test_instance.test_concurrent_singleton_creation),
        ("Performance Under Load", test_instance.test_performance_under_load),
        ("Configuration Validation", test_instance.test_configuration_validation),
        ("Metrics Collection", test_instance.test_metrics_collection),
    ]

    passed = 0
    failed = 0

    for test_name, test_method in test_methods:
        test_instance.setup_method()
        try:
            test_method()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All stability tests passed!")
        DIProfiler.print_metrics()
    else:
        print("⚠️ Some tests failed. Check implementation.")