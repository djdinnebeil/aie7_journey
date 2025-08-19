# Build a lightweight FastAPI app with the user's local library vendored in
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y build-essential wget && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Cache dir
RUN mkdir -p /app/cache

# Copy app
COPY app /app/app

# Copy the user's provided library into /app/lib
# Expecting the following files to be provided by the user at build time
COPY lib /app/lib

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Env for FastAPI
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080" ]
