"""
AWS Lambda entry point (serverless deployment option).

API Gateway -> Lambda -> this handler -> the same FastAPI app.
Mangum translates API Gateway / Lambda Function URL events into ASGI
requests, so no code changes are needed to go serverless.

Handler setting in Lambda:  backend.lambda_handler.handler
Required env vars: SECRET_KEY, DATABASE_URL, STORAGE_PROVIDER=s3, S3_BUCKET, ...
"""

from mangum import Mangum

from backend.app import app

handler = Mangum(app, lifespan="auto")
