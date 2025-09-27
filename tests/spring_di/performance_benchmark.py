"""
DI 시스템 성능 벤치마크 테스트
성능, 메모리 사용량, 확장성 분석
"""

import time
import sys
import os
import tracemalloc
import gc
from typing import Protocol

# 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../examples/spring_di_demo'))

from spring_di import (
    service, repository, controller, component, autowired,
    ApplicationContext, Scope
)

# dependency-injector와 비교
try:
    from dependency_injector import containers, providers
    from dependency_injector.wiring import inject, Provide
    HAS_DEPENDENCY_INJECTOR = True
except ImportError:
    HAS_DEPENDENCY_INJECTOR = False

# FastAPI 기본 Depends와 비교
from fastapi import Depends

class PerformanceBenchmark:

    def __init__(self):
        self.results = {}

    def measure_time_and_memory(self, func, *args, **kwargs):
        """시간과 메모리 사용량 측정"""
        # 메모리 추적 시작
        tracemalloc.start()
        gc.collect()  # 가비지 컬렉션 실행

        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        # 메모리 사용량 측정
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            'result': result,
            'time': end_time - start_time,
            'memory_current': current / 1024 / 1024,  # MB
            'memory_peak': peak / 1024 / 1024,  # MB
        }

    def benchmark_spring_di_creation(self, iterations=1000):
        """Spring DI 시스템 인스턴스 생성 성능"""

        # 테스트 컴포넌트 정의
        @repository()
        class BenchmarkRepository:
            def get_data(self):
                return "data"

        @service()
        class BenchmarkService:
            def __init__(self, repo: BenchmarkRepository):
                self.repo = repo

            def process(self):
                return self.repo.get_data()

        def create_instances():
            instances = []
            for _ in range(iterations):
                service = ApplicationContext.get_bean(BenchmarkService)
                instances.append(service.process())
            return len(instances)

        result = self.measure_time_and_memory(create_instances)
        self.results['spring_di_creation'] = {
            'iterations': iterations,
            'time_per_iteration': result['time'] / iterations * 1000,  # ms
            'total_time': result['time'],
            'memory_current': result['memory_current'],
            'memory_peak': result['memory_peak']
        }

    def benchmark_dependency_injector(self, iterations=1000):
        """dependency-injector와 비교"""
        if not HAS_DEPENDENCY_INJECTOR:
            self.results['dependency_injector'] = {'error': 'dependency-injector not installed'}
            return

        # dependency-injector 버전
        class Repository:
            def get_data(self):
                return "data"

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def process(self):
                return self.repo.get_data()

        class Container(containers.DeclarativeContainer):
            repo = providers.Factory(Repository)
            service = providers.Factory(Service, repo=repo)

        container = Container()

        def create_instances():
            instances = []
            for _ in range(iterations):
                service = container.service()
                instances.append(service.process())
            return len(instances)

        result = self.measure_time_and_memory(create_instances)
        self.results['dependency_injector'] = {
            'iterations': iterations,
            'time_per_iteration': result['time'] / iterations * 1000,  # ms
            'total_time': result['time'],
            'memory_current': result['memory_current'],
            'memory_peak': result['memory_peak']
        }

    def benchmark_fastapi_depends(self, iterations=1000):
        """FastAPI 기본 Depends와 비교"""

        class Repository:
            def get_data(self):
                return "data"

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def process(self):
                return self.repo.get_data()

        def get_repository():
            return Repository()

        def get_service(repo: Repository = Depends(get_repository)):
            return Service(repo)

        def create_instances():
            instances = []
            for _ in range(iterations):
                # FastAPI Depends는 실제로는 프레임워크가 호출하지만
                # 여기서는 직접 호출로 시뮬레이션
                repo = get_repository()
                service = Service(repo)
                instances.append(service.process())
            return len(instances)

        result = self.measure_time_and_memory(create_instances)
        self.results['fastapi_depends'] = {
            'iterations': iterations,
            'time_per_iteration': result['time'] / iterations * 1000,  # ms
            'total_time': result['time'],
            'memory_current': result['memory_current'],
            'memory_peak': result['memory_peak']
        }

    def benchmark_manual_creation(self, iterations=1000):
        """수동 인스턴스 생성과 비교 (베이스라인)"""

        class Repository:
            def get_data(self):
                return "data"

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def process(self):
                return self.repo.get_data()

        def create_instances():
            instances = []
            for _ in range(iterations):
                repo = Repository()
                service = Service(repo)
                instances.append(service.process())
            return len(instances)

        result = self.measure_time_and_memory(create_instances)
        self.results['manual_creation'] = {
            'iterations': iterations,
            'time_per_iteration': result['time'] / iterations * 1000,  # ms
            'total_time': result['time'],
            'memory_current': result['memory_current'],
            'memory_peak': result['memory_peak']
        }

    def benchmark_singleton_vs_prototype(self, iterations=1000):
        """싱글톤 vs 프로토타입 스코프 성능 비교"""

        @service(scope=Scope.SINGLETON)
        class SingletonService:
            def __init__(self):
                self.data = "singleton_data"

            def get_data(self):
                return self.data

        @service(scope=Scope.PROTOTYPE)
        class PrototypeService:
            def __init__(self):
                self.data = "prototype_data"

            def get_data(self):
                return self.data

        def test_singleton():
            results = []
            for _ in range(iterations):
                service = ApplicationContext.get_bean(SingletonService)
                results.append(service.get_data())
            return len(results)

        def test_prototype():
            results = []
            for _ in range(iterations):
                service = ApplicationContext.get_bean(PrototypeService)
                results.append(service.get_data())
            return len(results)

        singleton_result = self.measure_time_and_memory(test_singleton)
        prototype_result = self.measure_time_and_memory(test_prototype)

        self.results['singleton_scope'] = {
            'iterations': iterations,
            'time_per_iteration': singleton_result['time'] / iterations * 1000,
            'total_time': singleton_result['time'],
            'memory_current': singleton_result['memory_current'],
            'memory_peak': singleton_result['memory_peak']
        }

        self.results['prototype_scope'] = {
            'iterations': iterations,
            'time_per_iteration': prototype_result['time'] / iterations * 1000,
            'total_time': prototype_result['time'],
            'memory_current': prototype_result['memory_current'],
            'memory_peak': prototype_result['memory_peak']
        }

    def benchmark_deep_dependency_chain(self, iterations=100):
        """깊은 의존성 체인 성능"""

        @repository()
        class Layer1:
            def get_data(self): return "layer1"

        @service()
        class Layer2:
            def __init__(self, layer1: Layer1): self.layer1 = layer1
            def get_data(self): return f"{self.layer1.get_data()}_layer2"

        @service()
        class Layer3:
            def __init__(self, layer2: Layer2): self.layer2 = layer2
            def get_data(self): return f"{self.layer2.get_data()}_layer3"

        @service()
        class Layer4:
            def __init__(self, layer3: Layer3): self.layer3 = layer3
            def get_data(self): return f"{self.layer3.get_data()}_layer4"

        @service()
        class Layer5:
            def __init__(self, layer4: Layer4): self.layer4 = layer4
            def get_data(self): return f"{self.layer4.get_data()}_layer5"

        def test_deep_chain():
            results = []
            for _ in range(iterations):
                service = ApplicationContext.get_bean(Layer5)
                results.append(service.get_data())
            return len(results)

        result = self.measure_time_and_memory(test_deep_chain)
        self.results['deep_dependency_chain'] = {
            'iterations': iterations,
            'time_per_iteration': result['time'] / iterations * 1000,
            'total_time': result['time'],
            'memory_current': result['memory_current'],
            'memory_peak': result['memory_peak']
        }

    def run_all_benchmarks(self):
        """모든 벤치마크 실행"""
        print("🚀 DI 시스템 성능 벤치마크 시작...")

        # ApplicationContext 초기화
        ApplicationContext._components = {}
        ApplicationContext._component_configs = {}

        benchmarks = [
            ("Spring DI Creation", self.benchmark_spring_di_creation),
            ("Dependency Injector", self.benchmark_dependency_injector),
            ("FastAPI Depends", self.benchmark_fastapi_depends),
            ("Manual Creation", self.benchmark_manual_creation),
            ("Singleton vs Prototype", self.benchmark_singleton_vs_prototype),
            ("Deep Dependency Chain", self.benchmark_deep_dependency_chain),
        ]

        for name, benchmark in benchmarks:
            print(f"⏱️  {name} 벤치마크 실행 중...")
            try:
                benchmark()
                print(f"✅ {name} 완료")
            except Exception as e:
                print(f"❌ {name} 실패: {e}")
                self.results[name.lower().replace(' ', '_')] = {'error': str(e)}

        return self.results

    def print_results(self):
        """결과 출력"""
        print("\n" + "="*80)
        print("📊 DI 시스템 성능 벤치마크 결과")
        print("="*80)

        for name, result in self.results.items():
            if 'error' in result:
                print(f"\n❌ {name.upper()}: {result['error']}")
                continue

            print(f"\n📈 {name.upper().replace('_', ' ')}")
            print(f"   반복 횟수: {result.get('iterations', 'N/A')}")
            print(f"   반복당 시간: {result.get('time_per_iteration', 0):.4f} ms")
            print(f"   총 시간: {result.get('total_time', 0):.4f} s")
            print(f"   메모리 사용: {result.get('memory_current', 0):.2f} MB")
            print(f"   최대 메모리: {result.get('memory_peak', 0):.2f} MB")

    def performance_comparison_table(self):
        """성능 비교 테이블"""
        print("\n" + "="*100)
        print("🏁 성능 비교 테이블 (1000회 반복 기준)")
        print("="*100)
        print(f"{'방식':<25} {'반복당 시간(ms)':<15} {'총 시간(s)':<12} {'메모리(MB)':<12} {'상대 성능':<10}")
        print("-" * 100)

        baseline_time = self.results.get('manual_creation', {}).get('time_per_iteration', 1)

        methods = [
            ('Manual Creation', 'manual_creation'),
            ('FastAPI Depends', 'fastapi_depends'),
            ('Spring DI', 'spring_di_creation'),
            ('Dependency Injector', 'dependency_injector'),
        ]

        for display_name, key in methods:
            if key in self.results and 'error' not in self.results[key]:
                result = self.results[key]
                time_per_iter = result.get('time_per_iteration', 0)
                total_time = result.get('total_time', 0)
                memory = result.get('memory_current', 0)
                relative_perf = f"{time_per_iter / baseline_time:.2f}x"

                print(f"{display_name:<25} {time_per_iter:<15.4f} {total_time:<12.4f} {memory:<12.2f} {relative_perf:<10}")

if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    results = benchmark.run_all_benchmarks()
    benchmark.print_results()
    benchmark.performance_comparison_table()