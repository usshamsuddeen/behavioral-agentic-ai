/**
 * =========================================================
 * BEHAVIORAL AGENTIC AI - Escalation Page JavaScript
 * Dynamic Escalation Queue Management
 * =========================================================
 */

// State
const escalationState = {
    conversations: [],
    filter: 'all',
    isLoading: false
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initEscalationPage();
});

/**
 * Initialize Escalation Page
 */
async function initEscalationPage() {
    setupFilters();
    await loadEscalations();
}

/**
 * Load Escalations from API
 */
async function loadEscalations() {
    showLoading();

    try {
        // Fetch escalated conversations (status='escalated')
        // OR fetch all and filter client-side if we want to show 'at risk' too
        // For now, let's try fetching 'escalated' status specifically
        let response = await API.getConversations('escalated');

        // Fallback: If no escalated returned (maybe status not updated in seed data manually),
        // let's fetch 'active' and filter by is_escalated flag just in case
        if (!response.conversations || response.conversations.length === 0) {
            const allActive = await API.getConversations('active');
            escalationState.conversations = allActive.conversations.filter(c => c.is_escalated);
        } else {
            escalationState.conversations = response.conversations;
        }

        updateStats();
        renderEscalations();

    } catch (error) {
        console.error('Failed to load escalations:', error);
        if (window.BehavioralAI?.Toast) {
            window.BehavioralAI.Toast.error('Failed to load escalation queue');
        }
    } finally {
        hideLoading();
    }
}

/**
 * Update Header Stats
 */
function updateStats() {
    const total = escalationState.conversations.length;

    // Count 'waiting' (updated > 5 mins ago) - Mock logic for demo
    // In real app, we'd check last_message timestamp vs current time
    const waiting = escalationState.conversations.filter(c => {
        const date = new Date(c.updated_at);
        const diffMins = (new Date() - date) / 60000;
        return diffMins > 5;
    }).length;

    // Update DOM
    const pendingEl = document.querySelectorAll('.escalation-stat-value')[0];
    const todayEl = document.querySelectorAll('.escalation-stat-value')[1];

    if (pendingEl) pendingEl.textContent = total;
    if (todayEl) todayEl.textContent = total + 12; // Mock "Today" count as total + some closed ones
}

/**
 * Render Escalation Cards
 */
function renderEscalations() {
    const container = document.querySelector('.escalation-grid');
    if (!container) return;

    container.innerHTML = '';

    // Filter
    let filtered = escalationState.conversations;
    if (escalationState.filter !== 'all') {
        filtered = filtered.filter(c => c.priority.toLowerCase() === escalationState.filter);
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✅</div>
                <h3>All Caught Up!</h3>
                <p>No escalated conversations found.</p>
            </div>
        `;
        return;
    }

    // Render
    filtered.forEach(conv => {
        container.innerHTML += createEscalationCard(conv);
    });

    // Update Filter Button counts
    updateFilterCounts();
}

/**
 * Create HTML for a single card
 */
function createEscalationCard(conv) {
    const priority = conv.priority.toLowerCase();
    const isUrgent = priority === 'urgent';
    const cardClass = isUrgent ? 'escalation-card--urgent' :
        priority === 'high' ? 'escalation-card--high' : '';

    const badgeClass = `priority-badge--${priority}`;

    // Calculate wait time
    const updated = new Date(conv.updated_at);
    const diffMins = Math.floor((new Date() - updated) / 60000);
    const waitTime = diffMins < 60 ? `${diffMins} min` : `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;

    return `
        <div class="escalation-card glass-card ${cardClass}">
            <div class="escalation-card-header">
                <div class="escalation-priority">
                    <span class="priority-badge ${badgeClass}">
                        ${getPriorityIcon(priority)}
                        ${conv.priority.toUpperCase()}
                    </span>
                    <span class="wait-time">Waiting: ${waitTime}</span>
                </div>
                <span class="escalation-id">#ESC-${1000 + conv.id}</span>
            </div>

            <div class="escalation-card-body">
                <div class="escalation-customer">
                    <div class="avatar avatar-lg">${conv.customer_avatar}</div>
                    <div class="customer-details">
                        <span class="customer-name">${conv.customer_name}</span>
                        <span class="customer-email">${conv.customer_email || 'No email provided'}</span>
                        <div class="customer-tags">
                            <span class="language-badge">${conv.language_flag} ${conv.detected_language.toUpperCase()}</span>
                            <span class="customer-status">Customer</span>
                        </div>
                    </div>
                </div>

                <div class="escalation-reason">
                    <h4>Escalation Context</h4>
                    <ul class="trigger-list-compact">
                        <li><span class="trigger-icon">⚠️</span> ${conv.escalation_reason || 'Manual Escalation'}</li>
                        <li><span class="trigger-icon">${conv.sentiment_emoji}</span> Sentiment: ${conv.current_sentiment}</li>
                        <li><span class="trigger-icon">💬</span> ${conv.message_count} messages exchanged</li>
                    </ul>
                </div>

                <div class="escalation-preview">
                    <div class="preview-label">Latest Message:</div>
                    <p class="preview-text">"${conv.last_message_preview || 'No messages yet...'}"</p>
                </div>
            </div>

            <div class="escalation-card-footer">
                <button class="btn btn-primary" onclick="acceptEscalation(${conv.id})">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                        <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    Accept & Handle
                </button>
                <button class="btn btn-secondary" onclick="viewContext(${conv.id})">View Analysis</button>
            </div>
        </div>
    `;
}

function getPriorityIcon(priority) {
    if (priority === 'urgent') return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /></svg>';
    if (priority === 'high') return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>';
    return '<span>•</span>';
}

/**
 * Filter Logic
 */
function setupFilters() {
    document.querySelectorAll('.escalation-filters .filter-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            // UI
            document.querySelectorAll('.escalation-filters .filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Logic
            escalationState.filter = this.dataset.filter;
            renderEscalations();
        });
    });
}

function updateFilterCounts() {
    const all = escalationState.conversations.length;
    const urgent = escalationState.conversations.filter(c => c.priority === 'urgent').length;
    const high = escalationState.conversations.filter(c => c.priority === 'high').length;
    const medium = escalationState.conversations.filter(c => c.priority === 'normal' || c.priority === 'medium').length;

    updateBtnText('all', `All (${all})`);
    updateBtnText('urgent', `Urgent (${urgent})`);
    updateBtnText('high', `High (${high})`);
    updateBtnText('medium', `Normal (${medium})`);
}

function updateBtnText(filter, text) {
    const btn = document.querySelector(`.filter-btn[data-filter="${filter}"]`);
    if (btn) btn.textContent = text;
}

/**
 * Actions
 */
window.acceptEscalation = function (id) {
    if (window.BehavioralAI?.Toast) {
        window.BehavioralAI.Toast.success(`Redirecting to conversation #${id}...`);
    }
    setTimeout(() => {
        window.location.href = `chat.html?id=${id}`;
    }, 1000);
};

window.viewContext = function (id) {
    window.location.href = `chat.html?id=${id}`; // For now same as accept
};

// Utilities
function showLoading() {
    const container = document.querySelector('.escalation-grid');
    if (container) container.innerHTML = '<div class="loading-state">Loading escalations...</div>';
}

function hideLoading() {
    // Handled by render
}
