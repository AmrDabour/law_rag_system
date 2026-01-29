/**
 * Law RAG Admin - JavaScript Module
 * API integration and UI management
 */

// ========================================
// Configuration
// ========================================
const API_BASE = '/api/v1';
const COUNTRIES = {
    egypt: { name: 'Egypt', flag: '🇪🇬', nameAr: 'مصر' },
    jordan: { name: 'Jordan', flag: '🇯🇴', nameAr: 'الأردن' },
    uae: { name: 'UAE', flag: '🇦🇪', nameAr: 'الإمارات' },
    saudi: { name: 'Saudi Arabia', flag: '🇸🇦', nameAr: 'السعودية' },
    kuwait: { name: 'Kuwait', flag: '🇰🇼', nameAr: 'الكويت' }
};

const LAW_TYPES = [
    { value: 'criminal', label: 'Criminal Law', labelAr: 'قانون جنائي' },
    { value: 'civil', label: 'Civil Law', labelAr: 'قانون مدني' },
    { value: 'commercial', label: 'Commercial Law', labelAr: 'قانون تجاري' },
    { value: 'economic', label: 'Economic Law', labelAr: 'قانون اقتصادي' },
    { value: 'administrative', label: 'Administrative Law', labelAr: 'قانون إداري' },
    { value: 'arbitration', label: 'Arbitration Law', labelAr: 'قانون تحكيم' },
    { value: 'labor', label: 'Labor Law', labelAr: 'قانون عمل' },
    { value: 'personal_status', label: 'Personal Status', labelAr: 'أحوال شخصية' }
];

// ========================================
// State
// ========================================
let currentSection = 'dashboard';
let systemStatus = { healthy: false };
let countriesData = {};
let currentSessionId = null;
let chatMessages = [];

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initForms();
    initChat();
    loadDashboard();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            if (section) {
                switchSection(section);
            }
        });
    });
}

function switchSection(section) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(el => {
        el.classList.toggle('active', el.id === `section-${section}`);
    });

    currentSection = section;

    // Load section data
    switch (section) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'laws':
            loadLaws();
            break;
        case 'sessions':
            loadSessions();
            break;
    }
}

// ========================================
// API Utilities
// ========================================
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ========================================
// Toast Notifications
// ========================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    <span>${message}</span>
  `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ========================================
// Dashboard
// ========================================
async function loadDashboard() {
    await Promise.all([
        checkHealth(),
        loadCountryStats()
    ]);
}

async function checkHealth() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-badge span');

    try {
        const [health, ready] = await Promise.all([
            apiRequest('/health'),
            apiRequest('/ready')
        ]);

        systemStatus.healthy = health.status === 'healthy' && ready.ready;
        statusDot.classList.toggle('offline', !systemStatus.healthy);
        statusText.textContent = systemStatus.healthy ? 'System Online' : 'System Offline';

        // Update dashboard stats - API returns qdrant/redis as "ok" in health
        document.getElementById('stat-qdrant').textContent = health.qdrant === 'ok' ? '✓' : '✗';
        document.getElementById('stat-redis').textContent = health.redis === 'ok' ? '✓' : '✗';

        // Check if all models are loaded
        const allModelsLoaded = ready.models_loaded &&
            Object.values(ready.models_loaded).every(v => v === true);
        document.getElementById('stat-models').textContent = allModelsLoaded ? '✓' : '✗';

    } catch (error) {
        systemStatus.healthy = false;
        statusDot.classList.add('offline');
        statusText.textContent = 'System Offline';
        showToast('Failed to connect to backend', 'error');
    }
}

async function loadCountryStats() {
    try {
        const response = await apiRequest(`${API_BASE}/laws`);
        countriesData = response.countries || {};

        let totalPoints = 0;
        let activeCountries = 0;

        Object.values(countriesData).forEach(country => {
            totalPoints += country.points_count || 0;
            if (country.status === 'active') activeCountries++;
        });

        document.getElementById('stat-countries').textContent = activeCountries;
        document.getElementById('stat-documents').textContent = totalPoints.toLocaleString();

        renderCountriesTable();

    } catch (error) {
        showToast('Failed to load country stats', 'error');
    }
}

function renderCountriesTable() {
    // Get both tables (Dashboard and Laws Management have separate tbodies)
    const tbodyDashboard = document.getElementById('countries-tbody');
    const tbodyLaws = document.getElementById('countries-tbody-laws');

    const tableHTML = Object.entries(countriesData).map(([code, data]) => {
        const country = COUNTRIES[code] || { name: code, flag: '🏳️' };
        return `
      <tr>
        <td>
          <span class="country-flag">${country.flag}</span>
          ${country.name}
        </td>
        <td>${data.collection || `laws_${code}`}</td>
        <td>${(data.points_count || 0).toLocaleString()}</td>
        <td>
          <span class="badge ${data.status === 'active' ? 'badge-success' : 'badge-warning'}">
            ${data.status || 'unknown'}
          </span>
        </td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="viewCountry('${code}')">
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn btn-secondary btn-sm" onclick="resetCountry('${code}')">
            <i class="fas fa-sync"></i>
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteCountry('${code}')">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
    }).join('');

    // Populate both tables
    if (tbodyDashboard) tbodyDashboard.innerHTML = tableHTML;
    if (tbodyLaws) tbodyLaws.innerHTML = tableHTML;
}

// ========================================
// Laws Management
// ========================================
async function loadLaws() {
    await loadCountryStats();
}

async function viewCountry(code) {
    try {
        const data = await apiRequest(`${API_BASE}/laws/${code}`);
        const country = COUNTRIES[code] || { name: code };

        let message = `${country.flag} ${country.name}\n`;
        message += `Status: ${data.status}\n`;
        if (data.stats) {
            message += `Documents: ${data.stats.points_count}\n`;
        }

        alert(message);
    } catch (error) {
        showToast(`Failed to load ${code} details: ${error.message}`, 'error');
    }
}

async function resetCountry(code) {
    const country = COUNTRIES[code] || { name: code };
    if (!confirm(`Reset ${country.name}? This will delete all data and recreate the collection.`)) {
        return;
    }

    try {
        await apiRequest(`${API_BASE}/laws/${code}/reset`, { method: 'POST' });
        showToast(`${country.name} collection reset successfully`, 'success');
        await loadCountryStats();
    } catch (error) {
        showToast(`Failed to reset ${code}: ${error.message}`, 'error');
    }
}

async function deleteCountry(code) {
    const country = COUNTRIES[code] || { name: code };
    if (!confirm(`Delete all laws for ${country.name}? This cannot be undone!`)) {
        return;
    }

    try {
        await apiRequest(`${API_BASE}/laws/${code}`, { method: 'DELETE' });
        showToast(`${country.name} laws deleted successfully`, 'success');
        await loadCountryStats();
    } catch (error) {
        showToast(`Failed to delete ${code}: ${error.message}`, 'error');
    }
}

// ========================================
// PDF Ingestion
// ========================================
function initForms() {
    // File upload drag & drop
    const fileUpload = document.getElementById('file-upload');
    const fileInput = document.getElementById('pdf-file');

    if (fileUpload && fileInput) {
        fileUpload.addEventListener('click', () => fileInput.click());

        fileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUpload.classList.add('dragover');
        });

        fileUpload.addEventListener('dragleave', () => {
            fileUpload.classList.remove('dragover');
        });

        fileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUpload.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileName();
            }
        });

        fileInput.addEventListener('change', updateFileName);
    }

    // Ingest form
    const ingestForm = document.getElementById('ingest-form');
    if (ingestForm) {
        ingestForm.addEventListener('submit', handleIngest);
    }
}

function updateFileName() {
    const fileInput = document.getElementById('pdf-file');
    const fileNameEl = document.getElementById('file-name');

    if (fileInput.files.length) {
        fileNameEl.innerHTML = `<i class="fas fa-file-pdf"></i> ${fileInput.files[0].name}`;
        fileNameEl.style.display = 'inline-flex';
    } else {
        fileNameEl.style.display = 'none';
    }
}

async function handleIngest(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const fileInput = document.getElementById('pdf-file');
    if (!fileInput.files.length) {
        showToast('Please select a PDF file', 'warning');
        return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner"></div> Processing...';

    try {
        const response = await fetch(`${API_BASE}/ingest`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Ingestion failed');
        }

        showToast(`Ingested ${data.articles_found} articles, ${data.chunks_created} chunks`, 'success');
        form.reset();
        document.getElementById('file-name').style.display = 'none';
        await loadCountryStats();

    } catch (error) {
        showToast(`Ingestion failed: ${error.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// ========================================
// Chat Interface
// ========================================
function initChat() {
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleChat);
    }

    // Enter to send
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }
}

async function handleChat(e) {
    e.preventDefault();

    const input = document.getElementById('chat-input');
    const question = input.value.trim();

    if (!question) return;

    const country = document.getElementById('chat-country').value;
    const messages = document.getElementById('chat-messages');

    // Add user message
    addChatMessage(question, 'user');
    input.value = '';

    // Show typing indicator
    const typingId = showTyping();

    try {
        const response = await apiRequest(`${API_BASE}/query`, {
            method: 'POST',
            body: JSON.stringify({
                question,
                country,
                session_id: currentSessionId,
                top_k: 5
            })
        });

        removeTyping(typingId);

        // Add assistant message with sources
        addChatMessage(response.answer, 'assistant', response.sources);

        // Show metadata
        if (response.metadata) {
            console.log('Query metadata:', response.metadata);
        }

    } catch (error) {
        removeTyping(typingId);
        showToast(`Query failed: ${error.message}`, 'error');
        addChatMessage(`Error: ${error.message}`, 'assistant');
    }
}

function addChatMessage(content, role, sources = null) {
    const messages = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    if (role === 'assistant') {
        div.setAttribute('dir', 'rtl');
    }

    let html = content;

    if (sources && sources.length > 0) {
        html += `
      <div class="sources-section">
        <div class="sources-title">المصادر (Sources)</div>
        ${sources.map(s => `
          <div class="source-item">
            <span class="source-law">${s.law_name}</span>
            ${s.article_number ? `<span class="source-article"> - مادة ${s.article_number}</span>` : ''}
            <div class="source-preview">${s.content_preview?.substring(0, 150)}...</div>
          </div>
        `).join('')}
      </div>
    `;
    }

    div.innerHTML = html;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function showTyping() {
    const messages = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message assistant typing';
    div.id = 'typing-' + Date.now();
    div.innerHTML = '<div class="spinner"></div> جاري الإجابة...';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div.id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChat() {
    document.getElementById('chat-messages').innerHTML = '';
    chatMessages = [];
    currentSessionId = null;
}

// ========================================
// Sessions Management
// ========================================
async function loadSessions() {
    const container = document.getElementById('sessions-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div> Loading sessions...</div>';

    try {
        const response = await apiRequest(`${API_BASE}/sessions`);

        if (!response.sessions || response.sessions.length === 0) {
            container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-comments"></i>
          <p>No active sessions</p>
        </div>
      `;
            return;
        }

        container.innerHTML = '';
        response.sessions.forEach(sessionId => {
            const div = document.createElement('div');
            div.className = 'session-item';
            div.innerHTML = `
        <div class="session-info">
          <div class="session-id">${sessionId}</div>
        </div>
        <div class="session-actions">
          <button class="btn btn-secondary btn-sm" onclick="viewSession('${sessionId}')">
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteSession('${sessionId}')">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `;
            container.appendChild(div);
        });

        document.getElementById('stat-sessions').textContent = response.count || 0;

    } catch (error) {
        container.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-exclamation-triangle"></i>
        <p>Failed to load sessions</p>
      </div>
    `;
        showToast('Failed to load sessions', 'error');
    }
}

async function createSession() {
    try {
        const response = await apiRequest(`${API_BASE}/sessions`, {
            method: 'POST',
            body: JSON.stringify({})
        });

        currentSessionId = response.session_id;

        // Clear chat and switch to chat section
        clearChat();
        switchSection('chat');

        // Add welcome message with session info
        addChatMessage(
            `مرحباً! جلسة جديدة تم إنشاؤها.\\nSession ID: ${currentSessionId.substring(0, 8)}...\\n\\nيمكنك سؤالي عن أي قانون.`,
            'assistant'
        );

        showToast(`New session started`, 'success');

    } catch (error) {
        showToast(`Failed to create session: ${error.message}`, 'error');
    }
}

async function viewSession(sessionId) {
    try {
        const response = await apiRequest(`${API_BASE}/sessions/${sessionId}`);

        // Switch to chat and load messages
        switchSection('chat');
        clearChat();
        currentSessionId = sessionId;

        if (response.messages) {
            response.messages.forEach(msg => {
                addChatMessage(msg.content, msg.role);
            });
        }

        showToast('Session loaded', 'success');

    } catch (error) {
        showToast(`Failed to load session: ${error.message}`, 'error');
    }
}

async function deleteSession(sessionId) {
    if (!confirm('Delete this session?')) return;

    try {
        await apiRequest(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
        showToast('Session deleted', 'success');
        await loadSessions();

    } catch (error) {
        showToast(`Failed to delete session: ${error.message}`, 'error');
    }
}

// ========================================
// Utility Functions
// ========================================
function refreshData() {
    switch (currentSection) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'laws':
            loadLaws();
            break;
        case 'sessions':
            loadSessions();
            break;
        case 'chunks':
            loadChunks();
            break;
    }
    showToast('Data refreshed', 'success');
}

// ========================================
// Chunk Inspector
// ========================================
let chunksOffset = 0;
const chunksLimit = 20;
let chunksTotal = 0;
let currentChunks = [];

async function loadChunks(offset = 0) {
    const country = document.getElementById('chunks-country').value;
    const container = document.getElementById('chunks-container');
    const pagination = document.getElementById('chunks-pagination');

    container.innerHTML = '<div class="loading"><div class="spinner"></div> Loading chunks...</div>';

    try {
        const response = await apiRequest(`${API_BASE}/laws/${country}/chunks?offset=${offset}&limit=${chunksLimit}`);

        chunksOffset = offset;
        chunksTotal = response.total;
        currentChunks = response.chunks;

        if (!response.chunks || response.chunks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No chunks found for ${COUNTRIES[country]?.name || country}</p>
                </div>
            `;
            pagination.style.display = 'none';
            return;
        }

        // Render chunks
        container.innerHTML = `
            <div class="chunks-info">
                Showing ${offset + 1}-${Math.min(offset + response.chunks.length, response.total)} of ${response.total} chunks
            </div>
            <div class="chunks-list">
                ${response.chunks.map((chunk, idx) => `
                    <div class="chunk-card" onclick="viewChunk(${idx})">
                        <div class="chunk-header">
                            <span class="chunk-law">${chunk.law_name}</span>
                            <span class="chunk-type badge">${chunk.law_type}</span>
                        </div>
                        <div class="chunk-meta">
                            ${chunk.article_number ? `مادة ${chunk.article_number}` : ''}
                            ${chunk.page_number ? `| Page ${chunk.page_number}` : ''}
                        </div>
                        <div class="chunk-preview" dir="rtl">${escapeHtml(chunk.content)}</div>
                        <div class="chunk-footer">
                            <span class="chunk-id">ID: ${chunk.id.substring(0, 8)}...</span>
                            <i class="fas fa-expand-alt"></i>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Render pagination
        const totalPages = Math.ceil(response.total / chunksLimit);
        const currentPage = Math.floor(offset / chunksLimit) + 1;

        pagination.style.display = 'flex';
        pagination.innerHTML = `
            <button class="btn btn-secondary btn-sm" ${offset === 0 ? 'disabled' : ''} onclick="loadChunks(${offset - chunksLimit})">
                <i class="fas fa-chevron-left"></i> Previous
            </button>
            <span class="pagination-info">Page ${currentPage} of ${totalPages}</span>
            <button class="btn btn-secondary btn-sm" ${!response.has_more ? 'disabled' : ''} onclick="loadChunks(${offset + chunksLimit})">
                Next <i class="fas fa-chevron-right"></i>
            </button>
        `;

    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Failed to load chunks: ${error.message}</p>
            </div>
        `;
        pagination.style.display = 'none';
        showToast('Failed to load chunks', 'error');
    }
}

function viewChunk(index) {
    const chunk = currentChunks[index];
    if (!chunk) return;

    const modal = document.getElementById('chunk-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');

    title.textContent = `${chunk.law_name} - مادة ${chunk.article_number || 'N/A'}`;

    body.innerHTML = `
        <div class="chunk-detail">
            <div class="detail-row">
                <strong>Law Name:</strong> ${chunk.law_name}
            </div>
            <div class="detail-row">
                <strong>Law Type:</strong> ${chunk.law_type}
            </div>
            <div class="detail-row">
                <strong>Article Number:</strong> ${chunk.article_number || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Page Number:</strong> ${chunk.page_number || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Chunk ID:</strong> <code>${chunk.id}</code>
            </div>
            <hr>
            <div class="detail-content">
                <strong>Full Content:</strong>
                <div class="content-box">${escapeHtml(chunk.full_content)}</div>
            </div>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeChunkModal() {
    document.getElementById('chunk-modal').style.display = 'none';
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('chunk-modal');
    if (e.target === modal) {
        closeChunkModal();
    }
});

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
