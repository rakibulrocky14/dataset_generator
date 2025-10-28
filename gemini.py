from flask import Flask, request, jsonify, send_file
import csv
import io
import threading
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

app = Flask(__name__, static_folder='static', static_url_path='/static')

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# Validate API key
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
    raise ValueError("ERROR: GEMINI_API_KEY is not set. Please set it in your .env file.")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

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
        # Check if cell is empty
        if not cell or len(cell.strip()) == 0:
            return False
        
        # Check if cell looks like obvious placeholder text
        if cell.lower() in ['value1', 'value2', 'example', 'n/a', 'null', 'none']:
            return False
    
    return True


streaming_content = []

def generate_with_gemini(prompt, columns, batch_size):
    """Generate data using Gemini's streaming JSON mode"""
    global streaming_content
    try:
        # Create model with JSON response format
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "temperature": 1,
                "max_output_tokens": 32000,
                "response_mime_type": "application/json",
            }
        )
        
        # Use streaming to show progress
        response_text = ""
        with lock:
            streaming_content.append({"status": "generating", "text": ""})
            stream_index = len(streaming_content) - 1
        
        response = model.generate_content(prompt, stream=True)
        
        import time
        chunk_count = 0
        for chunk in response:
            if chunk.text:
                response_text += chunk.text
                chunk_count += 1
                with lock:
                    streaming_content[stream_index]["text"] = response_text
                print(f"[GEMINI STREAM] Chunk {chunk_count}, length: {len(response_text)}")
                # Small delay every few chunks to make streaming visible
                if chunk_count % 3 == 0:
                    time.sleep(0.05)
        
        with lock:
            streaming_content[stream_index]["status"] = "complete"
        
        # Parse JSON response (Gemini guarantees valid JSON with response_mime_type)
        data = json.loads(response_text)
        
        # Handle both array and object with "data" key
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        
        if not isinstance(data, list):
            print("[GEMINI ERROR] Response is not a JSON array")
            return []
        
        rows = []
        for item in data:
            if isinstance(item, dict):
                # Extract values in column order
                row = [str(item.get(col, "")).strip() for col in columns]
                # Only accept rows with correct number of non-empty columns
                if len(row) == len(columns) and all(cell for cell in row):
                    rows.append(row)
        
        print(f"[GEMINI] Successfully parsed {len(rows)} valid rows from JSON")
        return rows
        
    except json.JSONDecodeError as e:
        print(f"[GEMINI ERROR] Failed to parse JSON: {e}")
        print(f"[GEMINI ERROR] Response text: {response_text[:500] if response_text else 'empty'}")
        return []
    except Exception as e:
        print(f"[GEMINI ERROR] API call failed: {e}")
        import traceback
        traceback.print_exc()
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

    global api_call_count, generation_running, streaming_content
    with lock:
        generated_data = []
        streaming_content = []
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
            curr_batch = min(curr_batch, 1000)
            
            prompt = f"""Task: {description}

Generate EXACTLY {curr_batch} entries following the description EXACTLY.

Output a JSON array of objects with these exact keys: {', '.join(columns)}

Example format:
[
  {{"{columns[0]}": "content here", "{columns[1]}": "content here"}},
  {{"{columns[0]}": "different content", "{columns[1]}": "different content"}}
]

Generate {curr_batch} unique, diverse entries now."""
            
            try:
                rows = generate_with_gemini(prompt, columns, curr_batch)
                print(f"[GEMINI] Generated {len(rows)} rows from API call")
                with lock:
                    global api_call_count
                    api_call_count += 1
            except Exception as e:
                print(f"[GEMINI ERROR] API call failed: {str(e)}")
                import traceback
                traceback.print_exc()
                rows = []
            
            if not rows:
                empty_batches += 1
                print(f"[GEMINI WARNING] Empty batch {empty_batches}/{max_empty_batches}")
                if empty_batches >= max_empty_batches:
                    print("[GEMINI ERROR] Too many empty batches. Stopping generation.")
                    break
            else:
                empty_batches = 0
                # Deduplicate and validate rows
                new_rows = []
                with lock:
                    for row in rows:
                        # Validate row quality first
                        if not validate_row_quality(row, columns, description):
                            continue
                        
                        trow = tuple(row)
                        if trow not in seen:
                            seen.add(trow)
                            new_rows.append(row)
                    needed = total_rows - len(generated_data)
                    to_add = new_rows[:needed]
                    generated_data.extend(to_add)
                    generated = len(generated_data)
                    print(f"[GEMINI] Added {len(to_add)} valid rows. Total: {generated}/{total_rows}")
        
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
        stream_data = streaming_content.copy() if streaming_content else []
        
        if total > 0 and count < total:
            if count == 0:
                if not running:
                    error = "Gemini did not return any valid data. Please check your prompt or try again."
            else:
                if not running:
                    warning = f"Gemini could not generate the full requested dataset. Generated {count} out of {total} rows. You can still download the partial CSV."
    return jsonify(
        {
            "generated": count,
            "total": total,
            "columns": columns,
            "api_calls": calls,
            "error": error,
            "warning": warning,
            "running": running,
            "stream": stream_data,
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
    app.run(debug=True, port=5001)

