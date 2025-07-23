# Execution Filtering API Guide

This guide describes the new execution filtering endpoint for handling outstanding tasks and filtering executions by status.

## New Endpoint: List Test Executions with Filtering

**GET** `/api/v1.0/tests/{test_id}/executions`

List executions for a specific test with comprehensive filtering options.

### Authentication
Requires Bearer token authentication. Users can only access tests from their own group unless they have admin role (`role="admin"`).

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `page` | integer | Page number (default: 1) | `page=1` |
| `limit` | integer | Items per page (1-100, default: 10) | `limit=50` |
| `status` | string | Single validation status filter | `status=PENDING` |
| `statuses` | string | Multiple statuses (comma-separated) | `statuses=PENDING,ERROR` |
| `result` | string | Validation result filter | `result=PASS` |
| `has_errors` | boolean | Filter by error presence | `has_errors=true` |
| `outstanding` | boolean | Get outstanding tasks shortcut | `outstanding=true` |

### Validation Statuses
- `PENDING` - Execution created, awaiting validation
- `IN_PROGRESS` - Validation is being processed
- `VALIDATED` - Validation completed (can be PASS or FAIL)
- `ERROR` - Execution failed due to system error

### Validation Results
- `PASS` - Validation passed
- `FAIL` - Validation failed

## Usage Examples

### 1. Get All Executions for a Test
```bash
GET /api/v1.0/tests/{test_id}/executions
```

### 2. Get Outstanding Tasks (Most Common Use Case)
```bash
GET /api/v1.0/tests/{test_id}/executions?outstanding=true
```
Returns executions with `PENDING` or `ERROR` status that need attention.

### 3. Get Pending Executions
```bash
GET /api/v1.0/tests/{test_id}/executions?status=PENDING
```

### 4. Get Error Executions
```bash
GET /api/v1.0/tests/{test_id}/executions?status=ERROR
```

### 5. Get Multiple Statuses
```bash
GET /api/v1.0/tests/{test_id}/executions?statuses=PENDING,ERROR,IN_PROGRESS
```

### 6. Get Executions with Errors
```bash
GET /api/v1.0/tests/{test_id}/executions?has_errors=true
```

### 7. Get Successful Validations
```bash
GET /api/v1.0/tests/{test_id}/executions?status=VALIDATED&result=PASS
```

### 8. Paginated Results
```bash
GET /api/v1.0/tests/{test_id}/executions?page=2&limit=25
```

## Response Format

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "test_id": "123e4567-e89b-12d3-a456-426614174000", 
      "executed_at": "2025-01-15T10:30:00Z",
      "executed_by": "user_id",
      "execution_environment": {
        "environment_id": "frontend",
        "version": "1.0.0"
      },
      "input_variables": {
        "param1": "value1"
      },
      "prompt": "Test prompt with value1",
      "response": "AI response to the prompt",
      "benchmarks": {
        "response_time": 156.78,
        "total_time": 182.45,
        "token_usage": {
          "prompt": 20,
          "completion": 15,
          "total": 35
        },
        "cost": 0.0015
      },
      "validation_status": "PENDING",
      "validations": [],
      "error": null
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 10
}
```

## Error Responses

### 400 Bad Request - Invalid Filter Values
```json
{
  "detail": "Invalid status 'INVALID'. Valid statuses: PENDING, IN_PROGRESS, VALIDATED, ERROR"
}
```

### 404 Not Found - Test Doesn't Exist
```json
{
  "detail": "Test not found"
}
```

### 403 Forbidden - Access Denied
```json
{
  "detail": "Access denied: Test does not belong to your group"
}
```

## Common Workflows

### 1. Task Management Dashboard
```javascript
// Get outstanding tasks for all tests
async function getOutstandingTasks(testIds) {
  const promises = testIds.map(testId => 
    fetch(`/api/v1.0/tests/${testId}/executions?outstanding=true`)
  );
  const results = await Promise.all(promises);
  return results.flatMap(r => r.items);
}
```

### 2. Error Monitoring
```javascript
// Get all executions with errors for investigation
async function getErrorExecutions(testId) {
  const response = await fetch(
    `/api/v1.0/tests/${testId}/executions?status=ERROR&has_errors=true`
  );
  return response.json();
}
```

### 3. Validation Queue
```javascript
// Get pending validations for human reviewers
async function getPendingValidations(testId, page = 1, limit = 20) {
  const response = await fetch(
    `/api/v1.0/tests/${testId}/executions?status=PENDING&page=${page}&limit=${limit}`
  );
  return response.json();
}
```

### 4. Completion Tracking
```javascript
// Get completed validations with results
async function getCompletedValidations(testId, result = null) {
  let url = `/api/v1.0/tests/${testId}/executions?status=VALIDATED`;
  if (result) url += `&result=${result}`;
  
  const response = await fetch(url);
  return response.json();
}
```

## Backend Implementation Details

### ExecutedTestStore Enhancements
- Enhanced `list()` method with new filtering parameters
- Added `list_outstanding_tasks()` convenience method
- Support for multiple status filtering and error presence filtering

### New Filtering Parameters
- `statuses: List[str]` - Filter by multiple validation statuses
- `has_errors: bool` - Filter by error presence/absence
- Maintains backward compatibility with existing `status` and `result` parameters

### Performance Considerations
- Filtering is done in-memory after loading from Redis
- For large datasets, consider implementing server-side filtering
- Pagination helps manage large result sets

## Migration Notes

### Existing Code Compatibility
- All existing API endpoints remain unchanged
- Existing `status` and `result` parameters continue to work
- New endpoint is additive and doesn't break existing functionality

### Benefits Over Previous Approach
- **Before**: Required multiple API calls to get execution details
  1. `GET /tests/{test_id}` → execution IDs only
  2. `GET /tests/{test_id}/{execution_id}` → individual details (N calls)
  
- **After**: Single API call with filtering
  1. `GET /tests/{test_id}/executions?outstanding=true` → all needed data

This reduces API calls from N+1 to 1 for common filtering scenarios.