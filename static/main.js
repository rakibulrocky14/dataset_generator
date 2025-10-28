const form = document.getElementById("dataset-form");
const progressArea = document.getElementById("progress-area");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const downloadButtons = document.getElementById("download-buttons");
const downloadCsvBtn = document.getElementById("download-csv-btn");
const downloadJsonBtn = document.getElementById("download-json-btn");
const errorMessage = document.getElementById("error-message");
const csvPreviewArea = document.getElementById("csv-preview-area");
const csvPreview = document.getElementById("csv-preview");

form.addEventListener("submit", async function (e) {
  e.preventDefault();
  errorMessage.style.display = "none";
  csvPreviewArea.style.display = "none";
  csvPreview.innerHTML = "";
  progressArea.style.display = "block";
  downloadButtons.style.display = "none";
  setProgressBar(0);
  progressText.innerText = "Starting...";

  const description = document.getElementById("description").value;
  const columns = document
    .getElementById("columns")
    .value.split(",")
    .map((x) => x.trim())
    .filter((x) => x);
  const total_rows = parseInt(document.getElementById("total_rows").value);

  let response;
  try {
    response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description, columns, total_rows }),
    });
  } catch (err) {
    showError("Failed to start generation.");
    return;
  }

  let finished = false;
  let lastRows = [];
  while (!finished) {
    let res, data;
    try {
      res = await fetch("/progress");
      data = await res.json();
    } catch (err) {
      showError("Error fetching progress.");
      break;
    }
    if (data.error) {
      showError(data.error);
      break;
    }
    showWarning(data.warning);
    const percent = data.total
      ? Math.floor((data.generated / data.total) * 100)
      : 0;
    setProgressBar(percent);
    progressText.innerText = `${data.generated} / ${data.total} rows generated`;
    if (data.generated > 0) {
      // Live CSV preview (full)
      try {
        const previewRows = await getLiveCsvRows();
        if (previewRows.length) {
          showPreview(data.columns, previewRows);
        }
      } catch {}
    }
    // Show API call count
    showApiCallCount(data.api_calls);
    
    // Check if generation is complete or stopped
    if (data.generated >= data.total && data.total > 0) {
      finished = true;
      progressText.innerText = `Done! ${data.generated} rows generated.`;
      downloadButtons.style.display = "block";
    } else if (!data.running && data.generated > 0) {
      // Generation stopped but we have some data
      finished = true;
      progressText.innerText = `Generation stopped. ${data.generated} rows available.`;
      downloadButtons.style.display = "block";
    }
    
    await new Promise((r) => setTimeout(r, 1200));
  }
});

downloadCsvBtn.addEventListener("click", function () {
  window.location = "/download";
});

downloadJsonBtn.addEventListener("click", function () {
  window.location = "/download_json";
});

function setProgressBar(percent) {
  progressBar.style.width = percent + "%";
}

function showError(msg) {
  errorMessage.innerText = msg;
  errorMessage.style.display = "block";
}

function showWarning(msg) {
  let el = document.getElementById("warning-message");
  if (!el) {
    el = document.createElement("div");
    el.id = "warning-message";
    el.style.marginTop = "16px";
    el.style.background = "#fffbe6";
    el.style.color = "#b8860b";
    el.style.border = "1px solid #ffe58f";
    el.style.borderRadius = "6px";
    el.style.padding = "10px 14px";
    el.style.fontWeight = "500";
    el.style.display = "none";
    document
      .querySelector(".container")
      .insertBefore(el, document.getElementById("csv-preview-area"));
  }
  if (msg) {
    el.innerText = msg;
    el.style.display = "block";
  } else {
    el.style.display = "none";
  }
}

function parseCSVLine(line) {
  // Proper CSV parser that handles quoted fields with commas
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];
    
    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        // Escaped quote
        current += '"';
        i++;
      } else {
        // Toggle quote state
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      // Field separator
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  
  // Add last field
  result.push(current.trim());
  return result;
}

async function getLiveCsvRows() {
  // Fetch the full CSV (live) from the backend
  try {
    const res = await fetch("/csv_live");
    const text = await res.text();
    const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
    return lines.map((line) => parseCSVLine(line));
  } catch {
    return [];
  }
}

function showApiCallCount(count) {
  let el = document.getElementById("api-call-count");
  if (!el) {
    el = document.createElement("div");
    el.id = "api-call-count";
    el.style.marginTop = "10px";
    el.style.fontWeight = "500";
    el.style.color = "#3c8dbc";
    document.getElementById("progress-area").appendChild(el);
  }
  el.innerText = `LLM API calls: ${count}`;
}

function showPreview(columns, rows) {
  csvPreviewArea.style.display = "block";
  csvPreview.innerHTML = "";
  if (!rows.length) return;
  
  // Use the header row from CSV
  const thead = document.createElement("thead");
  const tr = document.createElement("tr");
  const headerRow = rows[0];
  
  headerRow.forEach((col) => {
    const th = document.createElement("th");
    th.innerText = col.replace(/^["']|["']$/g, '');
    tr.appendChild(th);
  });
  thead.appendChild(tr);
  csvPreview.appendChild(thead);
  
  const tbody = document.createElement("tbody");
  const expectedColCount = headerRow.length;
  
  for (let i = 1; i < rows.length && i <= 10; i++) {
    // Only show rows with correct column count
    if (rows[i].length !== expectedColCount) {
      console.warn(`Skipping row ${i} - has ${rows[i].length} columns, expected ${expectedColCount}`);
      continue;
    }
    
    const tr = document.createElement("tr");
    rows[i].forEach((cell) => {
      const td = document.createElement("td");
      td.innerText = cell.replace(/^["']|["']$/g, '');
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  csvPreview.appendChild(tbody);
}
