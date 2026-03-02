FROM python:3.10-slim

# Enterprise registry flexibility
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

# Copy optional enterprise certificates and pip configuration if they exist
# We use a wildcard (*) so it doesn't fail if the files are not present in the build context
COPY trustsource.pem* /usr/local/share/ca-certificates/
RUN if ls /usr/local/share/ca-certificates/trustsource.pem* 1> /dev/null 2>&1; then \
    apt-get update && apt-get install -y ca-certificates && update-ca-certificates && rm -rf /var/lib/apt/lists/*; \
    fi
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

COPY pip.ini* pip.conf* /etc/

WORKDIR /app

# Install dependencies
COPY requirements.txt .

# Use custom registry if provided
RUN if [ -n "$PIP_INDEX_URL" ]; then \
    pip install --no-cache-dir --index-url $PIP_INDEX_URL --trusted-host ${PIP_TRUSTED_HOST:-$(echo $PIP_INDEX_URL | awk -F/ '{print $3}' | cut -d: -f1)} -r requirements.txt; \
    else \
    pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

EXPOSE 5001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5001"]
