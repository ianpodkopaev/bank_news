# Custom Dockerfile for Crawlab with automatic spider upload
FROM crawlabteam/crawlab:0.6.3

# Switch to root user to install additional packages
USER root

# Fix Google Chrome GPG key issue and install dependencies
RUN rm -f /etc/apt/sources.list.d/google-chrome.list || true && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Crawlab SDK
RUN pip3 install crawlab-sdk

# Copy the initialization script
COPY init-spiders.sh /app/init-spiders.sh

# Make the initialization script executable
RUN chmod +x /app/init-spiders.sh

# Create a custom entrypoint that waits for Crawlab to be ready and then uploads spiders
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the custom entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
