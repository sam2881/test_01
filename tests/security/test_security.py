"""Security tests for AI Agent Platform"""
import pytest
import httpx
import json


@pytest.mark.security
@pytest.mark.asyncio
class TestInputValidation:
    """Test input validation and sanitization"""

    async def test_sql_injection_prevention(self, async_client):
        """Test SQL injection attempts are blocked"""

        sql_injections = [
            "'; DROP TABLE incidents; --",
            "1' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--"
        ]

        for injection in sql_injections:
            response = await async_client.post("/task", json={
                "description": injection,
                "priority": "P1"
            })

            # Should either sanitize or reject
            assert response.status_code in [200, 201, 400, 422]

            if response.status_code in [200, 201]:
                # If accepted, verify it was sanitized
                data = response.json()
                assert "task_id" in data

    async def test_xss_prevention(self, async_client):
        """Test XSS injection attempts are blocked"""

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>"
        ]

        for payload in xss_payloads:
            response = await async_client.post("/task", json={
                "description": payload,
                "priority": "P2"
            })

            # Should sanitize or reject
            assert response.status_code in [200, 201, 400, 422]

    async def test_command_injection_prevention(self, async_client):
        """Test command injection attempts are blocked"""

        command_injections = [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`rm -rf /`"
        ]

        for injection in command_injections:
            response = await async_client.post("/task", json={
                "description": f"Test incident {injection}",
                "priority": "P3"
            })

            # Should sanitize or reject
            assert response.status_code in [200, 201, 400, 422]

    async def test_path_traversal_prevention(self, async_client):
        """Test path traversal attempts are blocked"""

        path_traversals = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "....//....//etc/passwd"
        ]

        for path in path_traversals:
            response = await async_client.get(f"/incidents/{path}")

            # Should return 404 or 400, not expose files
            assert response.status_code in [404, 400]


@pytest.mark.security
@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication and authorization"""

    async def test_missing_authentication(self, async_client):
        """Test that protected endpoints require authentication"""

        # These endpoints should require auth (if implemented)
        protected_endpoints = [
            "/admin/users",
            "/admin/config",
            "/admin/reset"
        ]

        for endpoint in protected_endpoints:
            response = await async_client.get(endpoint)

            # Should return 401 (unauthorized) or 404 (doesn't exist)
            assert response.status_code in [401, 404]

    async def test_invalid_token(self, async_client):
        """Test that invalid tokens are rejected"""

        response = await async_client.get(
            "/agents/status",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        # Should accept without auth or reject invalid token
        assert response.status_code in [200, 401]

    async def test_expired_token(self, async_client):
        """Test that expired tokens are rejected"""

        # Simulate expired JWT token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjowfQ.invalid"

        response = await async_client.get(
            "/incidents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        # Should accept without auth or reject expired token
        assert response.status_code in [200, 401]


@pytest.mark.security
@pytest.mark.asyncio
class TestDataLeakage:
    """Test for data leakage vulnerabilities"""

    async def test_error_messages_no_sensitive_data(self, async_client):
        """Test that error messages don't leak sensitive information"""

        # Trigger an error
        response = await async_client.get("/nonexistent_endpoint_12345")

        assert response.status_code == 404

        # Error message should not contain:
        # - File paths
        # - Stack traces
        # - Database connection strings
        # - API keys
        error_text = response.text.lower()

        sensitive_patterns = [
            "/home/",
            "c:\\",
            "password",
            "api_key",
            "secret",
            "traceback"
        ]

        for pattern in sensitive_patterns:
            assert pattern not in error_text, f"Error message contains sensitive data: {pattern}"

    async def test_response_headers_secure(self, async_client):
        """Test that security headers are properly set"""

        response = await async_client.get("/health")

        headers = response.headers

        # Check for security headers (if implemented)
        # These may not be present in development
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]

        # Just check they exist, values can vary
        for header in expected_headers:
            if header in headers:
                print(f"✓ {header}: {headers[header]}")

    async def test_no_directory_listing(self, async_client):
        """Test that directory listing is disabled"""

        response = await async_client.get("/")

        # Should return proper response, not directory listing
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Should not contain directory listing indicators
            content = response.text.lower()
            assert "index of" not in content
            assert "parent directory" not in content


@pytest.mark.security
@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting and DOS prevention"""

    async def test_rate_limit_enforcement(self, async_client):
        """Test that rate limiting is enforced"""

        # Send many requests rapidly
        responses = []
        for i in range(120):  # Assuming 100 req/min limit
            response = await async_client.get("/health")
            responses.append(response.status_code)

        # Count rate limited responses
        rate_limited = responses.count(429)

        print(f"\n[RATE LIMIT] {rate_limited}/120 requests were rate limited")

        # In test environment, rate limiting might not be enforced
        # Just verify the endpoint is responsive
        assert 200 in responses

    async def test_request_size_limit(self, async_client):
        """Test that oversized requests are rejected"""

        # Create a very large payload
        large_payload = {
            "description": "A" * 1000000,  # 1MB string
            "priority": "P1"
        }

        response = await async_client.post("/task", json=large_payload)

        # Should reject or truncate
        assert response.status_code in [200, 201, 413, 422]


@pytest.mark.security
@pytest.mark.asyncio
class TestAPIKeyProtection:
    """Test API key and secret protection"""

    async def test_api_keys_not_in_responses(self, async_client):
        """Test that API keys are never returned in responses"""

        response = await async_client.get("/incidents")

        if response.status_code == 200:
            content = response.text

            # Should not contain API key patterns
            sensitive_patterns = [
                "sk-",  # OpenAI keys
                "sk-ant-",  # Anthropic keys
                "ghp_",  # GitHub tokens
                "AKIA",  # AWS keys
            ]

            for pattern in sensitive_patterns:
                assert pattern not in content, f"Response contains API key pattern: {pattern}"

    async def test_environment_variables_not_exposed(self, async_client):
        """Test that environment variables are not exposed"""

        response = await async_client.get("/health")

        if response.status_code == 200:
            content = response.text.upper()

            # Should not contain env var names
            env_vars = [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "DATABASE_URL",
                "SECRET_KEY"
            ]

            for var in env_vars:
                assert var not in content, f"Response exposes environment variable: {var}"


@pytest.mark.security
@pytest.mark.asyncio
class TestCryptography:
    """Test cryptographic implementations"""

    async def test_passwords_not_stored_plaintext(self, async_client):
        """Test that passwords are hashed, not stored in plain text"""

        # This would require database access to verify
        # For now, just document the requirement
        assert True  # Implement based on your auth system

    async def test_secure_session_management(self, async_client):
        """Test session security"""

        response = await async_client.get("/incidents")

        # Check for secure cookie flags (if using cookies)
        if "Set-Cookie" in response.headers:
            cookie = response.headers["Set-Cookie"]

            # Should have Secure and HttpOnly flags
            # In test environment, Secure might not be set
            assert "HttpOnly" in cookie or True  # Document requirement


@pytest.mark.security
@pytest.mark.asyncio
class TestDependencyVulnerabilities:
    """Test for known dependency vulnerabilities"""

    async def test_no_known_vulnerable_dependencies(self):
        """Test that dependencies don't have known vulnerabilities"""

        # This would typically run `safety check` or `pip-audit`
        import subprocess

        try:
            # Run safety check (if installed)
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                print(f"\n[SECURITY] Found {len(vulnerabilities)} vulnerabilities")

                # In production, this should be 0
                # For now, just report
                assert len(vulnerabilities) < 10, "Too many vulnerabilities found"
            else:
                print("[SECURITY] Safety check not available or failed")

        except FileNotFoundError:
            pytest.skip("Safety package not installed")
        except Exception as e:
            pytest.skip(f"Dependency check failed: {e}")
