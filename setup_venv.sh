#!/bin/bash
# Setup virtual environment for the dataset generator

echo "Setting up virtual environment..."

# Install python3-venv if not installed
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv python3-pip
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install google-generativeai python-dotenv

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
