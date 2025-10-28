#!/bin/bash
# Run Gemini Dataset Generator in tmux session

SESSION_NAME="dataset-gen"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed"
    echo "Install with: sudo apt install tmux"
    exit 1
fi

# Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists!"
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session: tmux attach -t $SESSION_NAME"
    echo "  2. Kill existing session: tmux kill-session -t $SESSION_NAME"
    exit 1
fi

# Show usage if help requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  Interactive mode (no arguments):"
    echo "    $0"
    echo ""
    echo "  With command line arguments:"
    echo "    $0 -d \"Description\" -c \"Col1,Col2\" -n 10000 -o output.csv"
    echo ""
    echo "  With config file:"
    echo "    $0 --config config.json"
    echo ""
    echo "Arguments:"
    echo "  -d, --description   Dataset description"
    echo "  -c, --columns       Comma-separated column names"
    echo "  -n, --rows          Total rows to generate"
    echo "  -b, --batch         Batch size (default: 100)"
    echo "  -o, --output        Output filename (default: dataset.csv)"
    echo "  --config            JSON config file"
    echo "  -y, --yes           Skip confirmation"
    echo ""
    echo "Examples:"
    echo "  # Interactive"
    echo "  $0"
    echo ""
    echo "  # With arguments"
    echo "  $0 -d \"Paraphrasing dataset\" -c \"Original,Paraphrased\" -n 10000 -y"
    echo ""
    echo "  # With config"
    echo "  $0 --config my_config.json -y"
    exit 0
fi

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Setting up automatically..."
    
    # Check if python3-venv is installed
    if ! dpkg -l | grep -q python3-venv 2>/dev/null; then
        echo "Installing python3-venv..."
        sudo apt update && sudo apt install -y python3-venv python3-full python3-pip
    fi
    
    # Create venv
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    # Install dependencies
    echo "Installing dependencies..."
    venv/bin/pip install --upgrade pip setuptools wheel
    venv/bin/pip install google-generativeai python-dotenv
    
    echo "✓ Setup complete!"
fi

# Verify dependencies are installed
if ! venv/bin/python -c "import google.generativeai" 2>/dev/null; then
    echo "Installing missing dependencies..."
    venv/bin/pip install google-generativeai python-dotenv
fi

PYTHON="venv/bin/python"
echo "Using virtual environment"

# Build command with all arguments passed to this script
# Use array to properly handle arguments with spaces
CMD_ARRAY=("$PYTHON" "gemini_cli.py" "$@")
CMD="$PYTHON gemini_cli.py $@"

# Create new tmux session and run the generator
echo "Creating tmux session: $SESSION_NAME"
echo ""
echo "Command: $CMD"
echo ""
echo "The generator will run in a tmux session."
echo "To detach: Press Ctrl+B, then D"
echo "To reattach: tmux attach -t $SESSION_NAME"
echo ""

# Start tmux session in detached mode and run the generator
# Use proper quoting to handle arguments with spaces
tmux new-session -d -s $SESSION_NAME "cd '$PWD' && $PYTHON gemini_cli.py $(printf '%q ' "$@"); echo ''; echo 'Generation complete. Press Enter to exit.'; read"

echo "✓ Session created successfully!"
echo ""
echo "Commands:"
echo "  Attach to session:  tmux attach -t $SESSION_NAME"
echo "  List sessions:      tmux ls"
echo "  Kill session:       tmux kill-session -t $SESSION_NAME"
echo ""
echo "Attaching to session in 2 seconds..."
sleep 2

# Attach to the session
tmux attach -t $SESSION_NAME
