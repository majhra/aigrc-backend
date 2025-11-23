# AI GRC backend API

API Server For:
- Corporate AI Governance Risk and Compliance (GRC) model

## Current Implementation Status

### Authentication & User Management
- JWT-based authentication with email/password
- User registration with email verification
- Password reset functionality
- User profile management
- Admin user management (create, update, list users)
- Support request system

### API Endpoints

#### Authentication
- `POST /api/v1.0/user/login` - User login with JWT token generation
- `POST /api/v1.0/user/register` - New user registration
- `POST /api/v1.0/user/verify_email` - Email verification
- `POST /api/v1.0/user/resend_verification_email` - Resend verification email
- `POST /api/v1.0/user/password_reset/request` - Request password reset
- `POST /api/v1.0/user/password_reset/verify` - Verify and set new password

#### User Management
- `GET /api/v1.0/user/me` - Get current user profile
- `POST /api/v1.0/user/update_profile` - Update user profile
- `POST /api/v1.0/user/support` - Submit support request
- `GET /api/v1.0/user/users` - List users (incomplete, admin only, paginated)
- `GET /api/v1.0/user/users/{user_id}` - Get user by UUID (admin only)
- `GET /api/v1.0/user/users/email/{email}` - Get user by email (admin only)
- `POST /api/v1.0/user/users` - Create new user (admin only)
- `PUT /api/v1.0/user/users/{user_id}` - Update user (admin only)

#### Feature Flags
- `GET /api/v1.0/feature-flags/proxy` - Get feature flags for user

#### Prompt Management
- `GET /api/v1.0/prompts/categories` - List prompt categories
- `GET /api/v1.0/prompts/categories/{category_id}` - Get specific category
- `POST /api/v1.0/prompts/categories` - Create prompt category
- `PUT /api/v1.0/prompts/categories/{category_id}` - Update prompt category
- `DELETE /api/v1.0/prompts/categories/{category_id}` - Delete prompt category
- `GET /api/v1.0/prompts/` - List all prompts
- `GET /api/v1.0/prompts/{prompt_id}` - Get specific prompt
- `POST /api/v1.0/prompts/` - Create new prompt
- `PUT /api/v1.0/prompts/{prompt_id}` - Update prompt
- `DELETE /api/v1.0/prompts/{prompt_id}` - Delete prompt
- `POST /api/v1.0/prompts/validate` - Validate prompt template
- `POST /api/v1.0/prompts/preview` - Preview prompt with variables

#### Test Management
- `GET /api/v1.0/tests` - List all tests with pagination and filtering
- `GET /api/v1.0/tests/{test_id}` - Get test details
- `POST /api/v1.0/tests` - Create new test
- `PUT /api/v1.0/tests/{test_id}` - Update test
- `DELETE /api/v1.0/tests/{test_id}` - Delete test
- `POST /api/v1.0/tests/{test_id}/execute` - Execute a test
- `GET /api/v1.0/tests/{test_id}/executions` - Get test executions
- `POST /api/v1.0/tests/connection/test` - Test AI connection configuration

#### AI Configuration Management
- `GET /api/v1.0/configurations/` - List AI endpoint configurations
- `GET /api/v1.0/configurations/{config_id}` - Get specific configuration
- `POST /api/v1.0/configurations/` - Create new configuration
- `PUT /api/v1.0/configurations/{config_id}` - Update configuration
- `DELETE /api/v1.0/configurations/{config_id}` - Delete configuration
- `POST /api/v1.0/configurations/test` - Test AI endpoint configuration
- `POST /api/v1.0/configurations/validate` - Validate configuration
- `GET /api/v1.0/configurations/providers` - Get available AI providers
- `GET /api/v1.0/configurations/templates` - Get configuration templates

#### Reports & Analytics
- `GET /api/v1.0/reports/summary` - Get summary report
- `GET /api/v1.0/reports/trends` - Get execution trends
- `GET /api/v1.0/reports/performance` - Get performance metrics

#### AI Simulation
- `POST /api/v1.0/simulation/v1/chat/completions` - OpenAI-compatible chat simulation
- `GET /api/v1.0/simulation/v1/models` - List available models

### Storage
- PostgreSQL database with SQLAlchemy ORM
- Database migrations managed with Alembic
- UUID-based identification with efficient indexing
- Email-based user lookup with optimized queries
- Support for pagination, filtering, and complex queries
- Multi-tenant architecture with group-based data segregation

### Security Features
- JWT token-based authentication
- Password hashing
- Email verification
- Password reset with time-limited codes
- CORS protection
- Environment-based configuration

### Email Integration
- AWS SES integration for transactional emails
- Email templates for:
  - Account verification
  - Password reset
  - Support requests

## Requirements
- Python 3.11
- `pip install -r requirements/base.txt`

## Environment Variables
For this application to run successfully, the following environment variables must be specified (.env file will automatically be loaded):

### Required Variables
| Variable                    | Description                                                                                         |
|-----------------------------|-----------------------------------------------------------------------------------------------------|
| SECRET_KEY                  | The secret key used for JWT encode/decode.                                                          |
| DATABASE_URL                | PostgreSQL connection string (e.g., `postgresql://user:pass@localhost:5432/aigrc`).                 |
| SES_AWS_ACCESS_KEY_ID       | AWS IAM access key ID (used for boto3 package).                                                     |
| SES_AWS_SECRET_ACCESS_KEY   | AWS IAM secret access key (used for boto3 package).                                                 |
| SES_AWS_SENDER_EMAIL        | The email address to send the verification emails (this email must be setup with the SES service).  |
| SUPPORT_EMAIL               | The email address that support requests get sent to.                                                |

### Optional Variables
| Variable                    | Default                  | Description                                                            |
|-----------------------------|--------------------------|------------------------------------------------------------------------|
| ALGORITHM                   | `HS256`                  | The algorithm used for JWT encode/decode.                              |
| ACCESS_TOKEN_EXPIRE_MINUTES | `30`                     | The number of minutes until a JWT expires.                             |
| DATABASE_POOL_SIZE          | `10`                     | Database connection pool size.                                         |
| DATABASE_MAX_OVERFLOW       | `20`                     | Maximum overflow connections for the database pool.                    |
| DATABASE_ECHO               | `False`                  | Enable SQL query logging (for debugging).                              |
| ORIGINS                     | `localhost,localhost:3000` | Comma separated list of whitelisted origin URLs for CORS.            |
| SES_AWS_REGION              | `ap-southeast-2`         | The AWS region for the SES service.                                    |
| FRONTEND_URL_BASE           | `http://localhost:3000`  | The base URL of the frontend application.                              |
| UNLEASH_URL                 | -                        | Feature flags service URL (Unleash).                                   |
| UNLEASH_INSTANCE_ID         | -                        | Feature flags instance ID.                                             |

### Legacy Variables (for Redis support)
| Variable                    | Default                  | Description                                                            |
|-----------------------------|--------------------------|------------------------------------------------------------------------|
| REDIS_ADDRESS               | `localhost`              | The URL for the Redis database.                                        |
| REDIS_PORT                  | `6379`                   | The port for the Redis database.                                       |

## Local Development

### Running FastAPI Locally
`uvicorn app.main:app --reload`

Then you can access it as directed (usually http://127.0.0.1:8000)
access the docs via:  http://127.0.0.1:8000/docs

### Running with Docker
Comment out AWS Docker and remove comment for Local in server/Dockerfile
- Docker-compose build
- Docker-compose up

you can then connect to it via http://127.0.0.1:8888/docs

### Running PostgreSQL Locally
```bash
docker run -d --name aigrc-postgres \
  -e POSTGRES_USER=aigrc \
  -e POSTGRES_PASSWORD=aigrc \
  -e POSTGRES_DB=aigrc \
  -p 5432:5432 \
  postgres:15
```
This will launch a PostgreSQL server. Set your `DATABASE_URL` to `postgresql://aigrc:aigrc@localhost:5432/aigrc`.

### Running Database Migrations
```bash
# Apply all migrations
alembic upgrade head

# Create a new migration (after model changes)
alembic revision --autogenerate -m "Description of changes"
```

### Running Redis Locally (Legacy)
```bash
docker run -d --rm --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```
This will launch a Redis server and will be automatically deleted after the container exits. Visit [http://localhost:8001/](http://localhost:8001/) to view the RedisInsight dashboard.

### Running Tests

#### Development Tests
```bash
# Install test dependencies
pip install -r requirements/dev.txt

# Run unit and integration tests
python -m pytest

# Run with coverage
pytest --cov=app
```

#### Production Integration Tests
For comprehensive production-level testing against the live backend:

```bash
# Navigate to production test directory
cd tests/integration/production

# Run all production tests (requires --production flag)
python run_production_tests.py

# Run specific test categories
python run_production_tests.py --security    # Security tests only
python run_production_tests.py --crud        # CRUD operation tests
python run_production_tests.py --auth        # Authentication tests
python run_production_tests.py --quick       # Skip slow tests

# Generate detailed HTML report
python run_production_tests.py --report

# Run with pytest directly (requires --production flag)
pytest test_production_integration.py --production -v
```

**Note**: Production tests require the `--production` flag to prevent accidental execution during regular development. They test against the actual backend service and perform comprehensive validation of all API endpoints, security, and performance characteristics.

## Known Issues & TODOs
- Test collection scheduling and automation (planned)
- Advanced compliance framework mapping (planned)
- Rate limiting for API endpoints (planned)

## Future Enhancements
- Custom JavaScript support for AI connectors
- Advanced validation criteria
- Automated test scheduling
- Enhanced analytics and visualization
- Compliance template library
- Integration with other GRC tools
- Advanced AI model testing capabilities
- Audit logging for user actions


### Setup first user example:

The following commands are to register and verify a new user. Change the --data-raw to match email, password and verification code.

Register:
curl 'http://localhost/api/v1.0/user/register' -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: http://localhost:5173/login' -H 'Origin: http://localhost:5173' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: no-cors' -H 'Sec-Fetch-Site: same-origin' -H 'DNT: 1' -H 'Sec-GPC: 1' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw 'email=email@gmail.com&password=Pass1word!'

Verify:
curl 'http://localhost/api/v1.0/user/verify_email' -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: http://localhost:5173/login' -H 'Origin: http://localhost:5173' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: no-cors' -H 'Sec-Fetch-Site: same-origin' -H 'DNT: 1' -H 'Sec-GPC: 1' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw 'email=email@gmail.com&password=Pass1word!&verification_code=ERNJCP'

login:
curl 'http://localhost/api/v1.0/user/login' -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://localhost:5173' -H 'Connection: keep-alive' -H 'Referer: http://localhost:5173/login' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'DNT: 1' -H 'Sec-GPC: 1' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw 'username=email%40gmail.com&password=Pass1word%21'