# Running with tmux on Linux VPS

Complete guide for running the dataset generator in tmux for long-running sessions.

## Quick Start

### 1. Install tmux (if not installed)
```bash
# Ubuntu/Debian
sudo apt install tmux

# CentOS/RHEL
sudo yum install tmux

# Arch
sudo pacman -S tmux
```

### 2. Run the generator in tmux
```bash
chmod +x run_tmux.sh
./run_tmux.sh
```

This will:
- Create a tmux session called "dataset-gen"
- Start the generator
- Attach you to the session

### 3. Detach and let it run
Press: `Ctrl+B`, then `D`

Your session keeps running in the background!

### 4. Reattach anytime
```bash
tmux attach -t dataset-gen
```

## Manual tmux Usage

### Start a new session
```bash
tmux new -s dataset-gen
python3 gemini_cli.py
```

### Detach from session
Press: `Ctrl+B`, then `D`

### List all sessions
```bash
tmux ls
```

### Attach to session
```bash
tmux attach -t dataset-gen
# or shorthand:
tmux a -t dataset-gen
```

### Kill a session
```bash
tmux kill-session -t dataset-gen
```

## tmux Cheat Sheet

### Basic Commands
- `Ctrl+B` - Command prefix (press before any command)
- `Ctrl+B, D` - Detach from session
- `Ctrl+B, C` - Create new window
- `Ctrl+B, N` - Next window
- `Ctrl+B, P` - Previous window
- `Ctrl+B, [` - Scroll mode (use arrow keys, press Q to exit)
- `Ctrl+B, ?` - Show all keybindings

### Session Management
```bash
tmux new -s name          # Create named session
tmux ls                   # List sessions
tmux attach -t name       # Attach to session
tmux kill-session -t name # Kill session
tmux rename-session name  # Rename current session
```

### Window Management
- `Ctrl+B, C` - Create window
- `Ctrl+B, ,` - Rename window
- `Ctrl+B, &` - Kill window
- `Ctrl+B, 0-9` - Switch to window number

### Pane Management
- `Ctrl+B, %` - Split vertically
- `Ctrl+B, "` - Split horizontally
- `Ctrl+B, Arrow` - Navigate panes
- `Ctrl+B, X` - Kill pane

## Example: 10-Hour Generation Run

```bash
# Start tmux session
tmux new -s longrun

# Run the generator
python3 gemini_cli.py

# Enter your configuration:
# Description: Paraphrasing dataset with 4 sentences
# Columns: Original,Paraphrased
# Rows: 50000
# Batch: 100
# Output: dataset_50k.csv

# Detach: Ctrl+B, D

# Check it's running
tmux ls

# Reattach later to check progress
tmux attach -t longrun

# When done, exit normally or kill session
tmux kill-session -t longrun
```

## Advanced: Multiple Generators

Run multiple generators in different windows:

```bash
# Start session
tmux new -s multi-gen

# Run first generator
python3 gemini_cli.py
# Configure for dataset 1

# Create new window: Ctrl+B, C
# Run second generator
python3 gemini_cli.py
# Configure for dataset 2

# Switch between windows: Ctrl+B, 0 or Ctrl+B, 1

# Detach: Ctrl+B, D
```

## Monitoring Progress

### From outside tmux
```bash
# Capture pane content
tmux capture-pane -t dataset-gen -p | tail -20

# Watch progress (updates every 2 seconds)
watch -n 2 'tmux capture-pane -t dataset-gen -p | tail -20'
```

### Inside tmux
- Scroll up: `Ctrl+B, [`, then use arrow keys or Page Up/Down
- Exit scroll mode: Press `Q`

## Logging Output

### Method 1: Pipe to file
```bash
tmux new -s dataset-gen
python3 gemini_cli.py 2>&1 | tee generation.log
```

### Method 2: tmux logging
```bash
# Enable logging for current pane
Ctrl+B, :
pipe-pane -o 'cat >> ~/tmux-output.log'

# Disable logging
Ctrl+B, :
pipe-pane
```

## SSH Disconnection Protection

tmux keeps running even if SSH disconnects!

```bash
# On your VPS
ssh user@your-vps.com
tmux new -s dataset-gen
python3 gemini_cli.py

# Detach: Ctrl+B, D
# Logout: exit

# Later, reconnect
ssh user@your-vps.com
tmux attach -t dataset-gen
```

## Automation Script

Create a script to run multiple datasets:

```bash
#!/bin/bash
# run_multiple.sh

tmux new-session -d -s gen1 "python3 gemini_cli.py < config1.txt"
tmux new-session -d -s gen2 "python3 gemini_cli.py < config2.txt"
tmux new-session -d -s gen3 "python3 gemini_cli.py < config3.txt"

echo "Started 3 generation sessions"
tmux ls
```

## Configuration Files

Create input files for automated runs:

```bash
# config1.txt
History questions and answers
Question,Answer
5000
100
history_qa.csv
y

# config2.txt
Paraphrasing dataset
Original,Paraphrased
10000
100
paraphrasing.csv
y
```

Run with:
```bash
tmux new -s auto1 "python3 gemini_cli.py < config1.txt"
```

## Best Practices

1. **Name your sessions meaningfully:**
   ```bash
   tmux new -s paraphrase-10k
   ```

2. **Use logging:**
   ```bash
   python3 gemini_cli.py 2>&1 | tee generation.log
   ```

3. **Check before starting:**
   ```bash
   tmux ls  # See what's already running
   ```

4. **Monitor system resources:**
   ```bash
   # In a separate tmux window
   htop
   ```

5. **Set up alerts:**
   ```bash
   # Get notified when done
   python3 gemini_cli.py && echo "Done!" | mail -s "Generation Complete" you@email.com
   ```

## Troubleshooting

**Session not found:**
```bash
tmux ls  # Check if it exists
```

**Can't attach:**
```bash
# Kill and restart
tmux kill-session -t dataset-gen
./run_tmux.sh
```

**tmux not installed:**
```bash
sudo apt install tmux
```

**Session disappeared:**
- Check if server rebooted: `uptime`
- Check logs: `cat generation.log`

## Useful Aliases

Add to your `~/.bashrc`:

```bash
alias tls='tmux ls'
alias ta='tmux attach -t'
alias tn='tmux new -s'
alias tk='tmux kill-session -t'
```

Then use:
```bash
tn dataset-gen    # Create new session
ta dataset-gen    # Attach to session
tls               # List sessions
tk dataset-gen    # Kill session
```

## Summary

**Start:**
```bash
./run_tmux.sh
```

**Detach:**
`Ctrl+B, D`

**Reattach:**
```bash
tmux attach -t dataset-gen
```

**Check status:**
```bash
tmux ls
```

That's it! Your generator will run for hours/days even if you disconnect.
