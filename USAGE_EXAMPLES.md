# Usage Examples

## Method 1: Interactive Mode

Just run and answer the prompts:

```bash
python3 gemini_cli.py
```

You'll be asked:
- Dataset description
- Column names
- Number of rows
- Batch size
- Output filename

## Method 2: Command Line Arguments

Pass everything as arguments:

```bash
python3 gemini_cli.py \
  -d "Paraphrasing dataset with 4 sentences in each column" \
  -c "Original,Paraphrased" \
  -n 10000 \
  -b 100 \
  -o paraphrasing_10k.csv \
  -y
```

Arguments:
- `-d` = Description
- `-c` = Columns (comma-separated)
- `-n` = Number of rows
- `-b` = Batch size (optional, default 100)
- `-o` = Output file (optional, default dataset.csv)
- `-y` = Skip confirmation (auto-start)

## Method 3: Config File

Create a JSON config file:

```json
{
  "description": "History questions and answers dataset",
  "columns": ["Question", "Answer"],
  "rows": 5000,
  "batch_size": 100,
  "output": "history_qa.csv"
}
```

Run with:
```bash
python3 gemini_cli.py --config my_config.json -y
```

## With tmux (Recommended for long runs)

### Interactive in tmux:
```bash
./run_tmux.sh
```

### With arguments in tmux:
```bash
./run_tmux.sh -d "Paraphrasing dataset" -c "Original,Paraphrased" -n 10000 -y
```

### With config in tmux:
```bash
./run_tmux.sh --config config.json -y
```

Then detach with `Ctrl+B, D` and let it run!

## Real-World Examples

### Example 1: Small test run
```bash
python3 gemini_cli.py \
  -d "Simple Q&A pairs" \
  -c "Question,Answer" \
  -n 100 \
  -o test.csv \
  -y
```

### Example 2: Large paraphrasing dataset
```bash
./run_tmux.sh \
  -d "Paraphrasing dataset where each row has 4 sentences in original and 4 in paraphrased" \
  -c "Original,Paraphrased" \
  -n 50000 \
  -b 100 \
  -o paraphrasing_50k.csv \
  -y
```

### Example 3: Multiple columns
```bash
python3 gemini_cli.py \
  -d "Product reviews with sentiment" \
  -c "Product,Review,Sentiment,Rating" \
  -n 10000 \
  -o reviews.csv \
  -y
```

### Example 4: Using config file
```bash
# Create config
cat > my_dataset.json << EOF
{
  "description": "Code snippets with explanations",
  "columns": ["Code", "Explanation", "Language"],
  "rows": 5000,
  "batch_size": 50,
  "output": "code_snippets.csv"
}
EOF

# Run with config
./run_tmux.sh --config my_dataset.json -y
```

## Multiple Datasets in Parallel

Run multiple generators in different tmux sessions:

```bash
# Dataset 1
tmux new -d -s gen1 "python3 gemini_cli.py --config config1.json -y"

# Dataset 2
tmux new -d -s gen2 "python3 gemini_cli.py --config config2.json -y"

# Dataset 3
tmux new -d -s gen3 "python3 gemini_cli.py --config config3.json -y"

# Check all sessions
tmux ls

# Attach to any session
tmux attach -t gen1
```

## Monitoring

### Check progress
```bash
tmux attach -t dataset-gen
```

### Capture output without attaching
```bash
tmux capture-pane -t dataset-gen -p | tail -20
```

### Watch progress
```bash
watch -n 5 'tmux capture-pane -t dataset-gen -p | tail -20'
```

## Tips

1. **Always use `-y` flag in tmux** to skip confirmation:
   ```bash
   ./run_tmux.sh -d "..." -c "..." -n 10000 -y
   ```

2. **Test with small numbers first:**
   ```bash
   python3 gemini_cli.py -d "Test" -c "A,B" -n 10 -y
   ```

3. **Use descriptive output names:**
   ```bash
   -o "paraphrasing_10k_$(date +%Y%m%d).csv"
   ```

4. **Save your configs:**
   ```bash
   # Create reusable configs
   mkdir configs
   # Edit and save
   nano configs/paraphrasing.json
   # Run anytime
   ./run_tmux.sh --config configs/paraphrasing.json -y
   ```

## Quick Reference

```bash
# Interactive
python3 gemini_cli.py

# With args
python3 gemini_cli.py -d "DESC" -c "COL1,COL2" -n 1000 -y

# With config
python3 gemini_cli.py --config file.json -y

# In tmux (interactive)
./run_tmux.sh

# In tmux (with args)
./run_tmux.sh -d "DESC" -c "COL1,COL2" -n 1000 -y

# In tmux (with config)
./run_tmux.sh --config file.json -y

# Detach from tmux
Ctrl+B, D

# Reattach to tmux
tmux attach -t dataset-gen

# List tmux sessions
tmux ls

# Kill tmux session
tmux kill-session -t dataset-gen
```
