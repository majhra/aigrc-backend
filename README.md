
# AI GRC backend API

API Server For:
- Corporate AI Governance Risk and Compliance (GRC) model

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
| SUPPORT_EMAIL               | The email address that support requests get sent to (default is `goricoaico@gmail.com`)      |
                                       |

## Local Machine FastApi
`uvicorn app.main:app --reload`

Then you can access it as directed (usually http://127.0.0.1:8000)
access the docs via:  http://127.0.0.1:8000/docs

## Run Docker Locally [This will also run pytest on Docker]
Comment out AWS Docker and remove comment for Local in server/Dockerfile
- Docker-compose build
- Docker-compose up

you can then connect to it via http://127.0.0.1:8888/docs

## Run Redis Docker Locally
`docker run -d --rm --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest`  
This will launch a Redis server and will be automatically deleted after the container exits. Visit [http://localhost:8001/](http://localhost:8001/) to view the RedisInsight dashboard.

## Run Tests locally
- `pip install -r requirements/dev.txt`
- `python -m pytest`