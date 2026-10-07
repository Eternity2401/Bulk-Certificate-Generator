// Client-Side Logic for Bulk Certificate Generator
let currentInputMode = 'manual';
let parsedCsvRecipients = [];
let pollingIntervalId = null;

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
        <td><input type="text" class="input-name" placeholder="John Doe" value="${escapeHtml(name)}" required></td>
        <td><input type="email" class="input-email" placeholder="john@example.com" value="${escapeHtml(email)}"></td>
        <td><button type="button" class="btn-icon delete-btn" onclick="removeRecipientRow(this)">✕</button></td>
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
        alert('You must have at least one recipient row.');
    }
}

function updateRecipientCount() {
    const tbody = document.getElementById('recipients-tbody');
    const countSpan = document.getElementById('recipient-count');
    if (countSpan && tbody) {
        countSpan.textContent = tbody.children.length;
    }
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
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border)';
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
        alert('Please upload a valid CSV file.');
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
    };
    reader.readAsText(file);
}

function parseCsv(csvText) {
    const lines = csvText.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    const recipients = [];

    for (let i = 0; i < lines.length; i++) {
        const parts = lines[i].split(',').map(p => p.trim());
        if (parts.length === 0 || !parts[0]) continue;

        // Skip header if present
        if (i === 0 && parts[0].toLowerCase() === 'name') continue;

        const name = parts[0];
        const email = parts.length > 1 ? parts[1] : '';
        if (name) {
            recipients.push({ name, email: email || null });
        }
    }
    return recipients;
}

// Form Submission & API Request
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
            alert('Please add at least one valid recipient.');
            return;
        }

        const payload = {
            course_name: courseName,
            issue_date: issueDate,
            recipients: recipients
        };

        // UI Loading State
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
            startMonitoringJob(data.job_id);

        } catch (err) {
            alert('Error: ' + err.message);
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
        submitText.textContent = 'Scheduling Job...';
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

    // Reset progress
    updateProgressUI({
        status: 'PENDING',
        progress_percentage: 0,
        total: 0,
        completed: 0,
        failed: 0,
        pending: 0,
        items: []
    });

    // Immediate fetch + interval polling every 700ms
    pollJobStatus(jobId);
    pollingIntervalId = setInterval(() => pollJobStatus(jobId), 700);
}

async function pollJobStatus(jobId) {
    try {
        const res = await fetch(`/api/v1/certificates/jobs/${jobId}`);
        if (!res.ok) return;

        const data = await res.json();
        updateProgressUI(data);

        // Stop polling when completed or failed
        if (['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'].includes(data.status)) {
            clearInterval(pollingIntervalId);
            pollingIntervalId = null;
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

    // 5. Itemized Table
    const tbody = document.getElementById('results-tbody');
    tbody.innerHTML = '';

    if (data.items && data.items.length > 0) {
        data.items.forEach(item => {
            const tr = document.createElement('tr');
            
            let actionHtml = '-';
            if (item.status === 'COMPLETED' && item.download_url) {
                actionHtml = `
                    <div style="display: flex; gap: 0.35rem;">
                        <a href="${item.download_url}" class="btn btn-secondary btn-sm" target="_blank">📥 PDF</a>
                        <a href="/api/v1/certificates/verify/${item.certificate_id}" class="btn btn-secondary btn-sm" target="_blank">🔍 Verify</a>
                    </div>
                `;
            } else if (item.status === 'FAILED') {
                actionHtml = `<span class="text-danger" title="${escapeHtml(item.error_message || '')}">Failed ⚠️</span>`;
            }

            tr.innerHTML = `
                <td>
                    <strong>${escapeHtml(item.recipient_name)}</strong>
                    ${item.recipient_email ? `<br><small class="text-muted">${escapeHtml(item.recipient_email)}</small>` : ''}
                </td>
                <td><code class="font-mono">${escapeHtml(item.certificate_id)}</code></td>
                <td><span class="badge ${getBadgeClass(item.status)}">${item.status}</span></td>
                <td>${actionHtml}</td>
            `;
            tbody.appendChild(tr);
        });
    }
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
