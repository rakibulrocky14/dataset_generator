#!/bin/bash
# Setup virtual environment for the dataset generator

echo "Setting up virtual environment..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Install python3-venv if not installed
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv and python3-full..."
    sudo apt update
    sudo apt install -y python3-venv python3-full python3-pip
fi

# Remove old venv if it exists and has issues
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate and install dependencies
echo "Installing dependencies..."
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install dependencies with specific versions that work
echo "Installing google-generativeai..."
pip install google-generativeai

echo "Installing python-dotenv..."
pip install python-dotenv

# Verify installation
echo ""
echo "Verifying installation..."
python -c "import google.generativeai as genai; print('✓ google-generativeai installed')" 2>/dev/null && echo "✓ Success" || echo "✗ Failed"
python -c "from dotenv import load_dotenv; print('✓ python-dotenv installed')" 2>/dev/null && echo "✓ Success" || echo "✗ Failed"

echo ""
echo "✓ Setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Then run:"
echo "  python gemini_cli.py"
echo "  or"
echo "  ./run_tmux.sh"
echo ""
echo "To deactivate:"
echo "  deactivate"
