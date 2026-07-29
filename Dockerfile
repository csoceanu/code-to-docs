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

# Install AsciiDoc validator (asciidoctor.js)
RUN npm install -g @asciidoctor/core @asciidoctor/cli

# Set up working directory
WORKDIR /app

# Copy project metadata and install Python dependencies from pyproject.toml
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/
RUN pip install --no-cache-dir /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set git config for commits
RUN git config --global user.email "action@github.com" && \
    git config --global user.name "GitHub Action"

ENTRYPOINT ["/entrypoint.sh"]
