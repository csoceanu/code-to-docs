FROM registry.access.redhat.com/ubi9/python-311:latest

# Switch to root user for package installation
USER root

# Install system dependencies
RUN dnf update -y && dnf install -y \
    git \
    curl \
    && dnf clean all

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/rpm/gh-cli.repo | tee /etc/yum.repos.d/github-cli.repo \
    && dnf install -y gh

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
