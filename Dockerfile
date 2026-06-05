FROM python:3.12-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files & buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

# Copy dependencies first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies using system Python inside the container
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Run the Django dev server
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
