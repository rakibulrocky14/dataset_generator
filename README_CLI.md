# Gemini Dataset Generator - CLI Version

Terminal-based dataset generator perfect for running on VPS for hours.

## Features

- ✅ Runs in terminal (no web browser needed)
- ✅ Colored output with progress tracking
- ✅ Auto-checkpoint saves every 100 rows
- ✅ ETA and rate calculations
- ✅ Can run for hours/days
- ✅ Resume from checkpoint if interrupted
- ✅ Saves both CSV and JSON formats

## Quick Start

### 1. Install Dependencies

```bash
pip install google-generativeai python-dotenv
```

### 2. Configure API Key

Add to your `.env` file:
```
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL_NAME=gemini-1.5-flash
```

### 3. Run Interactively

```bash
python3 gemini_cli.py
```

You'll be prompted for:
- Dataset description
- Column names (comma-separated)
- Total rows to generate
- Batch size (default: 100)
- Output filename

### 4. Run in Background (VPS)

```bash
chmod +x run_background.sh
./run_background.sh
```

Then monitor with:
```bash
tail -f logs/generation_*.log
```

## Example Usage

```bash
$ python3 gemini_cli.py

Dataset description: Paraphrasing dataset with 4 sentences in each column
Columns (comma-separated): Original,Paraphrased
Total rows to generate: 10000
Batch size (default 100): 100
Output filename (default: dataset.csv): paraphrasing_10k.csv

Ready to generate 10000 rows in batches of 100
Start generation? (y/n): y
```

## Output

The script generates:
- `dataset.csv` - Main CSV output
- `dataset.json` - JSON format
- `dataset.csv.checkpoint` - Checkpoint file (auto-saved every 100 rows)

## Progress Display

```
Batch 1: Requesting 100 rows...
  ✓ Received response (15234 chars)
✓ Added 98 rows (duplicates filtered: 2)
Progress: 98/10000 (1.0%)
Rate: 12.3 rows/sec
ETA: 13.4 minutes
API Calls: 1

Latest row sample:
  Original: The cat sat on the mat. It was very comfortable...
  Paraphrased: A feline rested upon the rug. It felt quite cozy...
```

## Stopping the Process

If running in foreground:
- Press `Ctrl+C` to stop gracefully
- Progress will be saved to checkpoint file

If running in background:
```bash
kill $(cat generation.pid)
```

## Resume from Checkpoint

If interrupted, you can manually load the checkpoint file and continue, or restart with a different filename.

## Tips for Long Runs

1. **Use screen or tmux** for better session management:
   ```bash
   screen -S dataset
   python3 gemini_cli.py
   # Detach with Ctrl+A, D
   # Reattach with: screen -r dataset
   ```

2. **Monitor API usage** - Gemini has rate limits, adjust batch size if needed

3. **Check disk space** - Large datasets can be several GB

4. **Use smaller batches** for more frequent checkpoints:
   ```
   Batch size: 50
   ```

## Troubleshooting

**Error: API key not set**
- Check your `.env` file has `GEMINI_API_KEY=...`

**Empty batches**
- Try reducing batch size
- Check your description is clear
- Verify API key has quota remaining

**Out of memory**
- Reduce batch size
- Process in smaller chunks (e.g., 1000 rows at a time)

## Advanced: Automated Runs

Create a config file and run multiple datasets:

```bash
# config.txt
description=History questions and answers
columns=Question,Answer
rows=5000
output=history_qa.csv

# Run with config
python3 gemini_cli.py < config.txt
```
