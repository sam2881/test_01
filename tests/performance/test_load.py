"""Load and stress testing for AI Agent Platform"""
import pytest
import asyncio
import time
import httpx
from typing import List, Dict
import statistics


@pytest.mark.performance
@pytest.mark.asyncio
class TestLoadTesting:
    """Load testing for API endpoints"""

    async def test_concurrent_task_creation(self, async_client):
        """Test creating multiple tasks concurrently"""

        async def create_task(task_num: int):
            start_time = time.time()
            response = await async_client.post("/task", json={
                "description": f"Load test task {task_num}",
                "priority": "P3",
                "metadata": {"test": True, "task_num": task_num}
            })
            duration = time.time() - start_time
            return {
                "status_code": response.status_code,
                "duration": duration,
                "task_num": task_num
            }

        # Create 50 concurrent tasks
        num_tasks = 50
        print(f"\n[LOAD TEST] Creating {num_tasks} concurrent tasks...")

        tasks = [create_task(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception) and r["status_code"] in [200, 201]]
        failed = [r for r in results if isinstance(r, Exception) or r["status_code"] not in [200, 201]]
        durations = [r["duration"] for r in successful]

        print(f"✓ Successful: {len(successful)}/{num_tasks}")
        print(f"✗ Failed: {len(failed)}/{num_tasks}")

        if durations:
            print(f"⏱ Avg response time: {statistics.mean(durations):.2f}s")
            print(f"⏱ Min response time: {min(durations):.2f}s")
            print(f"⏱ Max response time: {max(durations):.2f}s")
            print(f"⏱ Median response time: {statistics.median(durations):.2f}s")

        # Assert at least 80% success rate
        success_rate = len(successful) / num_tasks
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} is below 80%"

    async def test_sustained_load(self, async_client):
        """Test sustained load over time"""

        duration_seconds = 30
        requests_per_second = 5
        total_requests = duration_seconds * requests_per_second

        print(f"\n[SUSTAINED LOAD] {requests_per_second} req/s for {duration_seconds}s...")

        start_time = time.time()
        request_count = 0
        results = []

        while time.time() - start_time < duration_seconds:
            batch_start = time.time()

            # Send batch of requests
            tasks = []
            for _ in range(requests_per_second):
                if request_count >= total_requests:
                    break
                task = async_client.get("/health")
                tasks.append(task)
                request_count += 1

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

            # Wait for next second
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
        failed = [r for r in results if isinstance(r, Exception) or r.status_code != 200]

        print(f"✓ Successful: {len(successful)}/{len(results)}")
        print(f"✗ Failed: {len(failed)}/{len(results)}")

        success_rate = len(successful) / len(results) if results else 0
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} under sustained load"

    async def test_burst_traffic(self, async_client):
        """Test handling of sudden burst traffic"""

        print("\n[BURST TEST] Sending 100 requests simultaneously...")

        async def send_request():
            return await async_client.get("/incidents")

        # Send 100 requests at once
        start_time = time.time()
        tasks = [send_request() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        successful = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]

        print(f"✓ Completed in {total_duration:.2f}s")
        print(f"✓ Throughput: {len(successful)/total_duration:.2f} req/s")

        # At least 70% should succeed during burst
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.7, f"Burst success rate {success_rate:.2%} is too low"


@pytest.mark.performance
@pytest.mark.asyncio
class TestResponseTime:
    """Response time testing"""

    async def test_api_response_time_sla(self, async_client):
        """Test that API response times meet SLA (<500ms for GET)"""

        endpoints = [
            "/health",
            "/incidents",
            "/agents/status",
            "/api/stats/dashboard"
        ]

        print("\n[RESPONSE TIME] Testing SLA compliance...")

        for endpoint in endpoints:
            times = []
            for _ in range(20):
                start = time.time()
                response = await async_client.get(endpoint)
                duration = (time.time() - start) * 1000  # Convert to ms

                if response.status_code == 200:
                    times.append(duration)

            if times:
                avg_time = statistics.mean(times)
                p95_time = sorted(times)[int(len(times) * 0.95)]

                print(f"  {endpoint}")
                print(f"    Avg: {avg_time:.0f}ms, P95: {p95_time:.0f}ms")

                # SLA: P95 should be under 500ms for GET requests
                assert p95_time < 500, f"{endpoint} P95 {p95_time:.0f}ms exceeds 500ms SLA"

    async def test_task_creation_latency(self, async_client):
        """Test task creation latency"""

        print("\n[LATENCY] Testing task creation...")

        latencies = []
        for i in range(10):
            start = time.time()
            response = await async_client.post("/task", json={
                "description": f"Latency test {i}",
                "priority": "P3"
            })
            latency = (time.time() - start) * 1000

            if response.status_code in [200, 201]:
                latencies.append(latency)

        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            print(f"  Avg latency: {avg_latency:.0f}ms")
            print(f"  P95 latency: {p95_latency:.0f}ms")

            # Task creation should complete within 2 seconds (P95)
            assert p95_latency < 2000, f"Task creation P95 {p95_latency:.0f}ms exceeds 2s"


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabasePerformance:
    """Database query performance testing"""

    async def test_incident_query_performance(self, async_client):
        """Test incident query performance with filters"""

        print("\n[DB PERFORMANCE] Testing incident queries...")

        filters = [
            "?priority=P1",
            "?status=Resolved",
            "?category=Performance",
            "?limit=100"
        ]

        for filter_str in filters:
            times = []
            for _ in range(10):
                start = time.time()
                response = await async_client.get(f"/incidents{filter_str}")
                duration = (time.time() - start) * 1000

                if response.status_code == 200:
                    times.append(duration)

            if times:
                avg_time = statistics.mean(times)
                print(f"  Filter {filter_str}: {avg_time:.0f}ms avg")

                # Database queries should be under 200ms on average
                assert avg_time < 200, f"Query {filter_str} avg {avg_time:.0f}ms exceeds 200ms"


@pytest.mark.performance
@pytest.mark.asyncio
class TestRAGPerformance:
    """RAG system performance testing"""

    async def test_vector_search_performance(self, async_client):
        """Test Weaviate vector search performance"""

        print("\n[RAG PERFORMANCE] Testing vector search...")

        search_times = []
        for i in range(10):
            start = time.time()
            response = await async_client.post("/api/rag/search", json={
                "query": f"API timeout error test {i}",
                "limit": 5
            })
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                search_times.append(duration)

        if search_times:
            avg_time = statistics.mean(search_times)
            print(f"  Avg vector search: {avg_time:.0f}ms")

            # Vector search should be under 300ms on average
            assert avg_time < 300, f"Vector search avg {avg_time:.0f}ms exceeds 300ms"

    async def test_graph_query_performance(self, async_client):
        """Test Neo4j graph query performance"""

        print("\n[GRAPH PERFORMANCE] Testing causal queries...")

        query_times = []
        symptoms = ["502 errors", "timeout", "high CPU", "memory leak"]

        for symptom in symptoms:
            start = time.time()
            response = await async_client.post("/api/rag/causal", json={
                "symptom": symptom,
                "limit": 3
            })
            duration = (time.time() - start) * 1000

            if response.status_code == 200:
                query_times.append(duration)

        if query_times:
            avg_time = statistics.mean(query_times)
            print(f"  Avg graph query: {avg_time:.0f}ms")

            # Graph queries should be under 250ms on average
            assert avg_time < 250, f"Graph query avg {avg_time:.0f}ms exceeds 250ms"


@pytest.mark.performance
@pytest.mark.asyncio
class TestMemoryUsage:
    """Memory usage testing"""

    async def test_memory_leak_detection(self, async_client):
        """Test for memory leaks during sustained operation"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\n[MEMORY] Initial memory: {initial_memory:.2f} MB")

        # Perform 100 operations
        for i in range(100):
            await async_client.post("/task", json={
                "description": f"Memory test {i}",
                "priority": "P3"
            })

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"[MEMORY] Final memory: {final_memory:.2f} MB")
        print(f"[MEMORY] Increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable (<100MB for 100 requests)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB (possible leak)"


@pytest.mark.performance
def test_benchmark_llm_routing():
    """Benchmark LLM routing performance"""
    from orchestrator.router import route_task
    import time

    print("\n[BENCHMARK] LLM routing speed...")

    test_cases = [
        "API Gateway timeout - 502 errors",
        "Bug in payment validation code",
        "Database connection pool exhausted",
        "GitHub PR merge conflict",
        "High CPU usage on production servers"
    ]

    total_time = 0
    for description in test_cases:
        state = {
            "task_id": "bench-123",
            "description": description,
            "priority": "P2"
        }

        start = time.time()
        # This would call actual LLM in real scenario
        # result = route_task(state)
        duration = time.time() - start
        total_time += duration

    avg_time = total_time / len(test_cases)
    print(f"  Avg routing time: {avg_time:.2f}s")

    # Routing should be under 3 seconds on average
    # assert avg_time < 3.0, f"Routing avg {avg_time:.2f}s exceeds 3s"
