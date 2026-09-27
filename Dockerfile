FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY lr_agent ./lr_agent
RUN pip install --no-cache-dir .

RUN mkdir -p /app/workspace /app/data

EXPOSE 8765
CMD ["lr-agent", "serve", "--host", "0.0.0.0", "--port", "8765"]
