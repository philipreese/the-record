FROM ghcr.io/prefix-dev/pixi:latest

WORKDIR /app

# Copy lock and project files first to cache dependencies
COPY pixi.toml pixi.lock ./

# Install default environment (locked for exact reproduction)
RUN pixi install --locked -v

# Copy backend app source code
COPY backend/app ./backend/app

# Expose default port
EXPOSE 8000

# Set production environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start server using pixi run
CMD ["sh", "-c", "pixi run python -m uvicorn --app-dir backend app.main:app --host 0.0.0.0 --port ${PORT}"]
