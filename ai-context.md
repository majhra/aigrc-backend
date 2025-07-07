# AI Validation & Audit Tool - Frontend Development Context

## Project Overview

We are building an AI Validation & Audit Tool focused on providing governance, risk, and compliance (GRC) reporting to CEO and board level members. The system allows IT teams to document, validate, and report on AI interactions with expert human oversight for quality control and compliance verification.

This document provides complete context for the frontend development of this MVP application.

## Current Implementation Status

### ✅ IMPLEMENTED - Authentication & User Management
- JWT-based authentication with email/password
- User registration with email verification
- Password reset functionality
- User profile management
- Admin user management (create, update, list users)
- Support request system

### ✅ IMPLEMENTED - Core API Endpoints

#### Authentication (COMPLETE)
- `POST /api/v1.0/user/login` - User login with JWT token generation
- `POST /api/v1.0/user/register` - New user registration
- `POST /api/v1.0/user/verify_email` - Email verification
- `POST /api/v1.0/user/resend_verification_email` - Resend verification email
- `POST /api/v1.0/user/password_reset/request` - Request password reset
- `POST /api/v1.0/user/password_reset/verify` - Verify and set new password

#### User Management (COMPLETE)
- `GET /api/v1.0/user/me` - Get current user profile
- `POST /api/v1.0/user/update_profile` - Update user profile
- `POST /api/v1.0/user/support` - Submit support request
- `GET /api/v1.0/user/users` - List users (admin only, paginated)
- `GET /api/v1.0/user/users/{user_id}` - Get user by UUID (admin only)
- `GET /api/v1.0/user/users/email/{email}` - Get user by email (admin only)
- `POST /api/v1.0/user/users` - Create new user (admin only)
- `PUT /api/v1.0/user/users/{user_id}` - Update user (admin only)

#### Feature Flags (BASIC IMPLEMENTATION)
- `GET /api/v1.0/feature-flags/proxy` - Get feature flags for user

#### Basic AI Connection (IMPLEMENTED)
- `POST /api/v1.0/ai-connection/test` - Test AI connection
- Basic AI connection service with OpenAI integration

### ✅ IMPLEMENTED - Storage & Infrastructure
- Redis for persistent storage
- UUID-based user identification
- Email-based user lookup
- Support for pagination in user listing
- Store interfaces for users, groups, executions, tests, reports

### ✅ IMPLEMENTED - Security Features
- JWT token-based authentication
- Password hashing
- Email verification
- Password reset with time-limited codes
- CORS protection
- Environment-based configuration

### ✅ IMPLEMENTED - Email Integration
- AWS SES integration for transactional emails
- Email templates for:
  - Account verification
  - Password reset
  - Support requests
  - User invitations

### ✅ IMPLEMENTED - Additional Features
- Group management system
- Execution tracking infrastructure
- Test logging system
- Report generation foundation

### ✅ IMPLEMENTED - Test Management System
- Complete test CRUD operations
- Test execution workflow
- Test validation system
- Test collections and organization

### ✅ IMPLEMENTED - Prompts Management
- Prompt library and categorization
- Prompt template system with variable substitution
- Prompt versioning and prepared prompt sets
- Complete CRUD operations with pagination and filtering

### ✅ IMPLEMENTED - Reports & Analytics
- Comprehensive reporting dashboard
- Performance metrics and trends
- Compliance reporting

## Key Business Goals

1. Enable systematic testing and validation of AI system responses
2. Provide auditable records for governance requirements
3. Allow human experts to evaluate AI outputs for compliance
4. Generate board-level reporting on AI system performance and compliance
5. Align with Australian Financial regulatory frameworks

## System Architecture Overview

### Backend-Driven AI Connector Architecture (Updated from Original Design)

```
+-------------------+             +-------------------+
|                   |  1. Fetch   |                   |
|  Web Interface    |<----------->|  Backend API      |
|  (React + TS)     |  Config     |  (Python/FastAPI) |
|        |          |             |                   |
+--------+----------+             +--------+----------+
         |                                 |
         | 2. Execute                      | Store
         | Connection                      | Results
         v                                 v
+-------------------+             +-------------------+
|                   |             |                   |
|  AI Connector     |             |  Database Layer   |
|  (Client-side)    |             |  (Redis)          |
|                   |             |                   |
+--------+----------+             +-------------------+
         |
         | 3. Direct API
         | Communication
         v
+-------------------+
|                   |
|  External AI      |
|  Endpoints        |
|                   |
+-------------------+
```

### Key Design Decisions

1. **Backend-Driven AI Connection:** The backend handles AI connections through the AI connection service, for automation. The frontend-driven connections is expected to work as well.
2. **Server-Side Key Storage:** API keys and credentials are securely stored on the backend.
3. **Configuration-Based Approach:** The MVP will use a configuration-based approach (no custom JavaScript) with architecture designed for future extensibility.
4. **Two-Column Layout:** The frontend UI will use a two-column layout with navigation sidebar and main content area.
5. **Python Backend:** The backend will be built with Python (FastAPI recommended) to align with the AI ecosystem.

## Frontend Technical Stack

1. **Core Technologies:**
   - React 18+
   - TypeScript 4.8+
   - Vite (build system)
   - React Router 6+

2. **UI Framework Options:**
   - Material UI
   - Chakra UI
   - Tailwind CSS

3. **State Management:**
   - React Context API (sufficient for MVP)
   - Local Storage for persisting user preferences

4. **API Communication:**
   - Axios for HTTP requests
   - JWT authentication

## Application Structure

### Frontend Directory Structure

```
src/
├── assets/           # Static assets, images, icons
├── components/       # Reusable UI components
│   ├── common/       # Basic UI elements
│   ├── layout/       # Layout components
│   └── features/     # Feature-specific components
├── context/          # React Context providers
├── hooks/            # Custom React hooks
├── pages/            # Page components mapped to routes
├── routes/           # Routing configuration
├── services/         # API and external service integrations
├── styles/           # Global styles and theme configuration
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
├── App.tsx           # Main application component
└── index.tsx         # Application entry point
```

### Backend Directory Structure

```
app/
├── api/              # FastAPI application structure
    ├── api_v1/             # Core business logic
        ├── endpoints/          # Endpoint definitions
    ├── schemas/            # Pydantic models
    ├── services/           # Service definitions
    ├── tests/              # Test files
    ├── utils/              # Utility functions
    ├── db/                 # Database models and operations
    ├── assets/             # additional assets
    ├── core/               # Core config
    ├── modules/            # Module definitions
    ├── schemas/            # Pydantic models
    ├── main.py             # FastAPI application entry point
├── requirements/         # Requirements for prod and dev
├── tests/            # Test files
```

### Core Features & Screens

1. **Authentication** 
   - Login/Registration
   - Password reset
   - Account management

2. **Dashboard** 
   - Summary metrics
   - Recent activity
   - Quick actions

3. **Prompt Library** 
   - View/manage standard prompts
   - Categorized prompt display
   - Prompt selection for testing

4. **Test Execution** 
   - Prompt selection and execution
   - Configuration selection
   - Response display and formatting

5. **Validation Workspace** 
   - Side-by-side prompt/response review
   - Pass/fail evaluation
   - Comment submission

6. **Reports & Analytics** 
   - Summary statistics
   - Filterable data tables
   - Export functionality

7. **Settings & Configuration** 
   - AI endpoint configuration
   - User management (admin)
   - System preferences

## User Roles

1. **IT Administrators**
   - Configure AI endpoints
   - Manage users and permissions
   - Set up testing environments

2. **Testers/Evaluators**
   - Execute AI tests
   - Document interactions
   - Submit for validation

3. **Human Validators**
   - Review AI outputs
   - Provide pass/fail evaluation
   - Add context via comments

4. **Executives/Board Members**
   - View summary reports
   - Monitor compliance status
   - Access high-level metrics

## API Integration

### Core API Endpoints

1. **Authentication:**  (api/api_v1/endpoints/user.py)
   - `POST /api/v1.0/user/login` - User login with JWT token generation
   - `POST /api/v1.0/user/register` - New user registration
   - `POST /api/v1.0/user/verify_email` - Email verification
   - `POST /api/v1.0/user/resend_verification_email` - Resend verification email
   - `POST /api/v1.0/user/password_reset/request` - Request password reset
   - `POST /api/v1.0/user/password_reset/verify` - Verify and set new password

2. **Users:** (api/api_v1/endpoints/user.py)
   - `GET /api/v1.0/user/me` - Get current user profile
   - `POST /api/v1.0/user/update_profile` - Update user profile
   - `POST /api/v1.0/user/support` - Submit support request
   - `GET /api/v1.0/user/users` - List users (admin only, paginated)
   - `GET /api/v1.0/user/users/{user_id}` - Get user by UUID (admin only)
   - `GET /api/v1.0/user/users/email/{email}` - Get user by email (admin only)
   - `POST /api/v1.0/user/users` - Create new user (admin only)
   - `PUT /api/v1.0/user/users/{user_id}` - Update user (admin only)
   - `POST /api/v1.0/user/users/invite` - Invite user to group

3. **Feature Flags:** (api/api_v1/endpoints/feature_flags.py)
   - `GET /api/v1.0/feature-flags/proxy` - Get feature flags for user

4. **AI Connection:** (api/api_v1/endpoints/ai_connection.py)
   - `POST /api/v1.0/ai-connection/test` - Test AI connection

5. **Prompts:** (api/api_v1/endpoints/prompts.py) - ✅ COMPLETE
   - `GET /api/v1.0/prompts/categories` - List prompt categories with pagination
   - `GET /api/v1.0/prompts/categories/{id}` - Get prompt category details
   - `POST /api/v1.0/prompts/categories` - Create prompt category
   - `PUT /api/v1.0/prompts/categories/{id}` - Update prompt category
   - `DELETE /api/v1.0/prompts/categories/{id}` - Delete prompt category
   - `GET /api/v1.0/prompts/` - List prompts with filtering and search
   - `GET /api/v1.0/prompts/{id}` - Get prompt details
   - `POST /api/v1.0/prompts/` - Create new prompt with template validation
   - `PUT /api/v1.0/prompts/{id}` - Update prompt
   - `DELETE /api/v1.0/prompts/{id}` - Delete prompt
   - `POST /api/v1.0/prompts/validate` - Validate prompt template
   - `POST /api/v1.0/prompts/preview` - Preview prompt with variables
   - `GET /api/v1.0/prompts/sets` - List prompt sets
   - `POST /api/v1.0/prompts/sets` - Create prompt set
   - `PUT /api/v1.0/prompts/sets/{id}` - Update prompt set
   - `DELETE /api/v1.0/prompts/sets/{id}` - Delete prompt set

6. **Configurations:** (api/api_v1/endpoints/configurations.py) - ✅ COMPLETE
   - `GET /api/v1.0/configurations/` - List AI endpoint configurations
   - `GET /api/v1.0/configurations/{id}` - Get configuration details
   - `POST /api/v1.0/configurations/` - Create AI endpoint configuration
   - `PUT /api/v1.0/configurations/{id}` - Update configuration
   - `DELETE /api/v1.0/configurations/{id}` - Delete configuration
   - `POST /api/v1.0/configurations/{id}/test` - Test configuration
   - `GET /api/v1.0/configurations/providers/list` - List supported AI providers
   - `GET /api/v1.0/configurations/templates/list` - List configuration templates
   - `POST /api/v1.0/configurations/validate` - Validate configuration

5. **Tests:**  (api/api_v1/endpoints/tests.py) -
   - `GET /api/v1.0/tests` - List all tests (paginated)
     - Query Parameters:
       - `page`: Page number (default: 1)
       - `limit`: Items per page (default: 10)
       - `status`: Filter by status (DRAFT, ACTIVE, ARCHIVED)
       - `riskLevel`: Filter by risk level (LOW, MEDIUM, HIGH)
       - `search`: Search in name, description, or tags
   - `GET /api/v1.0/tests/{test_id}` - Get test details
   - `POST /api/v1.0/tests` - Create new test
     - Request Body:
       ```json
       {
         "name": "string",
         "description": "string",
         "prompt_template": "string",
         "interface_type": "DIRECT_LLM" | "CHATBOT" | "PLUGIN_ENABLED" | "CUSTOM_APP",
         "connection_config": {
           "endpoint": "string",
           "auth_type": "NONE" | "API_KEY" | "BEARER_TOKEN",
           "timeout": number
         },
         "validation_config": {
           "validator_type": "HUMAN" | "AI" | "RULE_BASED" | "HYBRID",
           "validation_criteria": [
             {
               "id": "string",
               "name": "string",
               "description": "string",
               "type": "string",
               "parameters": {}
             }
           ]
         },
         "tags": ["string"],
         "risk_level": "LOW" | "MEDIUM" | "HIGH",
         "status": "DRAFT" | "ACTIVE" | "ARCHIVED"
       }
       ```
   - `PUT /api/v1.0/tests/{test_id}` - Update test
     - Request Body: Same as POST
   - `DELETE /api/v1.0/tests/{test_id}` - Delete test

2. **Test Executions:**  (api/api_v1/endpoints/tests.py) - 🔄 PENDING
   - `GET /api/v1.0/tests/{test_id}/executions` - List test executions
     - Query Parameters:
       - `page`: Page number (default: 1)
       - `limit`: Items per page (default: 10)
       - `status`: Filter by validation status (PENDING, VALIDATED)
       - `result`: Filter by validation result (PASS, FAIL)
   - `GET /api/v1.0/tests/{test_id}/executions/{execution_id}` - Get execution details
   - `POST /api/v1.0/tests/{test_id}/execute` - Execute a test
     - Request Body:
       ```json
       {
         "input_variables": {
           "key": "value"
         }
       }
       ```
   - `POST /api/v1.0/tests/{test_id}/{execution_id}/validate` - Submit validation
     - Request Body:
       ```json
       {
         "validator_id": "string",
         "validator_type": "HUMAN" | "AI" | "RULE_BASED",
         "status": "PASS" | "FAIL",
         #"criteria_results": [
         #  {
         #    "criterion_id": "string",
         #    "result": boolean,
         #    "notes": "string"
         #  }
         #],
         "notes": "string",
         "confidence": number
       }
       ```

6. **Test Results:**
   - `GET /api/v1.0/tests/{test_id}/results/summary` - Get test results summary
     - Response:
       ```json
       {
         "total_executions": number,
         "pass_rate": number,
         "average_responseTime": number,
         "last_execution_date": "string",
         "validation_status": {
           "PASS": number,
           "FAIL": number,
           "PENDING": number
         }
       }
       ```
   - `GET /api/v1.0/tests/{test_id}/results/trends` - Get test performance trends
     - Query Parameters:
       - `period`: Time period (DAY, WEEK, MONTH)
     - Response:
       ```json
       {
         "passRate": [
           {
             "date": "string",
             "value": number
           }
         ],
         "response_time": [
           {
             "date": "string",
             "value": number
           }
         ],
         "execution_count": [
           {
             "date": "string",
             "value": number
           }
         ]
       }
       ```

7. **Configuration:**
   - GET /api/configurations
   - GET /api/configurations/{id}
   - POST /api/configurations
   - PUT /api/configurations/{id}

8. **Prompts:** (api/api_v1/endpoints/prompts.py)
   - GET /api/prompts/categories
   - GET /api/prompts/categories/{id}
   - POST /api/prompts/categories
   - PUT /api/prompts/categories/{id}
   - GET /api/prompts/{id}
   - POST /api/prompts/
   - PUT /api/prompts/{id}

9. **Reports:** (api/api_v1/endpoints/reports.py)
   - `GET /api/v1.0/reports/summary` - Get summary report of tests and executions
     - Response:
       ```json
       {
         "test_metrics": {
           "total_tests": number,
           "active_tests": number,
           "draft_tests": number,
           "archived_tests": number,
           "high_risk_tests": number,
           "medium_risk_tests": number,
           "low_risk_tests": number,
           "safety_tests": number,
           "accuracy_tests": number,
           "compliance_tests": number
         },
         "execution_metrics": {
           "total_executions": number,
           "pending_validations": number,
           "in_progress_validations": number,
           "validated_executions": number,
           "passed_validations": number,
           "failed_validations": number,
           "acceptance_rate": number,
           "executions_last_7_days": number,
           "executions_last_30_days": number
         },
         "generated_at": "string"
       }
       ```
   
   - `GET /api/v1.0/reports/trends` - Get execution trends over time
     - Query Parameters:
       - `days`: Number of days to analyze (1-365, default: 30)
     - Response:
       ```json
       {
         "trends": [
           {
             "date": "string",
             "executions": number,
             "validations": number,
             "passed": number
           }
         ],
         "period_days": number,
         "generated_at": "string"
       }
       ```
   
   - `GET /api/v1.0/reports/performance` - Get performance metrics for tests
     - Response:
       ```json
       {
         "performance_metrics": [
           {
             "test_id": "string",
             "test_name": "string",
             "total_executions": number,
             "success_rate": number,
             "avg_response_time": number,
             "avg_cost": number,
             "last_executed": "string"
           }
         ],
         "generated_at": "string"
       }
       ```

## Frontend AI Connector Design

### Core Functionality

1. **Configuration Management:**
   - Load connector configuration from backend
   - Apply configuration to HTTP client
   - Handle configuration versioning

2. **Request Execution:**
   - Format requests according to configuration
   - Send HTTP requests to AI endpoints
   - Process responses according to configuration

3. **Error Handling:**
   - Connection error management
   - Retry logic
   - User-friendly error messaging

4. **Result Processing:**
   - Format responses for display
   - Extract key information
   - Submit results to backend

### Connection Flow

1. Frontend loads connector configuration from backend API
2. User selects prompt to test
3. Frontend formats request according to configuration
4. Request is sent directly to AI endpoint
5. Response is received and processed
6. Result is displayed to user and stored in backend
7. User validates response (pass/fail)
8. Validation is stored in backend

## UI/UX Guidelines

### Layout

Two-column layout:
- Left sidebar for navigation (collapsible on mobile)
- Right main content area
- Header with user info and global actions

### Color Scheme

- Primary: #3366FF (blue)
- Secondary: #6E56CF (purple)
- Success: #10B981 (green)
- Warning: #F59E0B (amber)
- Error: #EF4444 (red)
- Background: #F9FAFB (light gray)
- Text: #111827 (dark gray)

### Typography

- Primary Font: Inter or system sans-serif
- Headings: Semi-bold
- Body: Regular
- Monospace (for code): Source Code Pro or Consolas

### Component Style Guide

- Cards with subtle shadows for content sections
- Clear visual hierarchy with consistent spacing
- Button styles: primary, secondary, outline, text
- Form elements should be accessible and support validation

## Test Collection Model

The TestCollection model represents a logical grouping of related tests for easier management, execution, and reporting.

### Core Properties
- **id**: UUID for unique identification
- **name**: Human-readable name for the collection
- **description**: Detailed description of the collection's purpose and scope
- **tests**: Array of test IDs included in this collection

### Organization Properties
- **category**: Primary categorization (e.g., "SAFETY", "ACCURACY", "COMPLIANCE")
- **subcategory**: More specific categorization (optional)
- **priority**: Priority level (HIGH, MEDIUM, LOW)
- **ValidatorType**: Default validator type for tests (HUMAN, AI, RULE_BASED, HYBRID)

### Scheduling Information
- **scheduleType**: When to run this collection (MANUAL, SCHEDULED, TRIGGERED)
- **schedule**: Scheduling details (optional)
  - **frequency**: How often to run (HOURLY, DAILY, WEEKLY, MONTHLY)
  - **startTime**: When to start execution
  - **timeZone**: Time zone for scheduling
  - **daysOfWeek**: Which days to run (for WEEKLY)
  - **dayOfMonth**: Which day to run (for MONTHLY)
- **triggers**: Events that should trigger execution (optional)
  - Each trigger contains:
    - **type**: Type of trigger (API_CHANGE, MODEL_UPDATE, CODE_COMMIT)
    - **source**: Source of the trigger
    - **conditions**: Specific conditions for triggering

### Notification Settings
- **notificationConfig**: Configuration for execution notifications
  - **channels**: Array of notification channels (EMAIL, SLACK, WEBHOOK)
  - **events**: Which events trigger notifications (START, COMPLETION, FAILURE)
  - **recipients**: Who should receive notifications
  - **templates**: Message templates for different events (optional)

### Compliance Mapping
- **complianceFrameworks**: Array of compliance frameworks this collection addresses
  - Each framework contains:
    - **id**: Framework identifier
    - **name**: Framework name
    - **version**: Framework version
    - **controls**: Specific controls covered by this collection

### Metadata
- **createdBy**: User ID who created the collection
- **createdAt**: Timestamp of creation
- **updatedAt**: Timestamp of last update
- **tags**: Array of tags for categorization and filtering

### Status Information
- **status**: Current status (DRAFT, ACTIVE, ARCHIVED)
- **lastRunAt**: Timestamp of most recent execution (optional)

### Latest Execution Reference
- **latestExecutionId**: Reference to the latest collection execution (optional)

## Test Collection Execution Model

The TestCollectionExecution model represents a specific instance of a test collection being run.

### Core Properties
- **id**: UUID for this specific collection execution
- **collectionId**: Reference to parent collection

### Execution Context
- **executedAt**: When this execution occurred
- **executedBy**: User who ran the collection
- **executionEnvironment**: Details about the execution context
  - **environmentId**: Testing environment identifier
  - **version**: Version of the system under test
  - **parameters**: Environment-specific parameters (optional)

### Execution Summary
- **status**: Overall execution status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
- **progress**: Execution progress (percentage complete)
- **startTime**: When execution started
- **endTime**: When execution completed (optional)
- **totalTests**: Total number of tests in the collection
- **testsCompleted**: Number of tests completed
- **testsPassed**: Number of tests passed
- **testsFailed**: Number of tests failed
- **testsSkipped**: Number of tests skipped

### Test Execution References
- **testExecutions**: Array of test execution references
  - Each reference contains:
    - **testId**: Reference to the test
    - **executionId**: Reference to the test execution
    - **status**: Execution status for this specific test
    - **order**: Order in which the test was executed
    - **startTime**: When test execution started
    - **endTime**: When test execution completed (optional)

### Aggregated Results
- **aggregatedResults**: Summary of results across all tests
  - **passingRate**: Percentage of tests passed
  - **criticalFailures**: Number of critical failures
  - **averageResponseTime**: Average response time across all tests
  - **totalTokenUsage**: Total tokens used across all tests
  - **totalCost**: Total cost of the execution (optional)

### Compliance Results
- **complianceResults**: Results specific to compliance frameworks
  - Each result contains:
    - **frameworkId**: Reference to compliance framework
    - **controlsCovered**: Number of controls covered
    - **controlsPassed**: Number of controls passed
    - **controlsFailed**: Number of controls failed
    - **details**: Additional compliance details (optional)

### Error Information
- **error**: Error details if the execution failed (optional)
  - **code**: Error code
  - **message**: Error message
  - **details**: Additional error details (optional)

## Implementation Considerations

### MVP Phase
For the MVP of collections, focus on implementing:
- Core collection properties
- Basic organization properties
- Collection membership (tests array)
- Simple execution summary
- Essential metadata and status information

### Future Enhancements
- Advanced scheduling capabilities
- Complex dependency rules
- Comprehensive notification system
- Detailed compliance mapping
- Aggregated analytics across collections

### Data Management
- Implement efficient queries for collection-based operations
- Consider caching frequently accessed collections
- Support batch operations for collection management

### User Experience Considerations
- Allow for easy test inclusion/exclusion from collections
- Support test duplication across collections
- Provide collection templates for common testing patterns
- Enable bulk operations on collections (run, archive, duplicate)

## Test Model

The Test model represents a configured test case that can be executed against an AI system.

### Core Properties
- **id**: UUID for unique identification
- **name**: Human-readable name for the test
- **description**: Detailed description of test purpose and expectations
- **promptTemplate**: The actual prompt text to send to the AI model (may include variable placeholders)

### Testing Interface Configuration
- **interfaceType**: Type of AI interface being tested
  - Options: DIRECT_LLM, CHATBOT, PLUGIN_ENABLED, CUSTOM_APP
- **connectionConfig**: Configuration details for connecting to the AI system
  - **endpoint**: API endpoint or service URL
  - **headers**: Any required headers for authentication (optional)
  - **authType**: Type of authentication required (optional)
  - **timeout**: Connection timeout settings (optional)

### Additional Capabilities
- **plugins**: Array of plugins/tools to enable during testing (optional)
  - Each plugin contains:
    - **id**: Plugin identifier
    - **version**: Plugin version
    - **parameters**: Custom configuration for this plugin

- **conversationContext**: For chatbot testing (optional)
  - **systemPrompt**: System instructions for the conversation
  - **conversationHistory**: Previous messages to include
  - **userRole**: What role the test should assume

### Validation Configuration
- **validationConfig**: Configuration for test validation
  - **validatorType**: Type of validator (HUMAN, AI, RULE_BASED, HYBRID)
  - **validationCriteria**: Array of criteria to check
    - Each criterion contains:
      - **id**: Unique identifier
      - **name**: Human-readable name
      - **description**: What's being checked
      - **type**: Type of check (e.g., "CONTAINS", "SENTIMENT", "TOXICITY")
      - **parameters**: Specific parameters for this check (optional)
  - **requiredValidators**: Number of validators required (optional)
  - **validatorGroups**: Which user groups can validate this test (optional)

### Metadata
- **createdBy**: User ID who created the test
- **createdAt**: Timestamp of creation
- **updatedAt**: Timestamp of last update
- **tags**: Array of tags for categorization and filtering

### Status Information
- **status**: Current status (DRAFT, ACTIVE, ARCHIVED)
- **lastRunAt**: Timestamp of most recent execution (optional)

### Compliance Information
- **complianceCategories**: Array of compliance areas this test covers
- **riskLevel**: Risk assessment level (LOW, MEDIUM, HIGH)

### Latest Result Reference
- **latestExecutionId**: Reference to the latest test execution (optional)

## Test Execution Model

The TestExecution model represents a specific instance of a test being run.

### Core Properties
- **id**: UUID for this specific execution
- **testId**: Reference to parent test

### Execution Context
- **executedAt**: When this execution occurred
- **executedBy**: User who ran the test
- **executionEnvironment**: Details about the execution context
  - **environmentId**: Testing environment identifier
  - **version**: Version of the system under test (optional)
  - **parameters**: Environment-specific parameters (optional)

### Input/Output Data
- **inputVariables**: Key-value pairs of variables used in the prompt template (optional)
- **prompt**: The actual prompt sent (after any variable substitution)
- **response**: The raw response from the AI model

### Plugin Interactions
- **pluginInteractions**: Record of how the LLM interacted with plugins (optional)
  - Each interaction contains:
    - **pluginId**: Plugin identifier
    - **timestamp**: When the interaction occurred
    - **request**: The request sent to the plugin
    - **response**: The response received from the plugin

### Performance Metrics
- **benchmarks**: Performance metrics for this execution
  - **responseTime**: Time to first token (milliseconds)
  - **totalTime**: Total completion time (milliseconds)
  - **tokenUsage**: Breakdown of tokens used
    - **prompt**: Tokens in the prompt
    - **completion**: Tokens in the completion
    - **total**: Total tokens used
  - **cost**: Estimated cost of the execution (optional)

### Validation Information
- **validationStatus**: Current validation status (PENDING, IN_PROGRESS, VALIDATED)
- **validations**: Array of validation events
  - Each validation contains:
    - **validatorId**: Who performed validation
    - **validatorType**: Type of validator (HUMAN, AI, RULE_BASED)
    - **timestamp**: When validation occurred
    - **status**: Overall status (PASS, FAIL)
    - **criteriaResults**: Results for each validation criterion
      - Each result contains:
        - **criterionId**: Reference to the validation criterion
        - **result**: Boolean pass/fail
        - **notes**: Validator comments on this criterion (optional)
        - **confidence**: Confidence score (especially for AI validators) (optional)
    - **notes**: Overall validator comments (optional)
    - **confidence**: Overall confidence score (optional)

### Error Information
- **error**: Error details if the execution failed (optional)
  - **code**: Error code
  - **message**: Error message
  - **details**: Additional error details (optional)

## Implementation Considerations

### MVP Phase
For the MVP, focus on implementing:
- Core test properties
- Basic interface configuration
- Simple validation configuration
- Essential metadata and status information

### Future Enhancements
- Full plugin support
- Advanced conversation context
- Multiple validator workflows
- Comprehensive benchmarking
- Detailed compliance tracking

### Data Storage
- Consider using a document database for flexibility
- Implement proper indexing for performance
- Set up regular backups and data retention policies

### Security Considerations
- Encrypt sensitive information in the connection configuration
- Implement proper access controls for test data
- Audit all access to test results


## Implementation Priorities for Frontend MVP

### ✅ Backend Implementation COMPLETE
- Authentication system fully implemented
- User management system complete
- AI connection service operational
- Storage infrastructure (Redis) established
- Email integration working
- **Prompts management system complete** (NEW)
- **AI endpoint configuration management complete** (NEW)
- **Multi-provider AI support** (NEW)
- **Configuration validation and testing** (NEW)

### 🔄 Next Development Priorities

#### Remaining Backend (Optional Enhancements)
1. Complete test management system (CRUD operations) - **Partially implemented**
2. Implement test execution workflow
3. Build comprehensive reports system - **Foundation complete**
4. ~~Develop prompts management~~ ✅ **COMPLETED**
5. Create test validation framework

#### Frontend Development  
1. Core layout and navigation structure
2. Authentication flows integration
3. Test management interface
4. Test execution workflow UI
5. Validation interface
6. Reporting dashboard
7. Configuration management UI

## Future Roadmap (Beyond MVP)

1. Custom JavaScript support for connectors
2. Advanced validation criteria
3. Automated test scheduling
4. Enhanced analytics and visualization
5. Compliance template library
6. Integration with other GRC tools
7. Advanced AI model testing capabilities

## Development Approach

- Focus on functional completeness over visual polish
- Ensure responsive design from the start
- Implement proper error handling
- Use TypeScript for type safety
- Write unit tests for critical functionality
- Follow accessibility best practices