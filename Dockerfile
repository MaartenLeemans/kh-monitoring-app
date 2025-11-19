FROM python:3.12-slim

# Vereiste dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Start productie server (niet de Flask dev server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
