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

#### Model Testing
- `POST /api/v1.0/model/tests` - Execute model tests

### Storage
- Currently using a local store implementation for tests. Redis for persistant storage
- UUID-based user identification
- Email-based user lookup
- Support for pagination in user listing

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
| Variable                    | Value                                                                                               |
|-----------------------------|-----------------------------------------------------------------------------------------------------|
| SECRET_KEY                  | The secret key used for JWT encode/decode.                                                          |
| ALGORITHM                   | The algorithm used for JWT encode/decode (default is `HS256`).                                      |
| ACCESS_TOKEN_EXPIRE_MINUTES | The number of minutes until a JWT expires (default is `30`).                                        |
| REDIS_ADDRESS               | The URL for the Redis database (default is `localhost`).                                            |
| REDIS_PORT                  | The port for the Redis database (default is `6379`).                                                |
| ORIGINS                     | A comma seperated list of whitelisted origin URLs (e.g., `http://localhost,http://localhost:3000`). |
| SES_AWS_ACCESS_KEY_ID       | AWS IAM access key ID (used for boto3 package).                                                     |
| SES_AWS_SECRET_ACCESS_KEY   | AWS IAM secret access key (used for boto3 package).                                                 |
| SES_AWS_SENDER_EMAIL        | The email address to send the verification emails (this email must be setup with the SES service).  |
| SES_AWS_REGION              | The AWS region for the SES service (default is `ap-southeast-2`).                                   |
| FRONTEND_URL_BASE           | The base URL of the Riskify website page (default is `http://localhost:3000`).                      |
| SUPPORT_EMAIL               | The email address that support requests get sent to (default is `goricoaico@gmail.com`)             |

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

### Running Redis Locally
`docker run -d --rm --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest`  
This will launch a Redis server and will be automatically deleted after the container exits. Visit [http://localhost:8001/](http://localhost:8001/) to view the RedisInsight dashboard.

### Running Tests
- `pip install -r requirements/dev.txt`
- `python -m pytest`

## Known Issues & TODOs
- Admin role check needs to be implemented for user management endpoints
- User listing endpoint currently uses test data (needs to be connected to actual storage)
- Email sender configuration needs to be reviewed
- Authorization checks needed for user operations (admin or self)

## Future Enhancements
- Implement proper role-based access control
- Add database integration for persistent storage
- Enhance user management with more granular permissions
- Add audit logging for user actions
- Implement rate limiting for API endpoints
- Add API versioning strategy
- Enhance test coverage