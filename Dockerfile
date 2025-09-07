FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install gh -y

# Install Python dependencies
RUN pip install --no-cache-dir google-generativeai>=0.8.0

# Set up working directory
WORKDIR /app

# Copy the original script
COPY scripts/suggest_docs.py /app/suggest_docs.py

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set git config for commits
RUN git config --global user.email "action@github.com" && \
    git config --global user.name "GitHub Action"

ENTRYPOINT ["/entrypoint.sh"]
