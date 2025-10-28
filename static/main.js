const form = document.getElementById("dataset-form");
const progressArea = document.getElementById("progress-area");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const downloadButtons = document.getElementById("download-buttons");
const downloadCsvBtn = document.getElementById("download-csv-btn");
const downloadJsonBtn = document.getElementById("download-json-btn");
const errorMessage = document.getElementById("error-message");
const streamArea = document.getElementById("stream-area");
const streamContent = document.getElementById("stream-content");
const csvPreviewArea = document.getElementById("csv-preview-area");
const csvPreview = document.getElementById("csv-preview");

form.addEventListener("submit", async function (e) {
  e.preventDefault();
  errorMessage.style.display = "none";
  streamArea.style.display = "none";
  streamContent.innerHTML = "";
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
  let lastRowCount = 0;
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
    
    // Show streaming content if available
    if (data.stream && data.stream.length > 0) {
      showStreamContent(data.stream, data.columns);
    }
    
    // Always try to show CSV preview if we have data
    try {
      const previewRows = await getLiveCsvRows();
      if (previewRows.length > 1) { // More than just header
        const newRowCount = previewRows.length - 1; // Exclude header
        const hasNewRows = newRowCount > lastRowCount;
        showPreview(data.columns, previewRows, hasNewRows);
        lastRowCount = newRowCount;
      }
    } catch (e) {
      console.error("Error fetching CSV preview:", e);
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
    
    await new Promise((r) => setTimeout(r, 300));
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

let lastStreamData = [];
let userScrolledStream = false;
let userScrolledCSV = false;

function showStreamContent(streams, columns) {
  streamArea.style.display = "block";
  
  const lastStream = streams[streams.length - 1];
  if (!lastStream || !lastStream.text) {
    streamContent.innerHTML = "<div style='padding: 10px; color: #666;'>⏳ Waiting for data...</div>";
    return;
  }
  
  try {
    // Try to parse the JSON
    const data = JSON.parse(lastStream.text);
    if (!Array.isArray(data) || data.length === 0) {
      streamContent.innerHTML = "<div style='padding: 10px; color: #666;'>⏳ Generating data...</div>";
      return;
    }
    
    // Store for comparison
    const previousCount = lastStreamData.length;
    lastStreamData = data;
    
    // Get columns from first object
    const dataColumns = Object.keys(data[0]);
    
    // Status indicator
    const statusHTML = `<div style="padding: 10px; margin-bottom: 10px; background: ${lastStream.status === 'complete' ? '#e8f5e9' : '#fff3e0'}; border: 1px solid ${lastStream.status === 'complete' ? '#4caf50' : '#ff9800'}; border-radius: 4px; font-weight: bold; color: ${lastStream.status === 'complete' ? '#2e7d32' : '#e65100'};">
      ${lastStream.status === 'complete' ? '✓ Stream Complete' : '⏳ Streaming...'} - ${data.length} rows
    </div>`;
    
    // Create scrollable table container
    let html = statusHTML + '<div id="stream-table-container" style="max-height: 400px; overflow-y: auto; overflow-x: auto; border: 1px solid #d1d5db; border-radius: 4px; background: #fff;">';
    html += '<table id="stream-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">';
    
    // Header
    html += '<thead><tr>';
    dataColumns.forEach(col => {
      html += `<th style="background: #e1e7f7; color: #23408e; padding: 8px; border: 1px solid #d1d5db; position: sticky; top: 0; z-index: 10;">${col}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // Body - add rows with animation for new ones
    data.forEach((row, idx) => {
      const bgColor = idx % 2 === 0 ? '#fff' : '#f1f5fb';
      const isNew = idx >= previousCount;
      const animation = isNew ? 'opacity: 0; animation: fadeIn 0.5s ease forwards;' : '';
      html += `<tr style="background: ${bgColor}; ${animation}">`;
      dataColumns.forEach(col => {
        html += `<td style="padding: 8px; border: 1px solid #d1d5db; word-break: break-word;">${row[col] || ''}</td>`;
      });
      html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    // Add CSS animation
    if (!document.getElementById('stream-animation-style')) {
      const style = document.createElement('style');
      style.id = 'stream-animation-style';
      style.textContent = '@keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }';
      document.head.appendChild(style);
    }
    
    streamContent.innerHTML = html;
    
    // Setup scroll tracking
    const container = document.getElementById('stream-table-container');
    if (container) {
      container.addEventListener('scroll', () => {
        const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 10;
        userScrolledStream = !isAtBottom;
      });
      
      // Auto-scroll to bottom if user hasn't manually scrolled up
      if (!userScrolledStream || lastStream.status === 'complete') {
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 100);
      }
    }
    
  } catch (e) {
    // If JSON is incomplete, show loading
    streamContent.innerHTML = `<div style="padding: 10px; background: #fff3e0; border: 1px solid #ff9800; border-radius: 4px;">
      <div style="font-weight: bold; color: #e65100; margin-bottom: 5px;">⏳ Streaming... (${lastStream.text.length} chars)</div>
      <div style="font-size: 11px; color: #666;">Parsing JSON...</div>
    </div>`;
  }
}

function showPreview(columns, rows, hasNewRows = false) {
  csvPreviewArea.style.display = "block";
  
  if (!rows.length) return;
  
  const headerRow = rows[0];
  const expectedColCount = headerRow.length;
  
  // Update status indicator
  const csvStatus = document.getElementById('csv-status');
  if (csvStatus) {
    const rowCount = rows.length - 1;
    csvStatus.innerHTML = `(${rowCount} rows) ${hasNewRows ? '<span style="color: #ff9800;">⚡ Updating...</span>' : ''}`;
  }
  
  // Check if we need to rebuild the table
  const existingRows = csvPreview.querySelectorAll('tbody tr').length;
  const newRowCount = rows.length - 1; // Exclude header
  
  if (existingRows === 0) {
    // First time - build entire table
    csvPreview.innerHTML = "";
    
    const thead = document.createElement("thead");
    const tr = document.createElement("tr");
    
    headerRow.forEach((col) => {
      const th = document.createElement("th");
      th.innerText = col.replace(/^["']|["']$/g, '');
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    csvPreview.appendChild(thead);
    
    const tbody = document.createElement("tbody");
    tbody.id = "csv-tbody";
    csvPreview.appendChild(tbody);
  }
  
  const tbody = document.getElementById("csv-tbody");
  
  // Add only new rows with animation
  for (let i = existingRows + 1; i < rows.length; i++) {
    if (rows[i].length !== expectedColCount) {
      console.warn(`Skipping row ${i} - has ${rows[i].length} columns, expected ${expectedColCount}`);
      continue;
    }
    
    const tr = document.createElement("tr");
    tr.style.opacity = "0";
    tr.style.transform = "translateY(-10px)";
    tr.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    
    rows[i].forEach((cell) => {
      const td = document.createElement("td");
      td.innerText = cell.replace(/^["']|["']$/g, '');
      tr.appendChild(td);
    });
    
    tbody.appendChild(tr);
    
    // Trigger animation
    setTimeout(() => {
      tr.style.opacity = "1";
      tr.style.transform = "translateY(0)";
    }, 10);
  }
  
  // Setup scroll tracking for CSV preview
  if (!csvPreviewArea.hasScrollListener) {
    csvPreviewArea.addEventListener('scroll', () => {
      const isAtBottom = csvPreviewArea.scrollHeight - csvPreviewArea.scrollTop - csvPreviewArea.clientHeight < 10;
      userScrolledCSV = !isAtBottom;
    });
    csvPreviewArea.hasScrollListener = true;
  }
  
  // Auto-scroll to bottom if user hasn't manually scrolled up
  if (hasNewRows && newRowCount > existingRows) {
    if (!userScrolledCSV) {
      setTimeout(() => {
        csvPreviewArea.scrollTop = csvPreviewArea.scrollHeight;
      }, 100);
    }
  }
}
