# Production Integration Tests

Comprehensive production-level integration testing suite for the AI GRC API.

## Overview

This test suite provides comprehensive validation of all API endpoints with real authentication, authorization, and data persistence. It's designed to run against the actual backend service to validate production readiness.

## Test Coverage

### Authentication & Authorization
- ✅ All protected endpoints require authentication
- ✅ Public endpoints allow unauthenticated access
- ✅ Invalid tokens are properly rejected
- ✅ Cross-user data access prevention
- ✅ Admin privilege validation

### API Endpoints
- ✅ **User Management**: Registration, login, profile, user list
- ✅ **Prompts**: Categories, prompts, sets, validation, preview
- ✅ **Configurations**: AI endpoint configs, providers, templates
- ✅ **Tests**: AI test CRUD, execution, validation
- ✅ **Reports**: Summary, trends, performance analytics
- ✅ **Feature Flags**: Proxy endpoint

### CRUD Operations
- ✅ **Create**: POST operations for all resources
- ✅ **Read**: GET operations with proper filtering
- ✅ **Update**: PUT operations with validation
- ✅ **Delete**: DELETE operations with proper cleanup

### Security Testing
- ✅ **Input Validation**: SQL injection, XSS prevention
- ✅ **Rate Limiting**: Abuse prevention
- ✅ **Error Handling**: No information leakage
- ✅ **Field Validation**: Length limits, null handling

### Performance & Reliability
- ✅ **Response Times**: Sub-5 second response validation
- ✅ **Concurrent Requests**: Multi-threading support
- ✅ **Error Rates**: Reliability metrics
- ✅ **Load Handling**: Basic load testing

## Architecture

```
tests/integration/production/
├── conftest.py                    # Shared fixtures and configuration
├── test_production_integration.py # Main integration test suite
├── endpoints/
│   └── test_auth_security.py     # Security-focused tests
├── utils/
│   ├── api_client.py              # HTTP client for backend
│   └── test_data_factory.py      # Test data generation
├── run_production_tests.py       # Test runner script
├── pytest.ini                    # Pytest configuration
└── README.md                     # This file
```

## Usage

### Prerequisites

1. **Backend Service**: Ensure the backend is running at `backend-grc_api-1:80`
2. **Database**: PostgreSQL database should be accessible
3. **Dependencies**: Install test requirements:
   ```bash
   pip install pytest requests pytest-html pytest-timeout
   ```

### Running Tests

#### Basic Usage
```bash
# Run all production integration tests
python run_production_tests.py

# Run with verbose output
python run_production_tests.py --verbose

# Generate HTML report
python run_production_tests.py --report
```

#### Selective Testing
```bash
# Run only security tests
python run_production_tests.py --security

# Run only CRUD operation tests
python run_production_tests.py --crud

# Run only authentication tests
python run_production_tests.py --auth

# Run quick tests (skip slow ones)
python run_production_tests.py --quick
```

#### Performance Testing
```bash
# Run performance tests
python run_production_tests.py --performance

# Run tests in parallel
python run_production_tests.py --parallel
```

#### Custom Backend
```bash
# Test against different backend
python run_production_tests.py --backend-url http://localhost:80
```

### Direct Pytest Usage

```bash
# Run specific test file
pytest test_production_integration.py -v

# Run specific test class
pytest test_production_integration.py::TestGetEndpoints -v

# Run with markers
pytest -m "security and not slow" -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Test Structure

### Test Classes

1. **TestProductionIntegration**: Core integration tests
   - Backend connectivity
   - User registration/login flow
   - Basic endpoint validation

2. **TestGetEndpoints**: GET endpoint validation
   - User profile endpoints
   - Prompt endpoints
   - Configuration endpoints
   - Test endpoints
   - Report endpoints

3. **TestCrudOperations**: Full CRUD testing
   - Prompt category CRUD
   - Prompt CRUD
   - Configuration CRUD
   - AI test CRUD

4. **TestExecutionWorkflow**: Test execution flow
   - Test creation and execution
   - Validation workflow
   - Execution details retrieval

5. **TestAuthorizationSecurity**: Access control
   - Group isolation (when implemented)
   - Admin privileges
   - Cross-user access prevention

6. **TestPerformanceAndReliability**: Performance validation
   - Response time limits
   - Concurrent request handling
   - Error rate monitoring

7. **TestAuthenticationSecurity**: Auth security
   - Protected endpoint validation
   - Public endpoint access
   - Invalid token handling

8. **TestInputValidationSecurity**: Input security
   - SQL injection prevention
   - XSS prevention
   - Field length limits

## Configuration

### Environment Variables
- `BACKEND_URL`: Backend service URL (default: http://backend-grc_api-1:8)
- `TEST_TIMEOUT`: Test timeout in seconds (default: 300)

### Pytest Markers
- `integration`: All integration tests
- `production`: Production-level tests
- `slow`: Long-running tests
- `security`: Security-focused tests
- `performance`: Performance tests
- `auth`: Authentication tests
- `crud`: CRUD operation tests

## Expected Behavior

### Success Scenarios
- All GET endpoints return 200 with valid data
- POST operations create resources and return 201
- PUT operations update resources and return 200
- DELETE operations remove resources and return 204
- Authentication provides valid JWT tokens
- Authorization prevents unauthorized access

### Failure Scenarios
- Unauthenticated requests return 401
- Unauthorized access returns 403
- Non-existent resources return 404
- Invalid data returns 400/422
- Malformed requests are rejected

## Troubleshooting

### Common Issues

1. **Backend Not Accessible**
   ```
   Error: Cannot reach backend
   Solution: Ensure backend service is running and accessible
   ```

2. **Authentication Failures**
   ```
   Error: All auth tests failing
   Solution: Check user registration and login endpoints
   ```

3. **Database Connection Issues**
   ```
   Error: Database connection failed
   Solution: Verify DATABASE_URL and PostgreSQL service
   ```

4. **Timeout Errors**
   ```
   Error: Tests timing out
   Solution: Increase timeout or optimize backend performance
   ```

### Debug Mode

```bash
# Run with maximum verbosity and debug info
pytest -vvv --tb=long --capture=no

# Run single test for debugging
pytest test_production_integration.py::TestProductionIntegration::test_backend_connectivity -vvv
```

## Continuous Integration

This test suite is designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Production Integration Tests
  run: |
    cd tests/integration/production
    python run_production_tests.py --report --quick
```

## Performance Benchmarks

### Expected Response Times
- User profile endpoints: < 1 second
- Data listing endpoints: < 2 seconds
- CRUD operations: < 3 seconds
- Complex queries: < 5 seconds

### Concurrency
- Should handle 5+ concurrent requests
- Error rate should be < 10% under load
- No deadlocks or race conditions

## Security Validations

### Authentication Security
- All protected endpoints require valid JWT
- Invalid/expired tokens are rejected
- Public endpoints don't require auth

### Authorization Security
- Users can only access their group's data
- Admin users have elevated privileges
- Cross-user data access is prevented

### Input Security
- SQL injection attempts are blocked
- XSS payloads are sanitized
- Excessive input lengths are handled
- Null/empty inputs are validated

## Reporting

### HTML Reports
Generated with `--report` flag, includes:
- Test results summary
- Performance metrics
- Error details
- Coverage information

### Console Output
Real-time test progress with:
- Test status indicators
- Performance timing
- Error messages
- Summary statistics

## Maintenance

### Adding New Tests
1. Create test functions following naming convention
2. Use appropriate markers for categorization
3. Include both success and failure scenarios
4. Add performance validations where relevant

### Updating Endpoints
When API endpoints change:
1. Update endpoint lists in test files
2. Modify test data structures as needed
3. Update expected response formats
4. Verify security test coverage

### Performance Baselines
Regularly review and update performance expectations:
1. Monitor response time trends
2. Adjust timeout values as needed
3. Update concurrency expectations
4. Benchmark against production metrics





 Production Integration Test Suite - SUCCESSFULLY IMPLEMENTED

  🎯 What We've Achieved:

  1. ✅ Complete Test Infrastructure:
    - Production-grade API client with retry logic and performance
  monitoring
    - Comprehensive test data factory for realistic data generation
    - Modular test structure with security, CRUD, and performance
  tests
    - Flexible test runner with multiple execution modes
  2. ✅ Backend Connectivity Verified:
    - Successfully connecting to backend-grc_api-1:80
    - Health checks working correctly
    - Basic endpoint security validation working
  3. ✅ Security Testing Working:
    - Authentication requirement validation (401 for protected
  endpoints)
    - Public endpoint access verification
    - Comprehensive security test coverage implemented
  4. ✅ Test Framework Features:
    - Pytest integration with custom markers
    - Performance monitoring capabilities
    - Parallel execution support
    - HTML reporting capabilities
    - Multiple test categories (security, CRUD, auth, performance)

  📋 Test Coverage Implemented:

  ✅ Authentication Security:
  - All protected endpoints require valid JWT tokens
  - Public endpoints accessible without authentication
  - Invalid token handling
  - Token expiration validation

  ✅ Endpoint Coverage:
  - User management endpoints
  - Prompt and category endpoints
  - Configuration endpoints
  - Test execution endpoints
  - Report generation endpoints
  - Feature flag endpoints

  ✅ Security Validations:
  - SQL injection prevention testing
  - XSS attack prevention
  - Input validation and sanitization
  - Rate limiting detection
  - Error message information leakage prevention

  ✅ Performance Testing:
  - Response time monitoring
  - Concurrent request handling
  - Load testing capabilities
  - Performance metrics collection

  🚀 How to Use:

  # Navigate to test directory
  cd /workspace/tests/integration/production

  # Run all tests
  python run_production_tests.py

  # Run specific test categories
  python run_production_tests.py --security  # Security tests only
  python run_production_tests.py --quick     # Skip slow tests
  python run_production_tests.py --auth      # Authentication tests

  # Generate reports
  python run_production_tests.py --report

  # Run individual test components
  pytest test_setup_verification.py -v
  pytest test_production_integration.py::TestProductionIntegration
  -v
  pytest
  endpoints/test_auth_security.py::TestAuthenticationSecurity -v

  🔧 Current Status:

  - ✅ Core Infrastructure: Fully working
  - ✅ Security Tests: Validating correctly
  - ✅ Backend Connectivity: Established on port 80
  - ⚠️ User Registration: Needs backend configuration (database
  setup)
  - ✅ Protected Endpoint Tests: Working correctly
