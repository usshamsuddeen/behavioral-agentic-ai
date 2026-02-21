/**
 * Knowledge Base Management JavaScript
 * Behavioral Agentic AI
 *
 * Handles:
 * - Document upload with drag-drop (JWT-authenticated)
 * - Knowledge base search (tenant-scoped)
 * - Document listing and management
 * - AI status checking
 *
 * All API calls use the global `API` object (from api.js)
 * which injects JWT Bearer tokens automatically.
 */

// =========================================================
// Configuration
// =========================================================
const KB_CONFIG = {
    MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
    ALLOWED_EXTENSIONS: ['pdf', 'docx', 'doc', 'txt', 'json', 'csv', 'md']
};

// =========================================================
// State
// =========================================================
let selectedFiles = [];
let isUploading = false;

// =========================================================
// DOM Elements
// =========================================================
const elements = {};

// =========================================================
// Initialization
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    initializeEventListeners();
    checkAIStatus();
    loadStats();
    loadDocuments();
});

function initializeElements() {
    elements.dropZone = document.getElementById('dropZone');
    elements.fileInput = document.getElementById('fileInput');
    elements.uploadBtn = document.getElementById('uploadBtn');
    elements.docType = document.getElementById('docType');
    elements.docCategory = document.getElementById('docCategory');
    elements.uploadProgress = document.getElementById('uploadProgress');
    elements.uploadFileName = document.getElementById('uploadFileName');
    elements.uploadPercent = document.getElementById('uploadPercent');
    elements.uploadProgressBar = document.getElementById('uploadProgressBar');
    elements.searchQuery = document.getElementById('searchQuery');
    elements.searchBtn = document.getElementById('searchBtn');
    elements.searchResults = document.getElementById('searchResults');
    elements.documentsTableBody = document.getElementById('documentsTableBody');
    elements.refreshDocsBtn = document.getElementById('refreshDocsBtn');
    elements.deleteAllBtn = document.getElementById('deleteAllBtn');
    elements.aiStatus = document.getElementById('aiStatus');
    elements.totalDocuments = document.getElementById('totalDocuments');
    elements.totalChunks = document.getElementById('totalChunks');
    elements.totalSize = document.getElementById('totalSize');
    elements.docTypes = document.getElementById('docTypes');
    elements.toastContainer = document.getElementById('toastContainer');
}

function initializeEventListeners() {
    // Drop zone events
    elements.dropZone.addEventListener('click', () => elements.fileInput.click());
    elements.dropZone.addEventListener('dragover', handleDragOver);
    elements.dropZone.addEventListener('dragleave', handleDragLeave);
    elements.dropZone.addEventListener('drop', handleDrop);
    elements.fileInput.addEventListener('change', handleFileSelect);

    // Upload button
    elements.uploadBtn.addEventListener('click', handleUpload);

    // Search
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Document management
    elements.refreshDocsBtn.addEventListener('click', () => {
        loadStats();
        loadDocuments();
    });
    elements.deleteAllBtn.addEventListener('click', handleDeleteAll);
}

// =========================================================
// Drag & Drop Handlers
// =========================================================
function handleDragOver(e) {
    e.preventDefault();
    elements.dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    elements.dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    elements.dropZone.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processFiles(files);
}

function processFiles(files) {
    const validFiles = files.filter(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!KB_CONFIG.ALLOWED_EXTENSIONS.includes(ext)) {
            showToast('error', 'Invalid File Type', `${file.name} is not a supported file type`);
            return false;
        }
        if (file.size > KB_CONFIG.MAX_FILE_SIZE) {
            showToast('error', 'File Too Large', `${file.name} exceeds the 10MB limit`);
            return false;
        }
        return true;
    });

    if (validFiles.length > 0) {
        selectedFiles = validFiles;
        updateDropZoneText();
        elements.uploadBtn.disabled = false;
    }
}

function updateDropZoneText() {
    const text = elements.dropZone.querySelector('.drop-zone-text');
    const subtext = elements.dropZone.querySelector('.drop-zone-subtext');

    if (selectedFiles.length === 1) {
        text.textContent = selectedFiles[0].name;
        subtext.textContent = formatFileSize(selectedFiles[0].size);
    } else if (selectedFiles.length > 1) {
        text.textContent = `${selectedFiles.length} files selected`;
        const totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);
        subtext.textContent = formatFileSize(totalSize);
    }
}

// =========================================================
// Upload Handler — uses API.upload() with JWT auth
// =========================================================
async function handleUpload() {
    if (selectedFiles.length === 0 || isUploading) return;

    isUploading = true;
    elements.uploadBtn.disabled = true;
    elements.uploadProgress.style.display = 'block';

    const docType = elements.docType.value;
    const category = elements.docCategory.value || 'general';

    let successCount = 0;
    let errorCount = 0;

    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const percent = Math.round(((i + 0.5) / selectedFiles.length) * 100);

        elements.uploadFileName.textContent = file.name;
        elements.uploadPercent.textContent = `${percent}%`;
        elements.uploadProgressBar.style.width = `${percent}%`;

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('doc_type', docType);
            formData.append('category', category);

            // Uses API.upload() which includes JWT auth header
            const result = await API.upload('/knowledge/upload', formData);

            if (result.success) {
                successCount++;
            } else {
                errorCount++;
                console.error(`Upload failed for ${file.name}:`, result.error);
            }
        } catch (err) {
            errorCount++;
            console.error(`Upload error for ${file.name}:`, err);
        }
    }

    // Complete
    elements.uploadProgressBar.style.width = '100%';
    elements.uploadPercent.textContent = '100%';

    setTimeout(() => {
        elements.uploadProgress.style.display = 'none';
        elements.uploadProgressBar.style.width = '0%';
        isUploading = false;
        selectedFiles = [];
        elements.fileInput.value = '';
        resetDropZone();

        if (successCount > 0) {
            showToast('success', 'Upload Complete', `${successCount} document(s) uploaded successfully`);
            loadStats();
            loadDocuments();
        }

        if (errorCount > 0) {
            showToast('error', 'Upload Errors', `${errorCount} document(s) failed to upload`);
        }
    }, 500);
}

function resetDropZone() {
    const text = elements.dropZone.querySelector('.drop-zone-text');
    const subtext = elements.dropZone.querySelector('.drop-zone-subtext');
    text.textContent = 'Drag & drop files here';
    subtext.textContent = 'or click to browse';
    elements.uploadBtn.disabled = true;
}

// =========================================================
// Search Handler — uses API.searchKnowledge() with JWT auth
// =========================================================
async function handleSearch() {
    const query = elements.searchQuery.value.trim();
    if (!query) return;

    elements.searchResults.innerHTML = `
        <div class="search-placeholder">
            <div class="spinner"></div>
            <p>Searching knowledge base...</p>
        </div>
    `;

    try {
        const result = await API.searchKnowledge(query, 5);

        if (result.results_count === 0) {
            elements.searchResults.innerHTML = `
                <div class="search-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                        <line x1="12" y1="9" x2="12" y2="13" />
                        <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <p>No matching documents found</p>
                </div>
            `;
            return;
        }

        elements.searchResults.innerHTML = result.results.map(r => `
            <div class="search-result-item">
                <div class="search-result-header">
                    <span class="search-result-source">${r.source || 'Unknown source'}</span>
                    <span class="search-result-similarity">${Math.round((r.similarity || 0) * 100)}% match</span>
                </div>
                <p class="search-result-text">${escapeHtml(r.text || r.content || '')}</p>
                <div class="search-result-meta">
                    <span>Type: ${r.doc_type || 'general'}</span>
                    <span>Category: ${r.category || 'general'}</span>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Search error:', err);
        elements.searchResults.innerHTML = `
            <div class="search-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
                <p>Search failed. Please check the backend connection.</p>
            </div>
        `;
    }
}

// =========================================================
// Document Management — uses API methods with JWT auth
// =========================================================
async function loadStats() {
    try {
        const stats = await API.getKnowledgeStats();

        elements.totalDocuments.textContent = stats.total_documents || 0;
        elements.totalChunks.textContent = stats.total_chunks || 0;
        elements.totalSize.textContent = formatFileSize(stats.total_size_bytes || 0);
        elements.docTypes.textContent = Object.keys(stats.documents_by_type || {}).length;

    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

async function loadDocuments() {
    try {
        const data = await API.getKnowledgeDocuments();

        if (!data.documents || data.documents.length === 0) {
            elements.documentsTableBody.innerHTML = `
                <tr class="documents-empty">
                    <td colspan="7">
                        <div class="documents-empty-content">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                <polyline points="14 2 14 8 20 8" />
                            </svg>
                            <p>No documents indexed yet</p>
                            <span>Upload documents to get started</span>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        elements.documentsTableBody.innerHTML = data.documents.map(doc => `
            <tr>
                <td>
                    <div class="doc-name">
                        <div class="doc-icon">
                            ${getFileIcon(doc.filename || doc.source)}
                        </div>
                        ${escapeHtml(doc.filename || doc.source || 'Unknown')}
                    </div>
                </td>
                <td>${doc.doc_type || 'general'}</td>
                <td>${doc.category || 'general'}</td>
                <td>${doc.chunks || '-'}</td>
                <td>${formatFileSize(doc.size || 0)}</td>
                <td><span class="badge badge-positive">Indexed</span></td>
                <td>
                    <div class="doc-actions">
                        <button class="btn-icon btn-ghost" onclick="deleteDocument('${doc.document_id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
        const result = await API.deleteKnowledgeDocument(documentId);

        if (result.success) {
            showToast('success', 'Document Deleted', 'Document removed from knowledge base');
            loadStats();
            loadDocuments();
        } else {
            showToast('error', 'Delete Failed', result.error || 'Could not delete document');
        }
    } catch (err) {
        console.error('Delete error:', err);
        showToast('error', 'Delete Failed', 'Network error occurred');
    }
}

async function handleDeleteAll() {
    if (!confirm('Are you sure you want to delete ALL documents? This cannot be undone.')) return;

    try {
        const result = await API.deleteAllKnowledge();

        if (result.success) {
            showToast('success', 'Knowledge Base Cleared', 'All documents have been removed');
            loadStats();
            loadDocuments();
        } else {
            showToast('error', 'Clear Failed', result.error || 'Could not clear knowledge base');
        }
    } catch (err) {
        console.error('Delete all error:', err);
        showToast('error', 'Clear Failed', 'Network error occurred');
    }
}

// =========================================================
// AI Status Check
// =========================================================
async function checkAIStatus() {
    try {
        const health = await API.healthCheck();

        if (health.status === 'healthy' || health.status === 'degraded') {
            elements.aiStatus.classList.add('connected');
            elements.aiStatus.classList.remove('disconnected');
            elements.aiStatus.querySelector('.ai-status-text').textContent = 'AI Connected';
        } else {
            throw new Error('AI unhealthy');
        }
    } catch (err) {
        elements.aiStatus.classList.add('disconnected');
        elements.aiStatus.classList.remove('connected');
        elements.aiStatus.querySelector('.ai-status-text').textContent = 'AI Offline';
    }
}

// =========================================================
// Toast Notifications
// =========================================================
function showToast(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const iconPath = type === 'success'
        ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />'
        : '<circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />';

    toast.innerHTML = `
        <div class="toast-icon ${type}">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${iconPath}
            </svg>
        </div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <p class="toast-message">${message}</p>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
        </button>
    `;

    elements.toastContainer.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// =========================================================
// Utility Functions
// =========================================================
function formatFileSize(bytes) {
    if (bytes === 0) return '0 KB';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getFileIcon(filename) {
    const ext = (filename || '').split('.').pop().toLowerCase();

    const icons = {
        pdf: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>',
        docx: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M8 12h8" /><path d="M8 16h8" /></svg>',
        txt: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /></svg>',
        json: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M10 9h4" /><path d="M10 12h4" /><path d="M10 15h4" /></svg>',
        csv: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M8 13h8" /><path d="M8 17h8" /></svg>'
    };

    return icons[ext] || icons.txt;
}
