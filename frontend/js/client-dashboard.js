/**
 * ═══════════════════════════════════════════════════════════
 * Behavioral Agentic AI — Client Dashboard (Single-Page)
 * All 6 tabs powered by api.js
 * ═══════════════════════════════════════════════════════════
 */

/* ─── State ──────────────────────────────────────────────── */
let currentTab = 'overview';
let loadedTabs = {};          // track which tabs have been initialised
let currentConvId = null;     // selected conversation
let allConversations = [];    // cached conversation list

const TAB_META = {
    overview: { title: 'Overview', subtitle: 'Welcome back — here\'s what\'s happening today' },
    conversations: { title: 'Conversations', subtitle: 'Monitor and respond to customer conversations' },
    analytics: { title: 'Analytics', subtitle: 'Insights into sentiment, escalations, and performance' },
    knowledge: { title: 'Knowledge Base', subtitle: 'Manage documents that power your AI responses' },
    widget: { title: 'Widget', subtitle: 'Configure and deploy your chat widget' },
    settings: { title: 'Settings', subtitle: 'Manage your profile, company, and preferences' },
};

/* ─── Init ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    // Auth guard
    const token = localStorage.getItem('access_token');
    if (!token) { window.location.href = 'login.html'; return; }

    loadUserInfo();
    setupTabNavigation();
    setupMobileMenu();
    setupSettingsSubNav();
    setupLogout();

    // Load initial tab from hash or default to overview
    const hash = window.location.hash.replace('#', '') || 'overview';
    switchTab(hash);
});

/* ═══════════════════════════════════════════════════════════
   USER INFO
   ═══════════════════════════════════════════════════════════ */
function loadUserInfo() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const name = user.name || user.full_name || 'User';
    const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

    document.getElementById('sidebarAvatar').textContent = initials;
    document.getElementById('sidebarName').textContent = name;
    document.getElementById('sidebarRole').textContent = user.role === 'client' ? 'Client Admin' : (user.role || 'User');
}

/* ═══════════════════════════════════════════════════════════
   TAB NAVIGATION
   ═══════════════════════════════════════════════════════════ */
function setupTabNavigation() {
    document.querySelectorAll('.nav-item[data-tab]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(item.dataset.tab);
        });
    });

    // Listen for hash changes (back/forward)
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.replace('#', '');
        if (hash && hash !== currentTab) switchTab(hash);
    });
}

function switchTab(tab) {
    if (!TAB_META[tab]) return;
    currentTab = tab;

    // Update hash
    history.replaceState(null, '', `#${tab}`);

    // Update nav highlight
    document.querySelectorAll('.nav-item[data-tab]').forEach(n => n.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[data-tab="${tab}"]`);
    if (activeNav) activeNav.classList.add('active');

    // Update header
    document.getElementById('pageTitle').textContent = TAB_META[tab].title;
    document.getElementById('pageSubtitle').textContent = TAB_META[tab].subtitle;

    // Show panel
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`panel-${tab}`);
    if (panel) panel.classList.add('active');

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').style.display = 'none';

    // Lazy-load tab data
    if (!loadedTabs[tab]) {
        loadedTabs[tab] = true;
        loadTabData(tab);
    }
}

/* ═══════════════════════════════════════════════════════════
   LAZY LOAD PER TAB
   ═══════════════════════════════════════════════════════════ */
function loadTabData(tab) {
    switch (tab) {
        case 'overview': loadOverview(); break;
        case 'conversations': loadConversations(); break;
        case 'analytics': loadAnalytics(); break;
        case 'knowledge': loadKnowledge(); break;
        case 'widget': loadWidget(); break;
        case 'settings': loadSettings(); break;
    }
}

/* ═══════════════════════════════════════════════════════════
   TAB 1: OVERVIEW
   ═══════════════════════════════════════════════════════════ */
async function loadOverview() {
    try {
        const data = await API.getDashboardMetrics();
        // /analytics/dashboard returns { overview, sentiment_distribution, recent_escalations, widget_status, language_distribution }
        const ov = data.overview || {};
        const sd = data.sentiment_distribution || {};

        // Metrics cards
        document.getElementById('metricConversations').textContent =
            (ov.total_conversations ?? 0).toLocaleString();
        document.getElementById('metricSentiment').textContent =
            ov.avg_sentiment_score != null ? (ov.avg_sentiment_score * 100).toFixed(0) + '%'
                : ov.satisfaction_score != null ? ov.satisfaction_score + '%' : 'N/A';
        document.getElementById('metricEscalations').textContent =
            ov.escalation_rate != null ? ov.escalation_rate.toFixed(1) + '%' : '0%';

        // Widget status from analytics/dashboard response
        const ws = data.widget_status || 'inactive';
        const isActive = ws === 'active';
        document.getElementById('metricWidgetStatus').innerHTML = isActive
            ? '<span class="widget-status widget-status--active"><span class="widget-status-dot"></span>Active</span>'
            : '<span class="widget-status widget-status--inactive"><span class="widget-status-dot"></span>Inactive</span>';

        // Sentiment donut
        renderSentimentDonut(sd);

        // Recent escalations from API data
        renderRecentEscalations(data.recent_escalations || []);

        // Conversation badge
        try {
            const convs = await API.getConversations('active');
            const activeCount = (convs.conversations || convs || []).length;
            const badge = document.getElementById('convBadge');
            if (activeCount > 0) {
                badge.textContent = activeCount;
                badge.style.display = '';
            }
        } catch { }
    } catch (err) {
        console.error('Overview load error:', err);
    }
}

function renderSentimentDonut(sd) {
    // sd = { positive, neutral, negative, positive_percent, neutral_percent, negative_percent }
    const pos = sd.positive || 0;
    const neu = sd.neutral || 0;
    const neg = sd.negative || 0;
    const total = pos + neu + neg || 1;

    const pPct = sd.positive_percent != null ? sd.positive_percent : Math.round(pos / total * 100);
    const nPct = sd.neutral_percent != null ? sd.neutral_percent : Math.round(neu / total * 100);
    const gPct = sd.negative_percent != null ? sd.negative_percent : (100 - pPct - nPct);

    document.getElementById('donutPositive').textContent = pPct + '%';
    document.getElementById('donutNeutral').textContent = nPct + '%';
    document.getElementById('donutNegative').textContent = gPct + '%';

    // CSS conic-gradient donut
    const chart = document.getElementById('donutChart');
    chart.style.background = `conic-gradient(
        var(--positive) 0% ${pPct}%,
        var(--neutral) ${pPct}% ${pPct + nPct}%,
        var(--negative) ${pPct + nPct}% 100%
    )`;
    chart.innerHTML = `<div class="donut-center">
        <span class="donut-center-value">${total}</span>
        <span class="donut-center-label">total</span>
    </div>`;
}

function renderRecentEscalations(escalations) {
    const container = document.getElementById('recentEscalations');
    if (!escalations || escalations.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            <p>No escalations — all clear!</p>
        </div>`;
        return;
    }
    container.innerHTML = escalations.map(c => {
        const initials = (c.customer_name || 'U').slice(0, 2).toUpperCase();
        const time = c.escalated_at ? timeAgo(c.escalated_at) : '';
        return `<div class="escalation-item" onclick="switchTab('conversations')">
            <div class="escalation-avatar">${initials}</div>
            <div class="escalation-info">
                <div class="escalation-name">${esc(c.customer_name || 'Unknown')}</div>
                <div class="escalation-reason">${esc(c.escalation_reason || 'High negative sentiment')}</div>
            </div>
            <div class="escalation-time">${time}</div>
        </div>`;
    }).join('');
}

/* ═══════════════════════════════════════════════════════════
   TAB 2: CONVERSATIONS
   ═══════════════════════════════════════════════════════════ */
async function loadConversations(statusFilter = null) {
    const container = document.getElementById('convListItems');
    container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading…</p></div>';

    try {
        const data = await API.getConversations(statusFilter);
        allConversations = data.conversations || data || [];
        renderConversationList(allConversations);
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><p>Failed to load conversations</p></div>';
    }

    setupConversationFilters();
    setupConversationSearch();
}

function renderConversationList(convs) {
    const container = document.getElementById('convListItems');
    if (convs.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No conversations found</p></div>';
        return;
    }

    container.innerHTML = convs.map(c => {
        const initials = (c.customer_name || 'U').slice(0, 2).toUpperCase();
        const preview = c.last_message_preview || c.last_message || 'No messages yet';
        const time = c.updated_at ? timeAgo(c.updated_at) : '';
        const status = c.status || 'active';
        const active = c.id === currentConvId ? 'active' : '';
        return `<div class="conv-item ${active}" data-id="${c.id}" onclick="selectConversation(${c.id})">
            <div class="conv-item-status conv-item-status--${status}"></div>
            <div class="conv-item-avatar">${initials}</div>
            <div class="conv-item-content">
                <div class="conv-item-top">
                    <span class="conv-item-name">${esc(c.customer_name || 'Unknown')}</span>
                    <span class="conv-item-time">${time}</span>
                </div>
                <div class="conv-item-preview">${esc(preview.substring(0, 60))}</div>
            </div>
        </div>`;
    }).join('');
}

function setupConversationFilters() {
    document.querySelectorAll('.conv-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.conv-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const status = btn.dataset.status === 'all' ? null : btn.dataset.status;
            loadedTabs['conversations'] = false;
            loadConversations(status);
        });
    });
}

function setupConversationSearch() {
    const input = document.getElementById('convSearch');
    input.addEventListener('input', () => {
        const q = input.value.toLowerCase();
        const filtered = allConversations.filter(c =>
            (c.customer_name || '').toLowerCase().includes(q) ||
            (c.last_message || '').toLowerCase().includes(q)
        );
        renderConversationList(filtered);
    });
}

async function selectConversation(id) {
    currentConvId = id;

    // Highlight in list
    document.querySelectorAll('.conv-item').forEach(i => i.classList.remove('active'));
    const item = document.querySelector(`.conv-item[data-id="${id}"]`);
    if (item) item.classList.add('active');

    // Show chat panel
    document.getElementById('chatEmpty').style.display = 'none';
    const chatActive = document.getElementById('chatActive');
    chatActive.style.display = 'flex';

    try {
        const data = await API.getConversation(id);
        const conv = data.conversation || data;
        const messages = data.messages || conv.messages || [];

        // Header
        const name = conv.customer_name || 'Unknown';
        document.getElementById('chatAvatar').textContent = name.slice(0, 2).toUpperCase();
        document.getElementById('chatName').textContent = name;
        document.getElementById('chatMeta').textContent =
            `${conv.status || 'active'} · ${messages.length} messages · ${conv.language || 'en'}`;

        // Render messages
        renderMessages(messages);

        // Setup actions
        setupChatActions(id, conv);
    } catch (err) {
        console.error('Failed to load conversation:', err);
    }
}

function renderMessages(messages) {
    const container = document.getElementById('chatMessages');
    if (!messages.length) {
        container.innerHTML = '<div class="empty-state"><p>No messages yet</p></div>';
        return;
    }

    container.innerHTML = messages.map(m => {
        const type = m.sender_type || 'customer';
        const label = type === 'customer' ? (m.sender_name || 'Customer').slice(0, 2).toUpperCase()
            : type === 'ai' ? 'AI'
                : '🧑';

        let sentimentBadge = '';
        if (m.sentiment_label || m.sentiment_score != null) {
            const sl = m.sentiment_label || (m.sentiment_score > 0.3 ? 'positive' : m.sentiment_score < -0.3 ? 'negative' : 'neutral');
            sentimentBadge = `<span class="msg-sentiment msg-sentiment--${sl}">${sl} ${m.sentiment_score != null ? (m.sentiment_score * 100).toFixed(0) + '%' : ''}</span>`;
        }

        const time = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

        return `<div class="msg msg--${type}">
            <div class="msg-avatar">${label}</div>
            <div>
                <div class="msg-bubble">${esc(m.content)}</div>
                ${sentimentBadge}
                <div class="msg-time">${time}</div>
            </div>
        </div>`;
    }).join('');

    container.scrollTop = container.scrollHeight;
}

function setupChatActions(convId, conv) {
    // Send message
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');

    const sendHandler = async () => {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        try {
            await API.respondToConversation(convId, text);
            await selectConversation(convId);
            showToast('Message sent', 'success');
        } catch (err) {
            showToast('Failed to send message', 'error');
        }
    };

    sendBtn.onclick = sendHandler;
    input.onkeydown = (e) => { if (e.key === 'Enter') sendHandler(); };

    // Action buttons
    document.getElementById('btnTakeover').onclick = async () => {
        try { await API.takeoverConversation(convId); showToast('Conversation taken over', 'success'); await selectConversation(convId); }
        catch { showToast('Takeover failed', 'error'); }
    };

    document.getElementById('btnEscalate').onclick = async () => {
        try { await API.escalateConversation(convId); showToast('Conversation escalated', 'info'); await selectConversation(convId); }
        catch { showToast('Escalation failed', 'error'); }
    };

    document.getElementById('btnResolve').onclick = async () => {
        try { await API.resolveConversation(convId); showToast('Conversation resolved', 'success'); await selectConversation(convId); }
        catch { showToast('Resolution failed', 'error'); }
    };
}

/* ═══════════════════════════════════════════════════════════
   TAB 3: ANALYTICS
   ═══════════════════════════════════════════════════════════ */
async function loadAnalytics() {
    try {
        const data = await API.getDashboardMetrics();
        const ov = data.overview || {};
        document.getElementById('analyticsTotal').textContent = (ov.total_conversations ?? 0).toLocaleString();
        document.getElementById('analyticsAvgSent').textContent = ov.avg_sentiment_score != null ? (ov.avg_sentiment_score * 100).toFixed(0) + '%' : 'N/A';
        document.getElementById('analyticsAvgResp').textContent = ov.avg_response_time || '< 2s';
        document.getElementById('analyticsEscRate').textContent = ov.escalation_rate != null ? ov.escalation_rate.toFixed(1) + '%' : '0%';
    } catch { }

    // Sentiment trends
    try {
        const trends = await API.getSentimentTrends(7);
        const items = trends.trends || trends || [];
        renderBarChart('sentimentTrendsChart', items.map(t => ({
            label: t.date ? t.date.slice(5) : '',
            value: (t.avg_sentiment || 0) * 100,
            type: 'primary'
        })));
    } catch { document.getElementById('sentimentTrendsChart').innerHTML = '<div class="empty-state"><p>No trend data</p></div>'; }

    // Escalation triggers
    try {
        const triggers = await API.getEscalationTriggers();
        const items = triggers.triggers || triggers || [];
        const tbody = document.getElementById('triggersBody');
        if (items.length) {
            const total = items.reduce((s, t) => s + (t.count || 0), 0) || 1;
            tbody.innerHTML = items.slice(0, 8).map(t => `<tr>
                <td>${esc(t.trigger || t.keyword || 'Unknown')}</td>
                <td>${t.count || 0}</td>
                <td>${((t.count || 0) / total * 100).toFixed(1)}%</td>
            </tr>`).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">No data yet</td></tr>';
        }
    } catch { }

    // Sentiment by language
    try {
        const langData = await API.getSentimentByLanguage();
        const items = langData.languages || langData || [];
        const tbody = document.getElementById('langBody');
        if (items.length) {
            tbody.innerHTML = items.map(l => `<tr>
                <td>${esc(l.language || 'Unknown')}</td>
                <td>${l.avg_sentiment != null ? (l.avg_sentiment * 100).toFixed(0) + '%' : 'N/A'}</td>
                <td>${l.count || 0}</td>
            </tr>`).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">No data yet</td></tr>';
        }
    } catch { }

    // Hourly activity
    try {
        const hourly = await API.getHourlyActivity();
        const items = hourly.activity || hourly || [];
        renderBarChart('hourlyActivityChart', items.map(h => ({
            label: h.hour != null ? h.hour + 'h' : '',
            value: h.count || 0,
            type: 'primary'
        })));
    } catch { document.getElementById('hourlyActivityChart').innerHTML = '<div class="empty-state"><p>No activity data</p></div>'; }
}

function renderBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!data.length) {
        container.innerHTML = '<div class="empty-state"><p>No data available</p></div>';
        return;
    }
    const maxVal = Math.max(...data.map(d => d.value), 1);
    container.innerHTML = data.map(d => {
        const h = Math.max((d.value / maxVal) * 100, 3);
        return `<div class="bar-chart-bar bar-chart-bar--${d.type || 'primary'}" style="height:${h}%">
            <span class="bar-chart-label">${d.label}</span>
        </div>`;
    }).join('');
}

/* ═══════════════════════════════════════════════════════════
   TAB 4: KNOWLEDGE BASE
   ═══════════════════════════════════════════════════════════ */
async function loadKnowledge() {
    // Stats
    try {
        const stats = await API.getKnowledgeStats();
        document.getElementById('kbDocCount').textContent = stats.total_documents ?? 0;
        document.getElementById('kbChunkCount').textContent = stats.total_chunks ?? 0;
        document.getElementById('kbTotalSize').textContent = formatFileSize(stats.total_size || 0);
    } catch { }

    // Document list
    await loadDocumentList();

    // Upload zone
    setupUploadZone();

    // Search
    document.getElementById('kbSearchBtn').onclick = async () => {
        const query = document.getElementById('kbSearchInput').value.trim();
        if (!query) return;
        const results = document.getElementById('kbSearchResults');
        results.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
        try {
            const data = await API.searchKnowledge(query, 5);
            const chunks = data.results || data || [];
            if (chunks.length === 0) {
                results.innerHTML = '<div class="empty-state" style="padding:var(--space-lg)"><p>No matching chunks found</p></div>';
            } else {
                results.innerHTML = chunks.map(c => `<div class="doc-item" style="margin-bottom:var(--space-sm)">
                    <div class="doc-info">
                        <div class="doc-name">${esc(c.document_name || c.source || 'Chunk')}</div>
                        <div class="doc-meta" style="white-space:normal;margin-top:4px;color:var(--text-secondary)">${esc((c.content || c.text || '').substring(0, 200))}…</div>
                        <div class="doc-meta">Score: ${(c.score || c.similarity || 0).toFixed(3)}</div>
                    </div>
                </div>`).join('');
            }
        } catch { results.innerHTML = '<div class="empty-state"><p>Search failed</p></div>'; }
    };

    // Delete all
    document.getElementById('deleteAllKbBtn').onclick = async () => {
        if (!confirm('Delete ALL documents from your knowledge base? This cannot be undone.')) return;
        try {
            await API.deleteAllKnowledge();
            showToast('All documents deleted', 'success');
            loadedTabs['knowledge'] = false;
            loadKnowledge();
        } catch { showToast('Delete failed', 'error'); }
    };
}

async function loadDocumentList() {
    const container = document.getElementById('docList');
    try {
        const data = await API.getKnowledgeDocuments();
        const docs = data.documents || data || [];
        if (docs.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No documents uploaded yet</p></div>';
            return;
        }
        container.innerHTML = docs.map(d => `<div class="doc-item">
            <div class="doc-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
            </div>
            <div class="doc-info">
                <div class="doc-name">${esc(d.filename || d.name || 'Document')}</div>
                <div class="doc-meta">${d.chunk_count || 0} chunks · ${formatFileSize(d.size || 0)} · ${d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}</div>
            </div>
            <button class="doc-delete" onclick="deleteDocument('${d.id || d.document_id}')" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
        </div>`).join('');
    } catch { container.innerHTML = '<div class="empty-state"><p>Failed to load documents</p></div>'; }
}

async function deleteDocument(docId) {
    if (!confirm('Delete this document?')) return;
    try {
        await API.deleteKnowledgeDocument(docId);
        showToast('Document deleted', 'success');
        loadedTabs['knowledge'] = false;
        loadKnowledge();
    } catch { showToast('Delete failed', 'error'); }
}

function setupUploadZone() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');

    zone.onclick = () => input.click();

    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    input.addEventListener('change', () => handleFiles(input.files));
}

async function handleFiles(files) {
    for (const file of files) {
        if (file.size > 10 * 1024 * 1024) {
            showToast(`${file.name} exceeds 10MB limit`, 'error');
            continue;
        }
        const formData = new FormData();
        formData.append('file', file);
        try {
            showToast(`Uploading ${file.name}…`, 'info');
            await API.upload('/knowledge/upload', formData);
            showToast(`${file.name} uploaded!`, 'success');
        } catch {
            showToast(`Failed to upload ${file.name}`, 'error');
        }
    }
    // Refresh
    loadedTabs['knowledge'] = false;
    loadKnowledge();
}

/* ═══════════════════════════════════════════════════════════
   TAB 5: WIDGET
   ═══════════════════════════════════════════════════════════ */
async function loadWidget() {
    // Load config
    try {
        const config = await API.getWidgetConfig();
        if (config) {
            document.getElementById('widgetBotName').value = config.bot_name || '';
            document.getElementById('widgetWelcome').value = config.welcome_message || '';
            document.getElementById('widgetColor').value = config.primary_color || '#3b82f6';
            document.getElementById('widgetColorText').value = config.primary_color || '#3b82f6';
            document.getElementById('widgetPosition').value = config.position || 'bottom-right';
            document.getElementById('widgetEnabled').checked = config.is_active !== false;
            updateWidgetPreview();
        }
    } catch { }

    // Load embed code
    try {
        const embed = await API.getEmbedCode();
        document.getElementById('embedCodePre').textContent = embed.embed_code || embed.code || 'No embed code available';
    } catch {
        document.getElementById('embedCodePre').textContent = '<!-- Embed code will appear after saving widget config -->';
    }

    // Live preview
    ['widgetBotName', 'widgetWelcome', 'widgetColor', 'widgetColorText'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateWidgetPreview);
    });

    // Sync color picker ↔ text
    document.getElementById('widgetColor').addEventListener('input', (e) => {
        document.getElementById('widgetColorText').value = e.target.value;
    });
    document.getElementById('widgetColorText').addEventListener('input', (e) => {
        if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) {
            document.getElementById('widgetColor').value = e.target.value;
        }
    });

    // Save
    document.getElementById('saveWidgetBtn').onclick = async () => {
        const data = {
            bot_name: document.getElementById('widgetBotName').value,
            welcome_message: document.getElementById('widgetWelcome').value,
            primary_color: document.getElementById('widgetColor').value,
            position: document.getElementById('widgetPosition').value,
            is_active: document.getElementById('widgetEnabled').checked,
        };
        try {
            await API.updateWidgetConfig(data);
            showToast('Widget configuration saved!', 'success');
            // Refresh embed code
            const embed = await API.getEmbedCode();
            document.getElementById('embedCodePre').textContent = embed.embed_code || embed.code || '';
        } catch { showToast('Failed to save config', 'error'); }
    };

    // Copy embed code
    document.getElementById('copyEmbedBtn').onclick = () => {
        const code = document.getElementById('embedCodePre').textContent;
        navigator.clipboard.writeText(code).then(() => showToast('Embed code copied!', 'success'));
    };
}

function updateWidgetPreview() {
    const color = document.getElementById('widgetColor').value;
    const name = document.getElementById('widgetBotName').value || 'AI Assistant';
    const welcome = document.getElementById('widgetWelcome').value || 'Hi! How can I help you?';

    document.getElementById('widgetPreviewHead').style.background = color;
    document.getElementById('previewBotName').textContent = name;
    document.getElementById('previewWelcome').textContent = welcome;
}

/* ═══════════════════════════════════════════════════════════
   TAB 6: SETTINGS
   ═══════════════════════════════════════════════════════════ */
async function loadSettings() {
    try {
        const resp = await API.getSettings();
        // /settings returns { profile, tenant, settings, widget, api_key, team }
        const profile = resp.profile || {};
        const tenant = resp.tenant || {};
        const prefs = resp.settings || {};
        const team = resp.team || [];

        // Profile
        document.getElementById('settingsName').value = profile.name || profile.full_name || '';
        document.getElementById('settingsEmail').value = profile.email || '';

        // Company
        document.getElementById('settingsCompanyName').value = tenant.company_name || profile.company_name || '';
        document.getElementById('settingsIndustry').value = tenant.industry || '';
        document.getElementById('settingsSupportEmail').value = tenant.support_email || '';
        document.getElementById('settingsWebsite').value = tenant.website || '';

        // Team
        renderTeamList(team);

        // API key
        document.getElementById('apiKeyValue').textContent = resp.api_key || resp.widget_api_key || '••••••••••••';

        // Preferences (from settings sub-object)
        if (prefs) {
            document.getElementById('prefEmailEscalation').checked = prefs.email_notifications !== false;
            document.getElementById('prefSoundNotif').checked = !!prefs.push_notifications;
            document.getElementById('prefSensitivity').value = prefs.auto_escalation_threshold ? (prefs.auto_escalation_threshold / 100) : 0.7;
            document.getElementById('sensitivityValue').textContent = prefs.auto_escalation_threshold ? (prefs.auto_escalation_threshold / 100).toFixed(2) : '0.70';
        }
    } catch (err) {
        console.error('Settings load error:', err);
    }

    // Save profile
    document.getElementById('saveProfileBtn').onclick = async () => {
        const data = { name: document.getElementById('settingsName').value };
        const pw = document.getElementById('settingsPassword').value;
        if (pw) {
            if (pw !== document.getElementById('settingsPasswordConfirm').value) {
                showToast('Passwords do not match', 'error'); return;
            }
            data.password = pw;
        }
        try { await API.updateProfile(data); showToast('Profile updated!', 'success'); }
        catch { showToast('Update failed', 'error'); }
    };

    // Save company
    document.getElementById('saveCompanyBtn').onclick = async () => {
        const data = {
            company_name: document.getElementById('settingsCompanyName').value,
            industry: document.getElementById('settingsIndustry').value,
            support_email: document.getElementById('settingsSupportEmail').value,
            website: document.getElementById('settingsWebsite').value,
        };
        try { await API.updateTenantSettings(data); showToast('Company settings updated!', 'success'); }
        catch { showToast('Update failed', 'error'); }
    };

    // Invite
    document.getElementById('inviteBtn').onclick = async () => {
        const data = {
            name: document.getElementById('inviteName').value,
            email: document.getElementById('inviteEmail').value,
        };
        if (!data.email) { showToast('Email is required', 'error'); return; }
        try {
            await API.inviteTeamMember(data);
            showToast('Invite sent!', 'success');
            document.getElementById('inviteName').value = '';
            document.getElementById('inviteEmail').value = '';
            loadedTabs['settings'] = false;
            loadSettings();
        } catch { showToast('Invite failed', 'error'); }
    };

    // Regen API key
    document.getElementById('regenApiKeyBtn').onclick = async () => {
        if (!confirm('Regenerate your API key? Your current embed code will stop working.')) return;
        try {
            const result = await API.regenerateApiKey();
            document.getElementById('apiKeyValue').textContent = result.api_key || result.widget_api_key || '—';
            showToast('API key regenerated', 'success');
        } catch { showToast('Regeneration failed', 'error'); }
    };

    // Copy API key
    document.getElementById('copyApiKeyBtn').onclick = () => {
        const key = document.getElementById('apiKeyValue').textContent;
        navigator.clipboard.writeText(key).then(() => showToast('API key copied!', 'success'));
    };

    // Sensitivity slider
    document.getElementById('prefSensitivity').addEventListener('input', (e) => {
        document.getElementById('sensitivityValue').textContent = e.target.value;
    });

    // Save preferences
    document.getElementById('savePrefsBtn').onclick = async () => {
        const data = {
            email_escalation: document.getElementById('prefEmailEscalation').checked,
            sound_notifications: document.getElementById('prefSoundNotif').checked,
            escalation_sensitivity: parseFloat(document.getElementById('prefSensitivity').value),
        };
        try { await API.updatePreferences(data); showToast('Preferences saved!', 'success'); }
        catch { showToast('Update failed', 'error'); }
    };
}

function renderTeamList(team) {
    const container = document.getElementById('teamList');
    if (!team.length) {
        container.innerHTML = '<div class="empty-state"><p>No team members yet</p></div>';
        return;
    }
    container.innerHTML = team.map(m => `<div class="team-item">
        <div class="avatar avatar-sm">${(m.name || 'U').slice(0, 2).toUpperCase()}</div>
        <div class="team-item-info">
            <div class="team-item-name">${esc(m.name || 'Unknown')}</div>
            <div class="team-item-email">${esc(m.email || '')}</div>
        </div>
        <button class="doc-delete" onclick="removeTeamMember('${m.id}')" title="Remove">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
    </div>`).join('');
}

async function removeTeamMember(id) {
    if (!confirm('Remove this team member?')) return;
    try {
        await API.removeTeamMember(id);
        showToast('Member removed', 'success');
        loadedTabs['settings'] = false;
        loadSettings();
    } catch { showToast('Remove failed', 'error'); }
}

/* ═══════════════════════════════════════════════════════════
   SETTINGS SUB-NAV
   ═══════════════════════════════════════════════════════════ */
function setupSettingsSubNav() {
    const map = {
        profile: 'settingsProfile',
        company: 'settingsCompany',
        team: 'settingsTeam',
        api: 'settingsApi',
        preferences: 'settingsPreferences',
    };
    document.querySelectorAll('.settings-nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.settings-nav-item').forEach(n => n.classList.remove('active'));
            document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
            item.classList.add('active');
            const panel = document.getElementById(map[item.dataset.settings]);
            if (panel) panel.classList.add('active');
        });
    });
}

/* ═══════════════════════════════════════════════════════════
   MOBILE MENU
   ═══════════════════════════════════════════════════════════ */
function setupMobileMenu() {
    document.getElementById('mobileToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
        const overlay = document.getElementById('sidebarOverlay');
        overlay.style.display = overlay.style.display === 'block' ? 'none' : 'block';
    });
    document.getElementById('sidebarOverlay').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebarOverlay').style.display = 'none';
    });
}

/* ═══════════════════════════════════════════════════════════
   LOGOUT
   ═══════════════════════════════════════════════════════════ */
function setupLogout() {
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    });
}

/* ═══════════════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════════════ */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast toast--${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function timeAgo(dateStr) {
    const diff = Date.now() - new Date(dateStr).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1) return 'now';
    if (m < 60) return m + 'm ago';
    const h = Math.floor(m / 60);
    if (h < 24) return h + 'h ago';
    return Math.floor(h / 24) + 'd ago';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// Make switchTab globally accessible (used by onclick in HTML)
window.switchTab = switchTab;
window.selectConversation = selectConversation;
window.deleteDocument = deleteDocument;
window.removeTeamMember = removeTeamMember;
