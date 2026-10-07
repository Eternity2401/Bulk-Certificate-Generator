// ==============================================================================
// CertiFlow — Client-Side Application Logic
// Handles form submission, CSV parsing, polling, presets, and UI interactions.
// ==============================================================================

let currentInputMode = 'manual';
let parsedCsvRecipients = [];
let pollingIntervalId = null;
let currentJobItems = [];

document.addEventListener('DOMContentLoaded', () => {
    setupCsvDropZone();
    setupFormSubmit();
    updateRecipientCount();
});

// Mode Switching (Manual Entry vs CSV)
function switchInputMode(mode) {
    currentInputMode = mode;
    const manualSec = document.getElementById('manual-recipients-section');
    const csvSec = document.getElementById('csv-upload-section');
    const tabManual = document.getElementById('tab-manual');
    const tabCsv = document.getElementById('tab-csv');

    if (mode === 'manual') {
        manualSec.classList.remove('hidden');
        csvSec.classList.add('hidden');
        tabManual.classList.add('active');
        tabCsv.classList.remove('active');
    } else {
        manualSec.classList.add('hidden');
        csvSec.classList.remove('hidden');
        tabManual.classList.remove('active');
        tabCsv.classList.add('active');
    }
}

// Manual Recipient Rows
function addRecipientRow(name = '', email = '') {
    const tbody = document.getElementById('recipients-tbody');
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" class="input-name" placeholder="Full Name" value="${escapeHtml(name)}" required></td>
        <td><input type="email" class="input-email" placeholder="email@example.com" value="${escapeHtml(email)}"></td>
        <td><button type="button" class="btn-icon delete-btn" onclick="removeRecipientRow(this)" title="Remove">✕</button></td>
    `;
    tbody.appendChild(tr);
    updateRecipientCount();
}

function removeRecipientRow(btn) {
    const tbody = document.getElementById('recipients-tbody');
    if (tbody.children.length > 1) {
        btn.closest('tr').remove();
        updateRecipientCount();
    } else {
        showToast('At least one recipient row is required.', 'warning');
    }
}

function updateRecipientCount() {
    const tbody = document.getElementById('recipients-tbody');
    const countSpan = document.getElementById('recipient-count');
    if (countSpan && tbody) {
        countSpan.textContent = tbody.children.length;
    }
}

// Quick Presets
function loadSampleDemoRecipients() {
    const tbody = document.getElementById('recipients-tbody');
    tbody.innerHTML = '';
    const samples = [
        { name: 'Alice Johnson', email: 'alice.johnson@example.com' },
        { name: 'Bob Smith', email: 'bob.smith@example.com' },
        { name: 'Charlie Brown', email: 'charlie.brown@example.com' }
    ];
    samples.forEach(s => addRecipientRow(s.name, s.email));
    showToast('Loaded 3 demo participants.');
}

function loadFaultTestRecipients() {
    const tbody = document.getElementById('recipients-tbody');
    tbody.innerHTML = '';
    const samples = [
        { name: 'Sarah Connor', email: 'sarah@example.com' },
        { name: 'John Connor', email: 'john@example.com' },
        { name: 'Kyle Reese', email: 'kyle@example.com' }
    ];
    samples.forEach(s => addRecipientRow(s.name, s.email));
    showToast('Loaded mixed test batch.');
}

function clearAllRecipients() {
    const tbody = document.getElementById('recipients-tbody');
    tbody.innerHTML = '';
    addRecipientRow('', '');
    showToast('Roster cleared.');
}

// Download Sample CSV directly from browser
function downloadSampleCsvTemplate() {
    const csvContent = 'name,email\nAlice Johnson,alice@example.com\nBob Smith,bob@example.com\nCharlie Brown,charlie@example.com\n';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'sample_recipients.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Sample CSV template downloaded!');
}

// CSV Drag & Drop and File Parsing
function setupCsvDropZone() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('csv-file-input');

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
        dropZone.style.background = 'var(--primary-soft)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border-subtle)';
        dropZone.style.background = '#fafafa';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border-subtle)';
        dropZone.style.background = '#fafafa';
        if (e.dataTransfer.files.length > 0) {
            handleCsvFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleCsvFile(fileInput.files[0]);
        }
    });
}

function handleCsvFile(file) {
    if (!file.name.endsWith('.csv')) {
        showToast('Please upload a valid .csv file', 'warning');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result;
        parsedCsvRecipients = parseCsv(text);

        const previewBox = document.getElementById('csv-preview-info');
        const filenameSpan = document.getElementById('csv-filename');
        const countBadge = document.getElementById('csv-rows-count');

        filenameSpan.textContent = file.name;
        countBadge.textContent = `${parsedCsvRecipients.length} recipients parsed`;
        previewBox.classList.remove('hidden');
        showToast(`Parsed ${parsedCsvRecipients.length} recipients from CSV!`);
    };
    reader.readAsText(file);
}

function parseCsv(csvText) {
    const lines = csvText.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    const recipients = [];

    for (let i = 0; i < lines.length; i++) {
        const parts = lines[i].split(',').map(p => p.trim());
        if (parts.length === 0 || !parts[0]) continue;

        // Skip header row if present
        if (i === 0 && parts[0].toLowerCase() === 'name') continue;

        const name = parts[0];
        const email = parts.length > 1 ? parts[1] : '';
        if (name) {
            recipients.push({ name, email: email || null });
        }
    }
    return recipients;
}

// Form Submission & API Call
function setupFormSubmit() {
    const form = document.getElementById('certificate-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const courseName = document.getElementById('course_name').value.trim();
        const issueDate = document.getElementById('issue_date').value.trim();

        let recipients = [];
        if (currentInputMode === 'manual') {
            const rows = document.querySelectorAll('#recipients-tbody tr');
            rows.forEach(r => {
                const nameInput = r.querySelector('.input-name');
                const emailInput = r.querySelector('.input-email');
                const name = nameInput ? nameInput.value.trim() : '';
                const email = emailInput ? emailInput.value.trim() : '';
                if (name) {
                    recipients.push({ name, email: email || null });
                }
            });
        } else {
            recipients = parsedCsvRecipients;
        }

        if (recipients.length === 0) {
            showToast('Please add at least one recipient.', 'warning');
            return;
        }

        const payload = {
            course_name: courseName,
            issue_date: issueDate,
            recipients: recipients
        };

        setSubmitting(true);

        try {
            const response = await fetch('/api/v1/certificates/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail ? JSON.stringify(errData.detail) : 'Failed to submit job.');
            }

            const data = await response.json();
            showToast('Generation job scheduled!');
            startMonitoringJob(data.job_id);

        } catch (err) {
            showToast('Error: ' + err.message, 'danger');
        } finally {
            setSubmitting(false);
        }
    });
}

function setSubmitting(isSubmitting) {
    const submitBtn = document.getElementById('submit-btn');
    const submitText = document.getElementById('submit-text');
    const spinner = document.getElementById('submit-spinner');

    if (isSubmitting) {
        submitBtn.disabled = true;
        submitText.textContent = 'Enqueuing Batch...';
        spinner.classList.remove('hidden');
    } else {
        submitBtn.disabled = false;
        submitText.textContent = '🚀 Generate Bulk Certificates';
        spinner.classList.add('hidden');
    }
}

// Monitoring & Polling
function startMonitoringJob(jobId) {
    if (pollingIntervalId) clearInterval(pollingIntervalId);

    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('job-details-container').classList.remove('hidden');
    document.getElementById('job-id-display').textContent = jobId;

    updateProgressUI({
        status: 'PENDING',
        progress_percentage: 0,
        total: 0,
        completed: 0,
        failed: 0,
        pending: 0,
        items: []
    });

    pollJobStatus(jobId);
    pollingIntervalId = setInterval(() => pollJobStatus(jobId), 700);
}

async function pollJobStatus(jobId) {
    try {
        const res = await fetch(`/api/v1/certificates/jobs/${jobId}`);
        if (!res.ok) return;

        const data = await res.json();
        currentJobItems = data.items || [];
        updateProgressUI(data);

        // Stop polling when batch is finalized
        if (['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes(data.status)) {
            clearInterval(pollingIntervalId);
            pollingIntervalId = null;
            if (data.status === 'COMPLETED') {
                showToast('All certificates generated successfully! 🎉', 'success');
            } else if (data.status === 'COMPLETED_WITH_ERRORS') {
                showToast('Batch completed with some item errors.', 'warning');
            }
        }
    } catch (e) {
        console.error('Polling error:', e);
    }
}

function updateProgressUI(data) {
    // 1. Status Badge
    const badge = document.getElementById('job-status-badge');
    badge.textContent = data.status;
    badge.className = 'badge ' + getBadgeClass(data.status);

    // 2. Progress Bar
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const processedText = document.getElementById('processed-count-text');

    const progress = data.progress_percentage || 0;
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `Progress: ${progress}%`;
    processedText.textContent = `${(data.completed || 0) + (data.failed || 0)} / ${data.total || 0}`;

    // 3. Stats Numbers
    document.getElementById('stat-total').textContent = data.total || 0;
    document.getElementById('stat-completed').textContent = data.completed || 0;
    document.getElementById('stat-failed').textContent = data.failed || 0;
    document.getElementById('stat-pending').textContent = data.pending || 0;

    // 4. Batch ZIP Download button
    const zipBtn = document.getElementById('download-zip-btn');
    if (data.download_all_url && data.completed > 0) {
        zipBtn.href = data.download_all_url;
        zipBtn.classList.remove('disabled');
    } else {
        zipBtn.href = '#';
        zipBtn.classList.add('disabled');
    }

    // 5. Render Items Table
    renderItemsTable(currentJobItems);
}

function renderItemsTable(items) {
    const tbody = document.getElementById('results-tbody');
    const filterTerm = (document.getElementById('results-filter-input')?.value || '').toLowerCase().trim();
    tbody.innerHTML = '';

    if (!items || items.length === 0) return;

    const filtered = items.filter(item => {
        if (!filterTerm) return true;
        return (item.recipient_name || '').toLowerCase().includes(filterTerm) ||
               (item.certificate_id || '').toLowerCase().includes(filterTerm);
    });

    filtered.forEach(item => {
        const tr = document.createElement('tr');

        let actionHtml = '-';
        if (item.status === 'COMPLETED' && item.download_url) {
            actionHtml = `
                <div style="display: flex; gap: 0.35rem;">
                    <a href="${item.download_url}" class="btn btn-secondary btn-sm" target="_blank" title="Download PDF">📥 PDF</a>
                    <a href="/api/v1/certificates/verify/${item.certificate_id}" class="btn btn-secondary btn-sm" target="_blank" title="Verify Online">🔍 Verify</a>
                </div>
            `;
        } else if (item.status === 'FAILED') {
            actionHtml = `<span class="badge badge-failed" title="${escapeHtml(item.error_message || '')}">Failed ⚠️</span>`;
        } else {
            actionHtml = `<span class="badge badge-processing">Processing...</span>`;
        }

        tr.innerHTML = `
            <td>
                <strong>${escapeHtml(item.recipient_name)}</strong>
                ${item.recipient_email ? `<br><small style="color: var(--text-muted);">${escapeHtml(item.recipient_email)}</small>` : ''}
            </td>
            <td><code class="font-mono" onclick="copyText('${escapeHtml(item.certificate_id)}')" style="cursor: pointer;" title="Click to copy">${escapeHtml(item.certificate_id)}</code></td>
            <td><span class="badge ${getBadgeClass(item.status)}">${item.status}</span></td>
            <td>${actionHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterResultsTable() {
    renderItemsTable(currentJobItems);
}

function copyJobId() {
    const jobId = document.getElementById('job-id-display').textContent;
    if (jobId && jobId !== '--') {
        copyText(jobId);
    }
}

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied: ${text}`);
    }).catch(() => {
        showToast('Failed to copy', 'warning');
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;

    if (type === 'success') toast.style.borderLeft = '3px solid var(--success)';
    else if (type === 'warning') toast.style.borderLeft = '3px solid var(--warning)';
    else if (type === 'danger') toast.style.borderLeft = '3px solid var(--danger)';
    else toast.style.borderLeft = '3px solid var(--primary)';

    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 250);
    }, 2800);
}

function getBadgeClass(status) {
    switch (status) {
        case 'COMPLETED': return 'badge-success';
        case 'PROCESSING': return 'badge-processing';
        case 'PENDING': return 'badge-pending';
        case 'COMPLETED_WITH_ERRORS': return 'badge-pending';
        case 'FAILED': return 'badge-failed';
        default: return 'badge-info';
    }
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
