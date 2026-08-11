# Base image
FROM amazonlinux:2023 AS builder

# Install Python and build dependencies
RUN yum install -y python3.12 python3.12-devel gcc make git tar gzip

RUN python3.12 -m ensurepip --upgrade
RUN python3.12 -m pip install --upgrade pip

# Set working directory in the container
WORKDIR /app

# Copy metadata harmonization API and processor
COPY projects/api /app/projects/api
COPY projects/metadata-harmonization-processor /app/projects/metadata-harmonization-processor

# Install the packages
RUN pip3.12 install --no-cache-dir '/app/projects/metadata-harmonization-processor'
RUN pip3.12 install --no-cache-dir '/app/projects/api'

# Second stage - minimal runtime image
FROM amazonlinux:2023

# Install AWS CLI, Session Manager Plugin, and curl for health checks
# RUN yum install -y unzip aws-cli curl && \
#     curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm" -o "session-manager-plugin.rpm" && \
#     yum install -y ./session-manager-plugin.rpm && \
#     rm session-manager-plugin.rpm

# Copy the entire Python installation from the builder stage
COPY --from=builder /usr /usr
COPY --from=builder /lib64 /lib64

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Set working directory
WORKDIR /app

# Copy the entrypoint script
COPY projects/infra/lib/api/entrypoint.sh /app/entrypoint.sh

# Copy the configuration file to the application directory
COPY projects/api/config.yaml /app/config.yaml

# Copy the schema data directory to where the app expects it
COPY data/schema /app/data/schema

# Set environment variables (API will search multiple locations as fallback)
ENV CONFIG_PATH=/app/config.yaml

# Create a non-root user for running the application
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appuser /app

# Expose the API port
EXPOSE 8080

# Run as non-root user
USER appuser

# Health check against the unauthenticated /api/health route. Uses Python rather
# than curl because curl is not installed in this runtime stage.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python3.12 -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/api/health', timeout=3).status == 200 else 1)"

# Set the entrypoint script
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
