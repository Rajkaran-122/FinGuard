# Multi-stage production build
FROM python:3.12-alpine AS builder

WORKDIR /app

# Install build dependencies for native extensions (psycopg2, etc.)
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final production image avoiding bloated toolchains
FROM python:3.12-alpine

# Install runtime dependencies
RUN apk add --no-cache libpq

# Set non-privileged user for security compliance
RUN addgroup -S finguard && adduser -S finguard -G finguard 

WORKDIR /app

# Copy built wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .

# Adjust permissions
RUN chown -R finguard:finguard /app

USER finguard

EXPOSE 8000

# Gunicorn + Uvicorn worker for production performance and stability
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4", "app.main:app"]
