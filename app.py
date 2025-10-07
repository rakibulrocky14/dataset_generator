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


def generate_with_llm(prompt, columns, batch_size):
    # Calls LLM API (OpenAI-compatible) to generate CSV rows
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that generates CSV data. Output only valid CSV format with no additional explanation.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    # Parse CSV rows from response
    csv_text = response.choices[0].message.content.strip()
    rows = []
    for line in csv_text.splitlines():
        if not line.strip():
            continue
        # skip header if present
        if any(col.lower() in line.lower() for col in columns):
            continue
        parts = [x.strip(' "') for x in line.split(",")]
        if len(parts) == len(columns):
            rows.append(parts)
    return rows


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
            prompt = (
                f"{description}. Generate {curr_batch} unique rows as CSV with columns: {', '.join(columns)}. "
                f"Output ONLY valid CSV with a header row and no explanation. Do not repeat any row or the header row. "
                f"Example:\n{', '.join(columns)}\nvalue1,value2\nvalue3,value4"
            )
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
                # Deduplicate rows
                new_rows = []
                with lock:
                    for row in rows:
                        trow = tuple(row)
                        if trow not in seen:
                            seen.add(trow)
                            new_rows.append(row)
                    needed = total_rows - len(generated_data)
                    to_add = new_rows[:needed]
                    generated_data.extend(to_add)
                    generated = len(generated_data)
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
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        json_data.append(row_dict)

    import json
    json_string = json.dumps(json_data, indent=2)

    return send_file(
        io.BytesIO(json_string.encode()),
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
