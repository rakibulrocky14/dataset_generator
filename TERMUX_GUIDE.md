# Running on Termux

Simple guide to run the dataset generator on Termux for hours.

## Setup (One-time)

1. **Install Python and dependencies:**
```bash
pkg install python
pip install google-generativeai python-dotenv
```

2. **Create .env file:**
```bash
nano .env
```

Add:
```
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL_NAME=gemini-1.5-flash
```

Save with `Ctrl+X`, then `Y`, then `Enter`

## Run in Foreground

Simple interactive mode:
```bash
python gemini_cli.py
```

## Run in Background (Recommended for long runs)

### Method 1: Using nohup (simplest)
```bash
nohup python gemini_cli.py > output.log 2>&1 &
```

Monitor progress:
```bash
tail -f output.log
```

### Method 2: Using screen (better for interaction)
```bash
# Install screen
pkg install screen

# Start a screen session
screen -S dataset

# Run the generator
python gemini_cli.py

# Detach: Press Ctrl+A, then D
# Your process keeps running!

# Reattach later:
screen -r dataset
```

### Method 3: Using tmux (alternative to screen)
```bash
# Install tmux
pkg install tmux

# Start tmux
tmux new -s dataset

# Run the generator
python gemini_cli.py

# Detach: Press Ctrl+B, then D

# Reattach later:
tmux attach -t dataset
```

## Quick Start Example

```bash
# Start in background
nohup python gemini_cli.py > generation.log 2>&1 &

# Check it's running
ps aux | grep gemini_cli

# Monitor progress
tail -f generation.log

# Or use less to scroll through log
less +F generation.log
```

## Input for Automated Run

Create an input file to avoid typing:
```bash
nano input.txt
```

Add your configuration:
```
Paraphrasing dataset with 4 sentences in each column
Original,Paraphrased
10000
100
dataset.csv
y
```

Run with input file:
```bash
python gemini_cli.py < input.txt > output.log 2>&1 &
```

## Stopping the Process

Find the process:
```bash
ps aux | grep gemini_cli
```

Kill it:
```bash
kill <PID>
```

Or kill all Python processes (careful!):
```bash
pkill -f gemini_cli
```

## Keep Termux Running

To prevent Termux from being killed by Android:

1. **Acquire wakelock:**
```bash
termux-wake-lock
```

2. **Release when done:**
```bash
termux-wake-unlock
```

3. **Or use a persistent notification:**
   - Go to Termux settings
   - Enable "Acquire wakelock"

## Check Progress

While running in background:
```bash
# See latest output
tail -20 generation.log

# Follow live updates
tail -f generation.log

# Search for specific info
grep "Progress:" generation.log | tail -5
```

## Tips for Long Runs

1. **Keep phone charged** - Plug it in!

2. **Prevent sleep:**
```bash
termux-wake-lock
```

3. **Use WiFi** - More stable than mobile data

4. **Check storage:**
```bash
df -h
```

5. **Monitor battery:**
```bash
termux-battery-status
```

## Example: Generate 10,000 rows overnight

```bash
# Acquire wakelock
termux-wake-lock

# Start generation in background
nohup python gemini_cli.py > overnight.log 2>&1 &

# Save the PID
echo $! > generator.pid

# Check it's running
ps aux | grep gemini_cli

# Go to sleep! Check in the morning:
tail overnight.log
```

## Troubleshooting

**Termux killed the process:**
- Use `termux-wake-lock`
- Disable battery optimization for Termux in Android settings

**Out of storage:**
```bash
# Check space
df -h

# Clean up
apt clean
```

**Process not running:**
```bash
# Check if it crashed
tail -50 output.log

# Check for errors
grep -i error output.log
```

## Output Files

After completion, you'll have:
- `dataset.csv` - Your generated data
- `dataset.json` - JSON format
- `dataset.csv.checkpoint` - Checkpoint (saved every 100 rows)
- `output.log` - Full log of the run

Transfer to PC:
```bash
# Using termux-share
termux-share dataset.csv

# Or copy to shared storage
cp dataset.csv ~/storage/downloads/
```
