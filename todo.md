

[x] - /users endpoint inclides password and verification code. Redact
[x] - /users get endpoint is simulating returns from local 
[x] - User listing endpoint currently uses test data (needs to be connected to actual storage)
[x] - Add admin role check to /users endpoint.
[x] - Admin role check needs to be implemented for user management endpoints
[x] - Authorization checks needed for user operations (admin or self)
[x] - Validate user lookup has access to view user details
[x] - tests are returned for all users. limit per user.
[ ] - Email sender configuration needs to be reviewed
[ ] - History of tasks needs to be implemented
[ ] - Redis Keys are stored in a sorted set. Whenever we run keys() it returns the full set. This won't scale. We need to implement a pagination system or limit per user.
[ ] - user validation for tests, executions, etc.
[ ] - only draft tests can be changed or deleted. 
[ ] - copy test to draft.
[ ] - security around the test init. Server side, how to ensure the requester is also the owner of the target chatbot, else it's a security exploit (ddos etc). On the browser, handle CORS. Handle logins. 
[ ] - Add updated test sets from NIST AI Risk Management Framework, OECD AI Principles, GDPR, CCPA/CPRA , NYDFS Cybersecurity Regulation , OCC/FDIC/FFIEC Guidelines , SOX & COSO Frameworks, NIST SP 800-53 / SP 800-161, other standard tests?
[ ] - Password reset return malformed data 400 on password resets on invalid email. 
[ ] - user group CRUD.
[ ] - add user id to all backend logs to track who does what. 
[x] - GET /api/v1.0/prompts/?page=1&limit=50&status=ACTIVE&search=tes doesn't seem to respond with valid data. is it because we're searching name rather than uuid? 
[ ] - Select Prompt from Library 'GET /api/v1.0/prompts/?page=1&limit=100&category_type=SAFETY&status=ACTIVE' fails for categoty_type
[ ] - The tests themselves have limited connection stored compared with the AI emdpoint config. Update!


[ ] - investigate handling other things than llm results - marketing images, emails etc etc


# Reporting Update
1. Add ERROR Validation Status Tracking

  - Endpoint: GET /api/v1.0/reports/summary
  - Schema: ExecutionSummaryMetrics in OpenAPI components
  - Required Changes:
    - Add error_validations: integer field to
  ExecutionSummaryMetrics schema
    - Update database aggregation queries to count
  validation_status = 'ERROR'
    - Ensure the field is included in response payload

  2. Fix Success Rate Calculation Bug

  - Endpoint: GET /api/v1.0/reports/performance
  - Schema: TestPerformanceMetrics.success_rate
  - Current Issue: Shows 100% when only 1/10 executions validated
  - Required Fix:
  -- Current (incorrect): success_rate = passed_validations / 
  validated_executions
  -- Should be: success_rate = passed_validations / 
  total_executions
  -- OR: success_rate = passed_validations / (passed + failed + 
  error) 
  -- AND: success_rate = NULL when no validations completed

  3. Update Summary Report Endpoint

  - Endpoint: GET /api/v1.0/reports/summary
  - Changes:
    - Include error_validations count in response
    - Verify all validation statuses sum to total_executions
    - Test aggregation logic with mixed validation statuses

  4. Validate Status Counting Logic

  - Database Queries: Ensure proper counting of all 4 validation
  statuses:
    - PENDING → pending_validations
    - IN_PROGRESS → in_progress_validations
    - VALIDATED → validated_executions (then split into
  passed/failed)
    - ERROR → error_validations (NEW)

  🔧 Medium Priority - Improvements

  5. Clarify Acceptance Rate Calculation

  - Field: ExecutionSummaryMetrics.acceptance_rate
  - Required: Document the calculation methodology
  - Options:
    - passed_validations / total_executions * 100
    - passed_validations / validated_executions * 100
    - passed_validations / (validated_executions - 
  error_validations) * 100

  6. Update OpenAPI Documentation

  - File: OpenAPI schema components
  - Changes:
    - Add error_validations field documentation
    - Update field descriptions for clarity
    - Add examples with all validation statuses

  📊 Low Priority - Enhancements

  7. Enhanced Performance Metrics

  - Endpoint: GET /api/v1.0/reports/performance
  - Potential Addition: Add validation status breakdown per test:
  {
    "test_id": "uuid",
    "validation_breakdown": {
      "pending": 5,
      "in_progress": 2,
      "passed": 8,
      "failed": 1,
      "error": 1
    }
  }

  🧪 Testing Requirements

  8. Database Query Testing

  - Test Cases:
    - Mixed validation statuses for single test
    - ERROR status aggregation in reports
    - Edge cases: all pending, all error, no executions
    - Performance with large datasets

  📋 Implementation Checklist

## Code Analysis Findings:

✅ **Current Issues Confirmed:**
1. ExecutionSummaryMetrics schema missing `error_validations` field (app/schemas/reports.py:27-44)
2. Success rate bug: uses `passed_count / validated_executions` instead of `passed_count / total_executions` (app/modules/reports_store.py:167,314)  
3. Missing ERROR status counting in _calculate_execution_metrics (app/modules/reports_store.py:407-411)
4. Only counts 3 validation statuses instead of 4 (PENDING, IN_PROGRESS, VALIDATED, ERROR)

✅ **Files to Update:**
- app/schemas/reports.py (add error_validations field)
- app/modules/reports_store.py (fix calculations and counting)
- tests/ (comprehensive validation testing)

✅ **Implementation Order:**
1. ✅ Schema updates (ExecutionSummaryMetrics) - COMPLETED
2. ✅ Store logic fixes (status counting, success rate calculation) - COMPLETED
3. ✅ Testing with mixed validation statuses - COMPLETED
4. ✅ Documentation updates - COMPLETED

## ✅ IMPLEMENTATION COMPLETE

**Changes Made:**
1. Added `error_validations` field to `ExecutionSummaryMetrics` schema (app/schemas/reports.py:35)
2. Fixed success rate calculation to use `total_executions` instead of `validated_executions` (app/modules/reports_store.py:167,314)
3. Updated `_calculate_execution_metrics` to count ERROR status (app/modules/reports_store.py:408)
4. Fixed acceptance rate calculation for consistency (app/modules/reports_store.py:424)
5. Added comprehensive tests for all validation statuses including edge cases

**Verification:**
- All 12 reports store tests passing ✅
- All 14 reports API tests passing ✅
- Mixed validation status scenarios tested ✅
- Success rate calculation edge cases tested ✅
