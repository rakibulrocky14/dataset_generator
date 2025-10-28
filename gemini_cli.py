#!/usr/bin/env python3
"""
Gemini Dataset Generator - CLI Version
Run for hours on Termux/VPS to generate large datasets
"""

import os
import csv
import json
import time
import sys
import argparse
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# Load environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
    print("ERROR: GEMINI_API_KEY is not set in .env file")
    exit(1)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def validate_row_quality(row, columns):
    """Validate row quality"""
    if not row or len(row) != len(columns):
        return False
    for cell in row:
        if not cell or len(cell.strip()) == 0:
            return False
        if cell.lower() in ['value1', 'value2', 'example', 'n/a', 'null', 'none']:
            return False
    return True

def generate_batch(description, columns, batch_size):
    """Generate a batch of data using Gemini"""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": 1,
            "max_output_tokens": 32000,
            "response_mime_type": "application/json",
        }
    )
    
    prompt = f"""Task: {description}

Generate EXACTLY {batch_size} entries following the description EXACTLY.

Output a JSON array of objects with these exact keys: {', '.join(columns)}

Example format:
[
  {{"{columns[0]}": "content here", "{columns[1]}": "content here"}},
  {{"{columns[0]}": "different content", "{columns[1]}": "different content"}}
]

Generate {batch_size} unique, diverse entries now."""
    
    try:
        print(f"{Colors.CYAN}  → Calling Gemini API...{Colors.ENDC}", end='', flush=True)
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"\r{Colors.GREEN}  ✓ Received response ({len(response_text)} chars){Colors.ENDC}")
        
        # Parse JSON
        data = json.loads(response_text)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        
        if not isinstance(data, list):
            print_error("Response is not a JSON array")
            return []
        
        # Convert to rows
        rows = []
        for item in data:
            if isinstance(item, dict):
                row = [str(item.get(col, "")).strip() for col in columns]
                if validate_row_quality(row, columns):
                    rows.append(row)
        
        return rows
        
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse JSON: {e}")
        return []
    except Exception as e:
        print_error(f"API call failed: {e}")
        return []

def save_checkpoint(filename, columns, rows):
    """Save current progress to CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Gemini Dataset Generator - CLI Mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 gemini_cli.py
  
  # With arguments
  python3 gemini_cli.py -d "Paraphrasing dataset" -c "Original,Paraphrased" -n 10000 -o dataset.csv
  
  # With config file
  python3 gemini_cli.py --config config.json
        """
    )
    
    parser.add_argument('-d', '--description', help='Dataset description')
    parser.add_argument('-c', '--columns', help='Comma-separated column names')
    parser.add_argument('-n', '--rows', type=int, help='Total rows to generate')
    parser.add_argument('-b', '--batch', type=int, default=100, help='Batch size (default: 100)')
    parser.add_argument('-o', '--output', default='dataset.csv', help='Output filename (default: dataset.csv)')
    parser.add_argument('--config', help='JSON config file with all parameters')
    parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print_header("Gemini Dataset Generator - CLI Mode")
    
    # Load from config file if provided
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            description = config.get('description')
            columns = config.get('columns', [])
            total_rows = config.get('rows')
            batch_size = config.get('batch_size', 100)
            output_file = config.get('output', 'dataset.csv')
            print_success(f"Loaded configuration from {args.config}")
        except Exception as e:
            print_error(f"Failed to load config file: {e}")
            return
    # Use command line arguments if provided
    elif args.description and args.columns and args.rows:
        description = args.description
        columns = [col.strip() for col in args.columns.split(',')]
        total_rows = args.rows
        batch_size = args.batch
        output_file = args.output
    # Interactive mode
    else:
        print(f"{Colors.BOLD}Configuration:{Colors.ENDC}")
        description = input(f"{Colors.CYAN}Dataset description: {Colors.ENDC}")
        columns_input = input(f"{Colors.CYAN}Columns (comma-separated): {Colors.ENDC}")
        columns = [col.strip() for col in columns_input.split(',')]
        total_rows = int(input(f"{Colors.CYAN}Total rows to generate: {Colors.ENDC}"))
        batch_size = int(input(f"{Colors.CYAN}Batch size (default 100): {Colors.ENDC}") or "100")
        output_file = input(f"{Colors.CYAN}Output filename (default: dataset.csv): {Colors.ENDC}") or "dataset.csv"
    
    print_info(f"Model: {MODEL_NAME}")
    print_info(f"Output: {output_file}")
    print_info(f"Columns: {', '.join(columns)}")
    
    # Confirm (skip if -y flag)
    if not args.yes:
        print(f"\n{Colors.YELLOW}Ready to generate {total_rows} rows in batches of {batch_size}{Colors.ENDC}")
        confirm = input(f"{Colors.CYAN}Start generation? (y/n): {Colors.ENDC}")
        if confirm.lower() != 'y':
            print_warning("Cancelled")
            return
    else:
        print_success("Auto-confirmed with -y flag")
    
    # Start generation
    print_header("Starting Generation")
    start_time = time.time()
    generated_data = []
    seen = set()
    api_calls = 0
    empty_batches = 0
    max_empty_batches = 3
    
    checkpoint_interval = 100  # Save every 100 rows
    last_checkpoint = 0
    
    while len(generated_data) < total_rows:
        current_batch = min(batch_size, total_rows - len(generated_data))
        
        print(f"\n{Colors.BOLD}Batch {api_calls + 1}:{Colors.ENDC} Requesting {current_batch} rows...")
        
        try:
            rows = generate_batch(description, columns, current_batch)
            api_calls += 1
            
            if not rows:
                empty_batches += 1
                print_warning(f"Empty batch ({empty_batches}/{max_empty_batches})")
                if empty_batches >= max_empty_batches:
                    print_error("Too many empty batches. Stopping.")
                    break
                continue
            
            empty_batches = 0
            
            # Deduplicate
            new_rows = []
            for row in rows:
                trow = tuple(row)
                if trow not in seen:
                    seen.add(trow)
                    new_rows.append(row)
            
            # Add to dataset
            needed = total_rows - len(generated_data)
            to_add = new_rows[:needed]
            generated_data.extend(to_add)
            
            # Progress
            progress = len(generated_data)
            percent = (progress / total_rows) * 100
            elapsed = time.time() - start_time
            rate = progress / elapsed if elapsed > 0 else 0
            eta = (total_rows - progress) / rate if rate > 0 else 0
            
            print_success(f"Added {len(to_add)} rows (duplicates filtered: {len(rows) - len(new_rows)})")
            print(f"{Colors.BOLD}Progress:{Colors.ENDC} {progress}/{total_rows} ({percent:.1f}%)")
            print(f"{Colors.BOLD}Rate:{Colors.ENDC} {rate:.1f} rows/sec")
            print(f"{Colors.BOLD}ETA:{Colors.ENDC} {eta/60:.1f} minutes")
            print(f"{Colors.BOLD}API Calls:{Colors.ENDC} {api_calls}")
            
            # Checkpoint save
            if progress - last_checkpoint >= checkpoint_interval:
                checkpoint_file = f"{output_file}.checkpoint"
                save_checkpoint(checkpoint_file, columns, generated_data)
                print_info(f"Checkpoint saved: {checkpoint_file}")
                last_checkpoint = progress
            
            # Show sample of latest row
            if to_add:
                print(f"\n{Colors.CYAN}Latest row sample:{Colors.ENDC}")
                for i, col in enumerate(columns):
                    value = to_add[-1][i][:100] + "..." if len(to_add[-1][i]) > 100 else to_add[-1][i]
                    print(f"  {col}: {value}")
            
        except KeyboardInterrupt:
            print_warning("\n\nInterrupted by user")
            break
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    # Final save
    print_header("Saving Final Dataset")
    save_checkpoint(output_file, columns, generated_data)
    
    # Summary
    elapsed = time.time() - start_time
    print_header("Generation Complete")
    print_success(f"Generated {len(generated_data)} rows")
    print_info(f"API calls: {api_calls}")
    print_info(f"Time elapsed: {elapsed/60:.1f} minutes")
    print_info(f"Average rate: {len(generated_data)/elapsed:.1f} rows/sec")
    print_info(f"Output file: {output_file}")
    
    # Also save as JSON
    json_file = output_file.replace('.csv', '.json')
    json_data = []
    for row in generated_data:
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        json_data.append(row_dict)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print_success(f"Also saved as JSON: {json_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nExiting...")
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
