FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps
# Copy source code (will be overridden by volume in dev)
COPY . .

EXPOSE 8000

# Start development server with hot-reloading
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
