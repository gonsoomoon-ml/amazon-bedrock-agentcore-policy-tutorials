#!/bin/bash

#####################################
# Get kernel name from argument
#####################################
KERNEL_NAME="${1:-agentcore_policy}"
export VirtualEnv=".venv"

echo "Setting up virtual environment: $VirtualEnv"
echo "Kernel name: $KERNEL_NAME"

#####################################
# Install uv if not already installed
#####################################
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    if ! command -v uv &> /dev/null; then
        echo "Error: UV installation failed"
        exit 1
    fi
fi

export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "Error: UV is not accessible. Please restart your terminal or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

echo "UV is ready: $(uv --version)"

#####################################
# Create virtual environment
#####################################
echo "## Creating virtual environment"
uv python install 3.10
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python 3.10"
    exit 1
fi

# Remove existing .venv if exists (to avoid prompt)
if [ -d ".venv" ]; then
    echo "Removing existing .venv..."
    rm -rf .venv
fi

uv venv --python 3.10
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

#####################################
# Activate the virtual environment
#####################################
echo "## Activating virtual environment"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment activation script not found"
    exit 1
fi

echo "Python: $(which python)"
echo "Version: $(python --version)"

#####################################
# Install packages from pyproject.toml
#####################################
echo "## Installing packages from pyproject.toml"
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found"
    exit 1
fi

uv sync
if [ $? -ne 0 ]; then
    echo "Error: Failed to sync packages"
    exit 1
fi

#####################################
# Register Jupyter kernel
#####################################
echo "## Registering Jupyter kernel: $KERNEL_NAME"
uv run python -m ipykernel install --user --name="$KERNEL_NAME" --display-name "$KERNEL_NAME (Python 3.10)"
if [ $? -eq 0 ]; then
    echo "✓ Jupyter kernel '$KERNEL_NAME' registered successfully"
else
    echo "Warning: Jupyter kernel registration failed"
fi

#####################################
# Show installed packages
#####################################
echo ""
echo "## Installed packages"
uv pip list | grep -E "boto3|bedrock|requests|jupyter" || echo "Core packages installed"
echo ""

#####################################
# Show usage
#####################################
echo "=============================================="
echo "Setup completed successfully!"
echo "=============================================="
echo ""
echo "To activate: source .venv/bin/activate"
echo "To run Jupyter: uv run jupyter lab"
echo ""
echo "In VS Code:"
echo "  1. Open a notebook"
echo "  2. Select kernel: $KERNEL_NAME"
echo ""
