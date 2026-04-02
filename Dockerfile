# Multi-stage production build
FROM python:3.12-alpine AS builder

WORKDIR /app

# Install build dependencies for native extensions
RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final production image avoiding bloated toolchains
FROM python:3.12-alpine

# Set non-privileged user for security compliance mapping to Top 1% requirements
RUN addgroup -S finguard && adduser -S finguard -G finguard 

WORKDIR /app

# Copy built wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .

# Adjust permissions for sqlite write access if using local DB
RUN chown -R finguard:finguard /app

USER finguard

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
