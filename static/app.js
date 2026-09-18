/**
 * Smart Expense Receipt Parser Agent — Client Application Logic
 */

let selectedSingleFile = null;
let selectedBulkFiles = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  setupDragAndDrop();
  fetchDashboardData();
});

// Tab Switching
function switchTab(tabId) {
  const tabs = ['single', 'bulk', 'analytics', 'history'];
  tabs.forEach(t => {
    const pane = document.getElementById(`pane-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (t === tabId) {
      pane.classList.add('active');
      btn.classList.add('active');
    } else {
      pane.classList.remove('active');
      btn.classList.remove('active');
    }
  });

  if (tabId === 'analytics') {
    fetchDashboardData();
  } else if (tabId === 'history') {
    loadAllRecentReceipts();
  }
}

// Drag & Drop Setup
function setupDragAndDrop() {
  const singleDz = document.getElementById('single-dropzone');
  const bulkDz = document.getElementById('bulk-dropzone');

  ['dragenter', 'dragover'].forEach(name => {
    singleDz.addEventListener(name, (e) => { e.preventDefault(); singleDz.classList.add('dragover'); });
    bulkDz.addEventListener(name, (e) => { e.preventDefault(); bulkDz.classList.add('dragover'); });
  });

  ['dragleave', 'drop'].forEach(name => {
    singleDz.addEventListener(name, (e) => { e.preventDefault(); singleDz.classList.remove('dragover'); });
    bulkDz.addEventListener(name, (e) => { e.preventDefault(); bulkDz.classList.remove('dragover'); });
  });

  singleDz.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSingleFile(e.dataTransfer.files[0]);
    }
  });

  bulkDz.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setBulkFiles(Array.from(e.dataTransfer.files));
    }
  });
}

function handleFileSelected(event) {
  if (event.target.files && event.target.files[0]) {
    setSingleFile(event.target.files[0]);
  }
}

function setSingleFile(file) {
  selectedSingleFile = file;
  const badge = document.getElementById('file-preview-badge');
  badge.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  badge.style.display = 'inline-block';
  document.getElementById('btn-submit-single').disabled = false;
}

function handleBulkFilesSelected(event) {
  if (event.target.files && event.target.files.length > 0) {
    setBulkFiles(Array.from(event.target.files));
  }
}

function setBulkFiles(files) {
  selectedBulkFiles = files;
  const badge = document.getElementById('bulk-file-preview');
  badge.textContent = `${files.length} receipt files ready for batch upload`;
  badge.style.display = 'inline-block';
  document.getElementById('btn-submit-bulk').disabled = false;
}

// Single Upload Submission
async function handleSingleUpload(event) {
  event.preventDefault();
  if (!selectedSingleFile) return;

  const btn = document.getElementById('btn-submit-single');
  const spinner = document.getElementById('single-spinner');
  btn.disabled = true;
  spinner.style.display = 'inline-block';

  const formData = new FormData();
  formData.append('employeeId', document.getElementById('employee-id').value);
  formData.append('departmentId', document.getElementById('department-id').value);
  formData.append('image', selectedSingleFile);

  const startTime = performance.now();

  try {
    const res = await fetch('/api/parse-receipt', {
      method: 'POST',
      body: formData
    });

    const elapsedSec = ((performance.now() - startTime) / 1000).toFixed(3);

    if (!res.ok) {
      const err = await res.json();
      alert(`Parsing failed: ${err.detail || 'Server error'}`);
      return;
    }

    const data = await res.json();
    renderSingleReceiptResult(data, elapsedSec);
  } catch (error) {
    alert(`Upload error: ${error.message}`);
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

function renderSingleReceiptResult(data, elapsedSec) {
  document.getElementById('result-empty-state').style.display = 'none';
  const resultContent = document.getElementById('result-content');
  resultContent.style.display = 'block';

  const ext = data.extraction || {};
  const cat = data.categorization || {};
  const comp = data.compliance || {};
  const app = data.approval || {};

  // Status Badge
  const statusBadge = document.getElementById('result-status-badge');
  const hero = document.getElementById('decision-hero');
  const heroLabel = document.getElementById('decision-label');
  const heroReason = document.getElementById('decision-reason');
  const heroIcon = document.getElementById('decision-icon');
  const timeChip = document.getElementById('processing-time-chip');

  timeChip.textContent = `${elapsedSec}s (SLA <2.0s)`;

  hero.className = 'decision-hero';
  if (app.recommendation === 'AUTO_APPROVE') {
    hero.classList.add('approved');
    statusBadge.className = 'badge badge-emerald';
    statusBadge.textContent = 'Auto-Approved';
    heroLabel.textContent = 'AUTO-APPROVED FOR REIMBURSEMENT';
    heroIcon.innerHTML = '&#10004;';
  } else if (app.recommendation === 'NEEDS_REVIEW') {
    hero.classList.add('needs-review');
    statusBadge.className = 'badge badge-amber';
    statusBadge.textContent = 'Needs Review';
    heroLabel.textContent = `REQUIRES ${app.requiredApproval ? app.requiredApproval.toUpperCase() : 'MANAGER'} REVIEW`;
    heroIcon.innerHTML = '&#9888;';
  } else {
    hero.classList.add('rejected');
    statusBadge.className = 'badge badge-crimson';
    statusBadge.textContent = 'Rejected';
    heroLabel.textContent = 'POLICY VIOLATION — REJECTED';
    heroIcon.innerHTML = '&#10008;';
  }

  heroReason.textContent = app.reason || 'Audited against enterprise policies.';

  // Metrics
  document.getElementById('res-vendor').textContent = ext.vendor || 'Unknown';
  document.getElementById('res-amount').textContent = `$${(ext.amount || 0).toFixed(2)}`;
  document.getElementById('res-category').textContent = cat.category || 'Other';
  document.getElementById('res-confidence').textContent = `Confidence: ${((cat.confidence || ext.confidence || 0) * 100).toFixed(0)}%`;
  document.getElementById('res-date').textContent = `${ext.date || 'Today'} ${ext.time || ''}`;

  // Policy Checks List
  const checksContainer = document.getElementById('policy-checks-list');
  checksContainer.innerHTML = '';
  const checks = comp.policyChecks || [];

  if (checks.length === 0) {
    checksContainer.innerHTML = '<p class="text-muted">No policy checks recorded.</p>';
  } else {
    checks.forEach(chk => {
      const isPass = chk.status === 'pass';
      const div = document.createElement('div');
      div.className = `check-item ${isPass ? 'pass' : 'fail'}`;
      div.innerHTML = `
        <span class="check-icon">${isPass ? '&#10004;' : '&#10008;'}</span>
        <div>
          <strong>${chk.rule.replace(/_/g, ' ').toUpperCase()}:</strong> 
          ${chk.message || (isPass ? 'Passed rule criteria' : 'Rule violation detected')}
        </div>
      `;
      checksContainer.appendChild(div);
    });
  }

  // Line items
  const tbody = document.getElementById('res-items-tbody');
  tbody.innerHTML = '';
  const items = ext.items || [];
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="text-muted">No itemized line items found</td></tr>';
  } else {
    items.forEach(itm => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(itm.name || itm.description || 'Item')}</td>
        <td>${itm.quantity || 1}</td>
        <td>$${(itm.price || 0).toFixed(2)}</td>
      `;
      tbody.appendChild(tr);
    });
  }
}

// Sample Receipt Generator for instant demo testing
function loadSampleReceipt() {
  const dummyContent = "SAMPLE_RECEIPT_CHIPOTLE_BURRITO_BOWL_$12.99";
  const blob = new Blob([dummyContent], { type: 'image/jpeg' });
  const file = new File([blob], "sample_receipt_chipotle.jpg", { type: 'image/jpeg' });
  setSingleFile(file);
  document.getElementById('single-upload-form').dispatchEvent(new Event('submit', { cancelable: true }));
}

// Bulk Upload Submission
async function handleBulkUpload(event) {
  event.preventDefault();
  if (!selectedBulkFiles || selectedBulkFiles.length === 0) return;

  const btn = document.getElementById('btn-submit-bulk');
  const spinner = document.getElementById('bulk-spinner');
  btn.disabled = true;
  spinner.style.display = 'inline-block';

  const formData = new FormData();
  formData.append('employeeId', document.getElementById('bulk-employee-id').value);
  formData.append('departmentId', document.getElementById('bulk-department-id').value);
  selectedBulkFiles.forEach(f => formData.append('receipts', f));

  try {
    const res = await fetch('/api/receipts/bulk', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      alert('Batch upload processing failed.');
      return;
    }

    const data = await res.json();
    renderBulkResults(data);
  } catch (error) {
    alert(`Bulk upload error: ${error.message}`);
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}

function renderBulkResults(data) {
  document.getElementById('bulk-results-section').style.display = 'block';
  document.getElementById('batch-id-val').textContent = data.batchId;
  document.getElementById('batch-processed-val').textContent = data.processed;
  document.getElementById('batch-approved-val').textContent = data.approved;
  document.getElementById('batch-flagged-val').textContent = data.flagged;
  document.getElementById('batch-amount-val').textContent = `$${(data.totalAmount || 0).toFixed(2)}`;

  const tbody = document.getElementById('bulk-results-tbody');
  tbody.innerHTML = '';

  (data.results || []).forEach(r => {
    const tr = document.createElement('tr');
    const isApp = r.approval.recommendation === 'AUTO_APPROVE';
    tr.innerHTML = `
      <td><code>${r.receiptId}</code></td>
      <td>${escapeHtml(r.extraction.vendor)}</td>
      <td>$${(r.extraction.amount || 0).toFixed(2)}</td>
      <td>${r.categorization.category}</td>
      <td><span class="badge ${isApp ? 'badge-emerald' : 'badge-amber'}">${r.compliance.status}</span></td>
      <td>${escapeHtml(r.approval.recommendation)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function loadMockBatch() {
  const files = [
    new File([new Blob(["receipt1"])], "lunch_01.jpg", { type: "image/jpeg" }),
    new File([new Blob(["receipt2"])], "flight_02.jpg", { type: "image/jpeg" }),
    new File([new Blob(["receipt3"])], "supplies_03.jpg", { type: "image/jpeg" })
  ];
  setBulkFiles(files);
  document.getElementById('bulk-upload-form').dispatchEvent(new Event('submit', { cancelable: true }));
}

// Analytics Dashboard Fetch & Render
async function fetchDashboardData() {
  try {
    const res = await fetch('/api/analytics/dashboard');
    if (!res.ok) return;
    const data = await res.json();

    // Summary KPIs
    const s = data.summary || {};
    document.getElementById('kpi-today-expenses').textContent = `$${(s.todayExpenses || 0).toFixed(2)}`;
    document.getElementById('kpi-month-expenses').textContent = `$${(s.thisMonthExpenses || 0).toFixed(2)}`;
    document.getElementById('kpi-approval-rate').textContent = s.approvalRate || '100.0%';
    document.getElementById('kpi-anomaly-rate').textContent = s.anomalyRate || '0.0%';

    // Category breakdown
    const catContainer = document.getElementById('category-bars-container');
    catContainer.innerHTML = '';
    const catTrends = data.trends?.byCategory || [];
    if (catTrends.length === 0) {
      catContainer.innerHTML = '<p class="text-muted" style="padding:1rem;">No expense categories recorded yet.</p>';
    } else {
      const maxTotal = Math.max(...catTrends.map(c => c.total), 1);
      catTrends.forEach(c => {
        const pct = Math.min((c.total / maxTotal) * 100, 100).toFixed(1);
        const div = document.createElement('div');
        div.className = 'bar-item';
        div.innerHTML = `
          <div class="bar-header">
            <span class="bar-name">${escapeHtml(c.category)} (${c.count})</span>
            <span class="bar-val">$${c.total.toFixed(2)}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${pct}%;"></div>
          </div>
        `;
        catContainer.appendChild(div);
      });
    }

    // Department breakdown
    const deptContainer = document.getElementById('department-bars-container');
    deptContainer.innerHTML = '';
    const deptTrends = data.trends?.byDepartment || [];
    if (deptTrends.length === 0) {
      deptContainer.innerHTML = '<p class="text-muted" style="padding:1rem;">No department expenses recorded yet.</p>';
    } else {
      const maxTotalDept = Math.max(...deptTrends.map(d => d.total), 1);
      deptTrends.forEach(d => {
        const pct = Math.min((d.total / maxTotalDept) * 100, 100).toFixed(1);
        const div = document.createElement('div');
        div.className = 'bar-item';
        div.innerHTML = `
          <div class="bar-header">
            <span class="bar-name">${escapeHtml(d.department.replace('dept_', '').toUpperCase())} (${d.count})</span>
            <span class="bar-val">$${d.total.toFixed(2)}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${pct}%; background: linear-gradient(135deg, #06b6d4, #3b82f6);"></div>
          </div>
        `;
        deptContainer.appendChild(div);
      });
    }

    // Flagged queue
    const flaggedBadge = document.getElementById('flagged-count-badge');
    const flaggedTbody = document.getElementById('flagged-table-tbody');
    const flagged = data.flagged || [];
    flaggedBadge.textContent = `${flagged.length} Pending`;

    if (flagged.length === 0) {
      flaggedTbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding:1.5rem;">No flagged receipts currently require review. All expenses are clean!</td></tr>';
    } else {
      flaggedTbody.innerHTML = '';
      flagged.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code>${f.receiptId}</code></td>
          <td>${escapeHtml(f.employeeId)}</td>
          <td>${escapeHtml(f.vendor)}</td>
          <td>$${f.amount.toFixed(2)}</td>
          <td><span class="badge badge-amber">${f.status}</span></td>
          <td style="max-width:280px; font-size:0.8rem;">${escapeHtml(f.reason || 'Compliance flag')}</td>
          <td>
            <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="inspectReceipt('${f.receiptId}')">
              Inspect
            </button>
          </td>
        `;
        flaggedTbody.appendChild(tr);
      });
    }
  } catch (error) {
    console.error('Error fetching dashboard:', error);
  }
}

// History Search & Lookup
async function handleHistorySearch() {
  const query = document.getElementById('history-search-input').value.trim();
  if (!query) {
    loadAllRecentReceipts();
    return;
  }

  // Check if search query starts with 'emp_'
  if (query.startsWith('emp_')) {
    try {
      const res = await fetch(`/api/receipts/employee/${encodeURIComponent(query)}`);
      const list = await res.json();
      renderHistoryTable(list);
    } catch (e) {
      alert('Error querying employee receipts.');
    }
  } else {
    // Treat as receipt ID
    try {
      const res = await fetch(`/api/receipts/${encodeURIComponent(query)}`);
      if (res.status === 404) {
        alert(`No receipt found with ID "${query}".`);
        return;
      }
      const rcpt = await res.json();
      renderHistoryTable([rcpt]);
    } catch (e) {
      alert('Error fetching receipt.');
    }
  }
}

async function loadAllRecentReceipts() {
  try {
    const res = await fetch('/api/receipts?limit=50');
    if (!res.ok) return;
    const list = await res.json();
    renderHistoryTable(list);
  } catch (e) {
    console.error(e);
  }
}

function renderHistoryTable(items) {
  const tbody = document.getElementById('history-table-tbody');
  tbody.innerHTML = '';

  if (!items || items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding:1.5rem;">No matching receipts found.</td></tr>';
    return;
  }

  items.forEach(r => {
    const tr = document.createElement('tr');
    const isApp = r.recommendation === 'AUTO_APPROVE';
    const badgeClass = isApp ? 'badge-emerald' : (r.recommendation === 'REJECT' ? 'badge-crimson' : 'badge-amber');
    tr.innerHTML = `
      <td><code>${r.receipt_id}</code></td>
      <td>${escapeHtml(r.employee_id)}</td>
      <td>${escapeHtml(r.vendor)}</td>
      <td>$${(r.amount || 0).toFixed(2)}</td>
      <td>${escapeHtml(r.category || 'Other')}</td>
      <td><span class="badge ${badgeClass}">${escapeHtml(r.recommendation || 'UNKNOWN')}</span></td>
      <td>${r.date || r.created_at || '—'}</td>
      <td>
        <button class="btn btn-secondary" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="inspectReceipt('${r.receipt_id}')">
          View
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Receipt Modal Inspector
async function inspectReceipt(receiptId) {
  try {
    const res = await fetch(`/api/receipts/${encodeURIComponent(receiptId)}`);
    if (!res.ok) {
      alert('Could not load receipt details.');
      return;
    }
    const data = await res.json();
    const body = document.getElementById('modal-body-content');
    document.getElementById('modal-title').textContent = `Receipt Details: ${data.receipt_id}`;

    const parsed = data.parsed_response || {};
    const ext = parsed.extraction || {};
    const app = parsed.approval || {};
    const comp = parsed.compliance || {};

    body.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.08);">
        <div>
          <h4 style="font-size:1.1rem; color:#fff;">${escapeHtml(data.vendor)}</h4>
          <span style="font-size:0.8rem; color:#94a3b8;">Employee: ${escapeHtml(data.employee_id)} &bull; Dept: ${escapeHtml(data.department_id)}</span>
        </div>
        <div style="text-align:right;">
          <span style="font-size:1.3rem; font-weight:700; color:#10b981;">$${data.amount.toFixed(2)} ${data.currency}</span>
          <div style="margin-top:0.2rem;"><span class="badge ${data.recommendation === 'AUTO_APPROVE' ? 'badge-emerald' : 'badge-amber'}">${data.recommendation}</span></div>
        </div>
      </div>

      <div style="margin-bottom:1rem;">
        <p style="font-size:0.85rem; color:#cbd5e1;"><strong>Audit Decision:</strong> ${escapeHtml(app.reason || 'Passed policy audit')}</p>
        ${app.alternativeAction ? `<p style="font-size:0.8rem; color:#f59e0b; margin-top:0.3rem;"><strong>Recommended Action:</strong> ${escapeHtml(app.alternativeAction)}</p>` : ''}
      </div>

      <h5 style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase; margin-bottom:0.5rem;">Raw Extracted Payload</h5>
      <pre style="background:rgba(0,0,0,0.4); padding:0.85rem; border-radius:8px; font-size:0.75rem; color:#a7f3d0; overflow-x:auto; max-height:220px;">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>
    `;

    document.getElementById('receipt-modal').style.display = 'flex';
  } catch (e) {
    alert('Error inspecting receipt.');
  }
}

function closeModal(event) {
  if (event.target.id === 'receipt-modal') {
    closeModalDirect();
  }
}

function closeModalDirect() {
  document.getElementById('receipt-modal').style.display = 'none';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
