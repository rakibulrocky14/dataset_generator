#!/bin/bash
# Run the dataset generator in the background on VPS

echo "Starting Gemini Dataset Generator in background..."

# Create logs directory
mkdir -p logs

# Get timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOGFILE="logs/generation_${TIMESTAMP}.log"

# Run in background with nohup
nohup python3 gemini_cli.py > "$LOGFILE" 2>&1 &

# Get the process ID
PID=$!

echo "✓ Started with PID: $PID"
echo "✓ Log file: $LOGFILE"
echo ""
echo "To monitor progress:"
echo "  tail -f $LOGFILE"
echo ""
echo "To stop the process:"
echo "  kill $PID"
echo ""
echo "Process ID saved to: generation.pid"

# Save PID to file
echo $PID > generation.pid
