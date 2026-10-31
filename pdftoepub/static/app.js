// Application State
let activeTab = 'upload';
let selectedFile = null;
let selectedWorkspaceFile = null;
let activeJobId = null;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initDropzone();
    loadSystemStatus();
    loadWorkspacePdfs();
});

// Load System Hardware Status
async function loadSystemStatus() {
    try {
        const res = await fetch('/api/system-status');
        const data = await res.json();
        
        // Tesseract Badge
        const tessBadge = document.getElementById('tess-badge');
        const tessLabel = document.getElementById('tess-label');
        if (data.tesseract_available) {
            tessLabel.textContent = 'Tesseract 5 (LSTM Hazır)';
        } else {
            tessBadge.style.opacity = '0.5';
            tessLabel.textContent = 'Tesseract Yok (EasyOCR Aktif)';
        }

        // GPU Badge
        const gpuLabel = document.getElementById('gpu-label');
        if (data.cuda_available) {
            gpuLabel.textContent = `${data.device_name} (CUDA Aktif)`;
        } else {
            const gpuBadge = document.getElementById('gpu-badge');
            gpuBadge.className = 'badge';
            gpuBadge.style.color = '#9ca3af';
            gpuLabel.textContent = 'CPU Modu';
        }
    } catch (e) {
        console.error('System status error:', e);
    }
}

// Load Existing PDFs from Workspace
async function loadWorkspacePdfs() {
    try {
        const res = await fetch('/api/workspace-pdfs');
        const data = await res.json();
        
        const listEl = document.getElementById('workspace-list');
        const countEl = document.getElementById('workspace-count');
        
        countEl.textContent = data.pdfs.length;

        if (data.pdfs.length === 0) {
            listEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem 0;">Klasörde PDF bulunamadı.</div>';
            return;
        }

        listEl.innerHTML = '';
        data.pdfs.forEach((pdf, idx) => {
            const item = document.createElement('div');
            item.className = 'book-item';
            item.innerHTML = `
                <div class="book-item-info">
                    <div class="book-item-title">${escapeHtml(pdf.name)}</div>
                    <div class="book-item-size">${pdf.size_mb} MB</div>
                </div>
                <div class="book-select-radio">
                    <span style="font-size: 0.8rem; color: var(--primary);">Seç &rarr;</span>
                </div>
            `;
            item.onclick = () => selectWorkspaceBook(pdf.name, item);
            listEl.appendChild(item);
        });
    } catch (e) {
        console.error('Error loading workspace PDFs:', e);
    }
}

function selectWorkspaceBook(filename, element) {
    selectedWorkspaceFile = filename;
    document.querySelectorAll('.book-item').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    
    // Auto-fill title if empty
    const titleInput = document.getElementById('book-title');
    if (!titleInput.value) {
        const cleanName = filename.replace(/\.pdf$/i, '');
        titleInput.value = cleanName;
    }
}

// Tab Switching
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');

    if (tab === 'upload') {
        document.getElementById('tab-upload-btn').classList.add('active');
        document.getElementById('tab-upload').style.display = 'block';
    } else {
        document.getElementById('tab-workspace-btn').classList.add('active');
        document.getElementById('tab-workspace').style.display = 'block';
    }
}

// Drag & Drop Handling
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    dropzone.onclick = (e) => {
        if (!e.target.classList.contains('btn-clear')) {
            fileInput.click();
        }
    };

    fileInput.onchange = (e) => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    };

    dropzone.ondragover = (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    };

    dropzone.ondragleave = () => {
        dropzone.classList.remove('dragover');
    };

    dropzone.ondrop = (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            const f = e.dataTransfer.files[0];
            if (f.name.toLowerCase().endsWith('.pdf')) {
                handleFileSelect(f);
            } else {
                alert('Lütfen yalnızca PDF dosyası seçin.');
            }
        }
    };
}

function handleFileSelect(file) {
    selectedFile = file;
    document.querySelector('.dropzone-content').style.display = 'none';
    const banner = document.getElementById('selected-file-banner');
    banner.style.display = 'flex';
    document.getElementById('selected-file-name').textContent = file.name;
    document.getElementById('selected-file-size').textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;

    const titleInput = document.getElementById('book-title');
    if (!titleInput.value) {
        titleInput.value = file.name.replace(/\.pdf$/i, '');
    }
}

function clearSelectedFile(e) {
    e.stopPropagation();
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('selected-file-banner').style.display = 'none';
    document.querySelector('.dropzone-content').style.display = 'block';
}

function toggleAiOptions() {
    const aiCheck = document.getElementById('ai-repair');
    const container = document.getElementById('ai-model-container');
    if (aiCheck && container) {
        container.style.display = aiCheck.checked ? 'block' : 'none';
    }
}

// Start Conversion Process
async function startConversion() {
    const ocrEngine = document.getElementById('ocr-engine').value;
    const ocrMode = document.getElementById('ocr-mode').value;
    const title = document.getElementById('book-title').value.trim() || null;
    const author = document.getElementById('book-author').value.trim() || null;
    const aiRepair = document.getElementById('ai-repair') ? document.getElementById('ai-repair').checked : false;
    const aiModel = document.getElementById('ai-model') ? document.getElementById('ai-model').value : 'Qwen/Qwen2.5-1.5B-Instruct';

    let response;

    if (activeTab === 'upload') {
        if (!selectedFile) {
            alert('Lütfen dönüştürülecek bir PDF dosyası seçin.');
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('ocr_engine', ocrEngine);
        formData.append('ocr_mode', ocrMode);
        formData.append('ai_repair', aiRepair ? 'true' : 'false');
        formData.append('ai_backend', 'transformers');
        formData.append('ai_model', aiModel);
        if (title) formData.append('title', title);
        if (author) formData.append('author', author);

        showProcessingState();

        response = await fetch('/api/convert-upload', {
            method: 'POST',
            body: formData
        });
    } else {
        if (!selectedWorkspaceFile) {
            alert('Lütfen listeden bir kitap seçin.');
            return;
        }

        showProcessingState();

        response = await fetch('/api/convert-existing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: selectedWorkspaceFile,
                ocr_engine: ocrEngine,
                ocr_mode: ocrMode,
                title: title,
                author: author,
                ai_repair: aiRepair,
                ai_backend: 'transformers',
                ai_model: aiModel
            })
        });
    }

    if (!response.ok) {
        const err = await response.json();
        alert('Dönüştürme başlatılamadı: ' + (err.detail || 'Bilinmeyen hata'));
        resetConverter();
        return;
    }

    const data = await response.json();
    activeJobId = data.job_id;
    startPollingJob(activeJobId);
}

// Polling Job Status
function startPollingJob(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/job-status/${jobId}`);
            if (!res.ok) return;

            const job = await res.json();
            updateProgressUI(job);

            if (job.status === 'completed') {
                clearInterval(pollInterval);
                showCompletedState(job.result);
            } else if (job.status === 'failed') {
                clearInterval(pollInterval);
                alert('Dönüştürme sırasında hata oluştu:\n' + job.message);
                resetConverter();
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 1500);
}

function updateProgressUI(job) {
    const percent = Math.min(Math.round(job.progress * 100), 100);
    document.getElementById('progress-fill').style.width = `${percent}%`;
    document.getElementById('progress-percent').textContent = `${percent}%`;
    document.getElementById('progress-status').textContent = job.message || 'İşleniyor...';

    // Update Steps
    updateStep('step-1', percent >= 15, percent < 20 && percent >= 5);
    updateStep('step-2', percent >= 70, percent < 70 && percent >= 20);
    updateStep('step-3', percent >= 80, percent < 80 && percent >= 70);
    updateStep('step-4', percent >= 100, percent < 100 && percent >= 80);
}

function updateStep(elementId, isDone, isActive) {
    const el = document.getElementById(elementId);
    el.classList.remove('active', 'done');
    if (isDone) {
        el.classList.add('done');
    } else if (isActive) {
        el.classList.add('active');
    }
}

function showProcessingState() {
    document.getElementById('state-idle').style.display = 'none';
    document.getElementById('state-completed').style.display = 'none';
    document.getElementById('state-processing').style.display = 'flex';
    document.getElementById('btn-convert').disabled = true;
    document.getElementById('progress-fill').style.width = '5%';
    document.getElementById('progress-percent').textContent = '5%';
}

function showCompletedState(result) {
    document.getElementById('state-processing').style.display = 'none';
    const comp = document.getElementById('state-completed');
    comp.style.display = 'flex';

    document.getElementById('result-title').textContent = result.title;
    document.getElementById('result-author').textContent = result.author;
    document.getElementById('stat-pages').textContent = result.total_pages;
    document.getElementById('stat-ocr').textContent = result.ocr_pages_count;
    document.getElementById('stat-chapters').textContent = result.chapter_count;

    const aiContainer = document.getElementById('stat-ai-container');
    const aiStat = document.getElementById('stat-ai');
    if (aiContainer && aiStat) {
        if (result.ai_repairs_count !== undefined && result.ai_repairs_count > 0) {
            aiStat.textContent = result.ai_repairs_count;
            aiContainer.style.display = 'flex';
        } else {
            aiContainer.style.display = 'none';
        }
    }

    // EPUB Download
    const epubBtn = document.getElementById('btn-download-epub');
    epubBtn.href = `/api/download/epub/${activeJobId}`;

    // AZW3 Download
    const azwBtn = document.getElementById('btn-download-azw3');
    const noticeEl = document.getElementById('azw3-notice');
    
    if (result.azw3_path) {
        azwBtn.href = `/api/download/azw3/${activeJobId}`;
        azwBtn.classList.remove('disabled');
        noticeEl.style.display = 'none';
    } else {
        azwBtn.href = '#';
        azwBtn.classList.add('disabled');
        noticeEl.style.display = 'block';
        document.getElementById('azw3-notice-text').textContent = result.azw3_message;
    }
}

function resetConverter() {
    if (pollInterval) clearInterval(pollInterval);
    activeJobId = null;
    const aiContainer = document.getElementById('stat-ai-container');
    if (aiContainer) aiContainer.style.display = 'none';
    document.getElementById('state-completed').style.display = 'none';
    document.getElementById('state-processing').style.display = 'none';
    document.getElementById('state-idle').style.display = 'flex';
    document.getElementById('btn-convert').disabled = false;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
