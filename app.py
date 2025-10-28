from flask import Flask, request, jsonify, send_file
import csv
import io
import threading
import os
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__, static_folder='static', static_url_path='/static')

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

# Validate API key
if not API_KEY or API_KEY == "your_api_key_here":
    raise ValueError("ERROR: API_KEY is not set or is using the default placeholder. Please set a valid API key in your .env file.")

# Initialize OpenAI client
try:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
except Exception as e:
    raise ValueError(f"ERROR: Failed to initialize OpenAI client: {e}")

generated_data = []
dataset_meta = {}
api_call_count = 0
generation_running = False
lock = threading.Lock()


def validate_row_quality(row, columns, description=""):
    """Validate that row meets quality standards"""
    if not row or len(row) != len(columns):
        return False
    
    for cell in row:
        # Check if cell is empty or too short
        if not cell or len(cell.strip()) < 10:
            return False
        
        # Check if cell looks like placeholder text
        if cell.lower() in ['value1', 'value2', 'value3', 'value4', 'example', 'n/a', 'null']:
            return False
        
        # If description mentions "4 sentences" or "multiple sentences", validate minimum length
        if "4 sentence" in description.lower() or "multiple sentence" in description.lower():
            # Each cell should have at least 50 characters for multi-sentence content
            if len(cell.strip()) < 50:
                return False
            # Should have at least 2 periods (indicating multiple sentences)
            if cell.count('.') < 2:
                return False
    
    return True


def generate_with_llm(prompt, columns, batch_size):
    # Calls LLM API (OpenAI-compatible) to generate data as JSON
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a precise dataset generator. Follow the user's description EXACTLY. Output ONLY a valid JSON array of objects, no explanations. Each object represents one complete dataset entry. Ensure the JSON is complete and valid.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=16000,
    )
    
    # Parse JSON response
    import json
    import re
    response_text = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split('\n')
        response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
    
    # Try to extract JSON array if there's extra text
    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(0)
    
    try:
        data = json.loads(response_text)
        if not isinstance(data, list):
            print("[LLM ERROR] Response is not a JSON array")
            return []
        
        rows = []
        for item in data:
            if isinstance(item, dict):
                # Extract values in column order
                row = [str(item.get(col, "")).strip() for col in columns]
                # Only accept rows with correct number of non-empty columns
                if len(row) == len(columns) and all(cell for cell in row):
                    rows.append(row)
        
        print(f"[LLM] Successfully parsed {len(rows)} valid rows from JSON")
        return rows
    except json.JSONDecodeError as e:
        print(f"[LLM ERROR] Failed to parse JSON: {e}")
        print(f"[LLM ERROR] Response text (first 500 chars): {response_text[:500]}")
        # Try to salvage partial data by fixing common issues
        try:
            # Try to fix truncated JSON by closing it
            if not response_text.endswith(']'):
                # Find last complete object
                last_brace = response_text.rfind('}')
                if last_brace > 0:
                    response_text = response_text[:last_brace+1] + ']'
                    data = json.loads(response_text)
                    rows = []
                    for item in data:
                        if isinstance(item, dict):
                            row = [str(item.get(col, "")).strip() for col in columns]
                            if len(row) == len(columns) and all(cell for cell in row):
                                rows.append(row)
                    print(f"[LLM] Recovered {len(rows)} rows from truncated JSON")
                    return rows
        except:
            pass
        return []


@app.route("/generate", methods=["POST"])
def generate_dataset():
    global generated_data, dataset_meta
    try:
        data = request.json
        description = data.get("description")
        columns = data.get("columns")
        total_rows = int(data.get("total_rows"))
        batch_size = int(data.get("batch_size", 50))
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid request data: {e}"}), 400

    global api_call_count, generation_running
    with lock:
        generated_data = []
        dataset_meta = {
            "columns": columns,
            "description": description,
            "total_rows": total_rows,
        }
        api_call_count = 0
        generation_running = True

    def run_batches():
        nonlocal columns, total_rows, batch_size, description
        generated = 0
        empty_batches = 0
        max_empty_batches = 3
        seen = set()
        with lock:
            for row in generated_data:
                seen.add(tuple(row))
        while generated < total_rows:
            # Request up to 2x the remaining rows, capped at 100
            curr_batch = min(max(batch_size, 2 * (total_rows - generated)), 100)
            
            # Build a stronger, more specific prompt  
            # Limit batch size to avoid truncation but keep it reasonable
            curr_batch = min(curr_batch, 50)
            
            prompt = f"""Task: {description}

Generate EXACTLY {curr_batch} entries following the description EXACTLY.

Output format: Valid JSON array of objects with these exact keys: {', '.join(columns)}

CRITICAL: Output ONLY the JSON array, nothing else. Ensure the JSON is complete and valid.

Example:
[
  {{"{columns[0]}": "content here", "{columns[1]}": "content here"}},
  {{"{columns[0]}": "different content", "{columns[1]}": "different content"}}
]

Generate {curr_batch} unique entries:"""
            try:
                rows = generate_with_llm(prompt, columns, curr_batch)
                print(f"[LLM] Generated {len(rows)} rows from API call")
                with lock:
                    global api_call_count
                    api_call_count += 1
            except Exception as e:
                print(f"[LLM ERROR] API call failed: {str(e)}")
                import traceback
                traceback.print_exc()
                rows = []
            if not rows:
                empty_batches += 1
                print(f"[LLM WARNING] Empty batch {empty_batches}/{max_empty_batches}")
                if empty_batches >= max_empty_batches:
                    print("[LLM ERROR] Too many empty batches. Stopping generation.")
                    break
            else:
                empty_batches = 0
                # Deduplicate and validate rows
                new_rows = []
                with lock:
                    for row in rows:
                        # Validate row quality first
                        if not validate_row_quality(row, columns, description):
                            print(f"[LLM WARNING] Skipping low-quality row: {row[:50] if row else row}...")
                            continue
                        
                        trow = tuple(row)
                        if trow not in seen:
                            seen.add(trow)
                            new_rows.append(row)
                    needed = total_rows - len(generated_data)
                    to_add = new_rows[:needed]
                    generated_data.extend(to_add)
                    generated = len(generated_data)
                    print(f"[LLM] Added {len(to_add)} valid rows. Total: {generated}/{total_rows}")
        with lock:
            global generation_running
            generation_running = False

    thread = threading.Thread(target=run_batches)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/progress", methods=["GET"])
def get_progress():
    with lock:
        count = len(generated_data)
        total = dataset_meta.get("total_rows", 0)
        columns = dataset_meta.get("columns", [])
        calls = api_call_count
        error = None
        warning = None
        running = generation_running
        if total > 0 and count < total:
            if count == 0:
                if not running:
                    error = "LLM did not return any valid data. Please check your prompt or try again."
            else:
                if not running:
                    warning = f"LLM could not generate the full requested dataset. Generated {count} out of {total} rows. You can still download the partial CSV."
    return jsonify(
        {
            "generated": count,
            "total": total,
            "columns": columns,
            "api_calls": calls,
            "error": error,
            "warning": warning,
            "running": running,
        }
    )


@app.route("/download", methods=["GET"])
def download_csv():
    with lock:
        columns = dataset_meta.get("columns", [])
        rows = generated_data.copy()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="dataset.csv",
    )


@app.route("/download_json", methods=["GET"])
def download_json():
    with lock:
        columns = dataset_meta.get("columns", [])
        rows = generated_data.copy()

    # Convert to list of dictionaries
    json_data = []
    for row in rows:
        # Only process rows with correct column count
        if len(row) == len(columns):
            row_dict = {columns[i]: row[i] for i in range(len(columns))}
            json_data.append(row_dict)

    import json
    json_string = json.dumps(json_data, indent=2, ensure_ascii=False)

    return send_file(
        io.BytesIO(json_string.encode('utf-8')),
        mimetype="application/json",
        as_attachment=True,
        download_name="dataset.json",
    )


@app.route("/csv_live", methods=["GET"])
def csv_live():
    """Stream or show the full CSV live (for frontend preview)."""
    with lock:
        columns = dataset_meta.get("columns", [])
        rows = generated_data.copy()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    output.seek(0)
    return output.getvalue(), 200, {"Content-Type": "text/csv"}


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True)
