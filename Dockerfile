FROM registry.access.redhat.com/ubi10/python-312-minimal:latest

# Switch to root user for package installation
USER root

# Install system dependencies
RUN microdnf install -y git jq nodejs npm tar && microdnf clean all

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/rpm/gh-cli.repo | tee /etc/yum.repos.d/github-cli.repo \
    && microdnf install -y gh && microdnf clean all

# Install Google Workspace CLI (for fetching Google Docs)
RUN npm install -g @googleworkspace/cli

# Install uv (Python package runner, needed for mcp-atlassian)
RUN pip install --no-cache-dir -U uv

# Install Python dependencies
RUN pip install --no-cache-dir -U openai mcp mcp-atlassian

# Set up working directory
WORKDIR /app

# Copy the scripts
COPY scripts/suggest_docs.py /app/suggest_docs.py
COPY scripts/security_utils.py /app/security_utils.py
COPY scripts/doc_index.py /app/doc_index.py
COPY scripts/jira_integration.py /app/jira_integration.py

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set git config for commits
RUN git config --global user.email "action@github.com" && \
    git config --global user.name "GitHub Action"

ENTRYPOINT ["/entrypoint.sh"]
