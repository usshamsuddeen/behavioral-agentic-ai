/**
 * ***********************************************************
 * Behavioral Agentic AI - Client Dashboard (Single-Page)
 * All 8 tabs powered by api.js (FRD v4.0)
 * ***********************************************************
 */

/* --- State ------------------------------------------------ */
let currentTab = 'overview';
let loadedTabs = {};          // track which tabs have been initialised
let currentConvId = null;     // selected conversation
let allConversations = [];    // cached conversation list

/* --- Timezone Helpers -------------------------------------- */
let TENANT_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone; // default: browser tz

/** Format date in tenant's timezone: "March 14, 2026" */
function tzDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
        return new Date(isoStr).toLocaleDateString('en-US', {
            timeZone: TENANT_TZ, year: 'numeric', month: 'long', day: 'numeric'
        });
    } catch { return new Date(isoStr).toLocaleDateString(); }
}

/** Format time in tenant's timezone: "02:30 PM" */
function tzTime(isoStr) {
    if (!isoStr) return '';
    try {
        return new Date(isoStr).toLocaleTimeString('en-US', {
            timeZone: TENANT_TZ, hour: '2-digit', minute: '2-digit'
        });
    } catch { return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
}

/** Format full datetime in tenant's timezone: "Mar 14, 2026, 2:30 PM" */
function tzDateTime(isoStr) {
    if (!isoStr) return 'N/A';
    try {
        return new Date(isoStr).toLocaleString('en-US', {
            timeZone: TENANT_TZ, year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch { return new Date(isoStr).toLocaleString(); }
}

/** Format short date in tenant's timezone: "3/14/2026" */
function tzShortDate(isoStr) {
    if (!isoStr) return '--';
    try {
        return new Date(isoStr).toLocaleDateString('en-US', { timeZone: TENANT_TZ });
    } catch { return new Date(isoStr).toLocaleDateString(); }
}

const TAB_META = {
    overview: { title: 'Overview', subtitle: 'Welcome back - here\'s what\'s happening today' },
    conversations: { title: 'Conversations', subtitle: 'Monitor and respond to customer conversations' },
    orders: { title: 'Order Data', subtitle: 'Manage order data for AI order-tracking queries' },
    products: { title: 'Products', subtitle: 'Manage product listings for your AI catalog' },
    widget: { title: 'Widget Config', subtitle: 'Configure and deploy your chat widget' },
    analytics: { title: 'Analytics', subtitle: 'Insights into sentiment, escalations, and performance' },
    settings: { title: 'Settings', subtitle: 'Manage your profile, company, and preferences' },
    'kb-about': { title: 'Restrictions / Rules', subtitle: 'Set instructions and restrictions that guide your AI chatbot\'s behavior' },
    'kb-custom': { title: 'Custom Data', subtitle: 'Upload policies, FAQs, company info, and any knowledge base documents' },
};

/* --- Init ------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    // Auth guard
    const token = localStorage.getItem('access_token');
    if (!token) { window.location.href = '/pages/login.html'; return; }

    // Eagerly load tenant timezone for all date formatting
    (async () => {
        try {
            const resp = await API.getSettings();
            if (resp?.tenant?.timezone) TENANT_TZ = resp.tenant.timezone;
        } catch (_) {}
    })();

    loadUserInfo();
    setupTabNavigation();

    setupMobileMenu();
    setupLogout();
    setupUploadZones();

    // Load initial tab from hash or default to overview
    const hash = window.location.hash.replace('#', '') || 'overview';
    switchTab(hash);
});

/* ***********************************************************
   USER INFO
   *********************************************************** */
function loadUserInfo() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const name = user.name || user.full_name || 'User';
    const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

    document.getElementById('sidebarAvatar').textContent = initials;
    document.getElementById('sidebarName').textContent = name;
    document.getElementById('sidebarRole').textContent = user.role === 'client' ? 'Client Admin' : (user.role || 'User');
}

/* ***********************************************************
   TAB NAVIGATION
   *********************************************************** */
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

    // Lazy-load tab data (orders/products/kb always refresh for fresh data)
    const alwaysRefresh = ['orders', 'products', 'kb-about', 'kb-custom'];
    if (alwaysRefresh.includes(tab) || !loadedTabs[tab]) {
        loadedTabs[tab] = true;
        loadTabData(tab);
    }
}

/* ***********************************************************
   LAZY LOAD PER TAB
   *********************************************************** */
function loadTabData(tab) {
    switch (tab) {
        case 'overview': loadOverview(); break;
        case 'conversations': loadConversations(); break;
        case 'analytics': loadAnalytics(); break;
        case 'orders': loadOrders(); break;
        case 'products': loadProducts(); break;
        case 'widget': loadWidget(); break;
        case 'settings': loadSettings(); break;
        case 'kb-about': loadRestrictionsTab(); break;
        case 'kb-custom': loadCustomDataTab(); break;
    }
}

async function loadOverview() {
    try {
        // Fetch comprehensive data (gives us KPIs, pipeline, etc.)
        const [dashData, compData] = await Promise.all([
            API.getDashboardMetrics(),
            API.getComprehensiveAnalytics('7d')
        ]);

        const ov = dashData.overview || {};
        const k = compData.kpis || {};
        const pipeline = compData.order_pipeline || {};

        // ── 6 KPI Cards ──
        _ovSet('ovKpiConversations', (k.total_conversations ?? ov.total_conversations ?? 0).toLocaleString());
        _ovSet('ovKpiActive', (k.active_conversations ?? ov.active_conversations ?? 0).toLocaleString());
        _ovSet('ovKpiOrders', (k.total_orders ?? 0).toLocaleString());
        _ovSet('ovKpiRevenue', '$' + (k.total_revenue ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        _ovSet('ovKpiProducts', (k.products ?? 0).toLocaleString());
        _ovSet('ovKpiKbDocs', (k.kb_documents ?? 0).toLocaleString());

        // ── System Status — Infrastructure ──
        // API health check
        const apiDot = document.getElementById('ovSsDotApi');
        const apiBadge = document.getElementById('ovSsApi');
        try {
            await API.healthCheck();
            if (apiDot) apiDot.className = 'ss-dot ss-dot--green';
            if (apiBadge) { apiBadge.textContent = 'Online'; apiBadge.className = 'ss-row-badge ss-row-badge--ok'; }
        } catch {
            if (apiDot) apiDot.className = 'ss-dot ss-dot--red';
            if (apiBadge) { apiBadge.textContent = 'Offline'; apiBadge.className = 'ss-row-badge ss-row-badge--err'; }
        }

        // Widget status
        const ws = dashData.widget_status || 'inactive';
        const isActive = ws === 'active';
        const wDot = document.getElementById('ovSsDotWidget');
        const wBadge = document.getElementById('ovSsWidget');
        if (wDot) wDot.className = 'ss-dot ' + (isActive ? 'ss-dot--green' : 'ss-dot--red');
        if (wBadge) {
            wBadge.textContent = isActive ? 'Active' : 'Inactive';
            wBadge.className = 'ss-row-badge ' + (isActive ? 'ss-row-badge--ok' : 'ss-row-badge--err');
        }

        // Response time
        _ovSet('ovSsResponseTime', k.avg_response_time || '< 2s');

        // ── System Status — Quality Metrics ──
        const escRate = k.escalation_rate ?? ov.escalation_rate ?? 0;
        const escDot = document.getElementById('ovSsDotEsc');
        if (escDot) escDot.className = 'ss-dot ' + (escRate > 15 ? 'ss-dot--red' : escRate > 5 ? 'ss-dot--orange' : 'ss-dot--green');
        _ovSet('ovSsEscalation', escRate.toFixed(1) + '%');
        const escBar = document.getElementById('ovSsEscBar');
        if (escBar) escBar.style.width = Math.min(escRate, 100) + '%';

        // Last checked timestamp
        const lcEl = document.getElementById('ovSsLastChecked');
        if (lcEl) lcEl.textContent = 'Checked ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // ── Order Pipeline ──
        _ovRenderPipeline(pipeline, k.total_orders || 0, k.total_revenue || 0, k.avg_order_value || 0);

        // ── Recent Orders (inside Pipeline card) ──
        try {
            const ordersData = await API.getOrders(1, 5);
            const orders = ordersData.orders || ordersData || [];
            _renderRecentOrdersInto('ovRecentOrders', orders);
        } catch { _renderRecentOrdersInto('ovRecentOrders', []); }

        // ── Recent Escalations (kept) ──
        renderRecentEscalations(dashData.recent_escalations || []);

        // ── Conversation badge ──
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

function _ovSet(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function _ovRenderPipeline(pipeline, totalOrders, totalRevenue, avgOrderValue) {
    const body = document.getElementById('ovPipelineBody');
    const badge = document.getElementById('ovPipelineTotal');
    if (!body) return;
    if (badge) badge.textContent = totalOrders ? totalOrders + ' orders' : '';

    const stages = [
        { key: 'pending',    label: 'Pending',    color: '#f59e0b', icon: '⏳' },
        { key: 'confirmed',  label: 'Confirmed',  color: '#3b82f6', icon: '✓' },
        { key: 'processing', label: 'Processing', color: '#8b5cf6', icon: '⚙' },
        { key: 'shipped',    label: 'Shipped',    color: '#22d3ee', icon: '📦' },
        { key: 'delivered',  label: 'Delivered',  color: '#10b981', icon: '✅' },
        { key: 'cancelled',  label: 'Cancelled',  color: '#ef4444', icon: '✕' },
    ];

    const maxCount = Math.max(...stages.map(s => pipeline[s.key] || 0), 1);
    const hasData = stages.some(s => (pipeline[s.key] || 0) > 0);

    if (!hasData) {
        body.innerHTML = `<div class="pipeline-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
            <div>No orders in pipeline yet</div>
        </div>`;
        return;
    }

    // Summary strip
    const summaryHTML = `<div class="pl-summary">
        <div class="pl-summary-item"><span class="pl-summary-val">${totalOrders.toLocaleString()}</span><span class="pl-summary-label">Total</span></div>
        <div class="pl-summary-item"><span class="pl-summary-val">$${totalRevenue.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0})}</span><span class="pl-summary-label">Revenue</span></div>
        <div class="pl-summary-item"><span class="pl-summary-val">$${avgOrderValue.toFixed(0)}</span><span class="pl-summary-label">Avg Order</span></div>
    </div>`;

    // Stage bars with percentage
    const stagesHTML = stages.filter(s => (pipeline[s.key] || 0) > 0).map(s => {
        const count = pipeline[s.key] || 0;
        const pct = Math.max((count / maxCount) * 100, 4);
        const pctOfTotal = ((count / totalOrders) * 100).toFixed(0);
        return `<div class="pipeline-stage">
            <span class="pipeline-dot" style="background:${s.color};color:${s.color}"></span>
            <span class="pipeline-label">${s.label}</span>
            <div class="pipeline-bar-track"><div class="pipeline-bar-fill" style="width:${pct}%;background:${s.color}"></div></div>
            <span class="pipeline-count">${count}</span>
            <span class="pipeline-pct" style="color:${s.color}">${pctOfTotal}%</span>
        </div>`;
    }).join('');

    body.innerHTML = summaryHTML + '<div class="pipeline-stages">' + stagesHTML + '</div>';
}

function _renderRecentOrdersInto(containerId, orders, limit = 5) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!orders || orders.length === 0) {
        container.innerHTML = `<div class="pipeline-empty" style="padding:12px 16px">
            <div style="font-size:.8125rem;color:var(--text-muted)">No recent orders</div>
        </div>`;
        return;
    }

    const STATUS_COLORS = {
        pending: '#f59e0b', confirmed: '#3b82f6', processing: '#8b5cf6',
        shipped: '#22d3ee', delivered: '#10b981', cancelled: '#ef4444', refunded: '#ef4444'
    };

    container.innerHTML = orders.slice(0, limit).map(o => {
        const color = STATUS_COLORS[o.status] || '#8b5cf6';
        const amount = o.total_amount ? `${o.currency || '$'}${parseFloat(o.total_amount).toFixed(2)}` : '';
        return `<div class="ro-item" onclick="switchTab('orders')">
            <div class="ro-item-left">
                <span class="ro-item-id">#${esc(o.order_id)}</span>
                <span class="ro-item-customer">${esc(o.customer_name || 'Guest')}</span>
            </div>
            <div class="ro-item-right">
                <span class="ro-item-amount">${amount}</span>
                <span class="ro-item-status" style="background:${color}20;color:${color};border:1px solid ${color}40">${o.status}</span>
            </div>
        </div>`;
    }).join('');
}
function renderRecentEscalations(escalations) {
    const container = document.getElementById('recentEscalations');
    if (!escalations || escalations.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            <p>No escalations - all clear!</p>
        </div>`;
        return;
    }
    container.innerHTML = escalations.map(c => {
        const time = c.escalated_at ? timeAgo(c.escalated_at) : '';
        return `<div class="escalation-item" onclick="switchTab('conversations')">
            <div class="escalation-item-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
            <div class="escalation-item-info">
                <div class="escalation-item-name">${esc(c.customer_name || 'Unknown')}</div>
                <div class="escalation-item-reason">${esc(c.escalation_reason || 'High negative sentiment')}</div>
            </div>
            <div class="escalation-item-time">${time}</div>
        </div>`;
    }).join('');
}

/* ***********************************************************
   TAB 2: CONVERSATIONS
   *********************************************************** */
async function loadConversations(statusFilter = null) {
    const container = document.getElementById('convListItems');
    container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading</p></div>';

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
            `${conv.status || 'active'} | ${messages.length} messages | ${conv.language || 'en'}`;

        // Render messages
        renderMessages(messages);

        // Setup actions
        setupChatActions(id, conv);
    } catch (err) {
        console.error('Failed to load conversation:', err);
    }
}

function formatMessageContent(content) {
    if (!content) return '';
    if (!content.includes('[IMAGE:')) return esc(content);
    // Parse [IMAGE:url] tags ' rendered <img>, text parts escaped
    return content.split(/\[IMAGE:(.*?)\]/g).map((part, i) => {
        if (i % 2 === 0) return esc(part.trim());
        const url = part.trim();
        if (!url) return '';
        return `<img src="${esc(url)}" alt="Product" class="chat-product-img" loading="lazy" onerror="this.style.display='none'" onclick="window.open('${esc(url)}','_blank')">`;
    }).filter(Boolean).join('');
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
                : 'AG';

        // -- Sentiment Pill Badge (hero section style) --------
        let sentimentBadge = '';
        if ((m.sentiment_label || m.sentiment_score != null) && type !== 'ai') {
            const score = m.sentiment_score != null ? m.sentiment_score : 0.5;
            const pct = Math.round(score * 100);

            // Customer messages only -> colorful pill by emotion
            const sentiment = m.sentiment_label || (score > 0.58 ? 'positive' : score < 0.42 ? 'negative' : 'neutral');
            const emotionLabel = _getEmotionLabel(sentiment, score);
            const cssClass = _labelToClass(emotionLabel);
            sentimentBadge = `<span class="msg-sentiment-pill msg-sentiment-pill--${cssClass}">` +
                `<span class="msg-sentiment-dot"></span>${emotionLabel} | ${pct}%</span>`;
        }

        const time = m.created_at ? tzTime(m.created_at) : '';

        return `<div class="msg msg--${type}">
            <div class="msg-avatar">${label}</div>
            <div>
                <div class="msg-bubble">${formatMessageContent(m.content)}</div>
                ${sentimentBadge}
                <div class="msg-time">${time}</div>
            </div>
        </div>`;
    }).join('');

    container.scrollTop = container.scrollHeight;
}

/**
 * Map sentiment + score ' 16-tier emotion label
 * Mirrors backend get_sentiment_label() in sentiment.py
 */
function _getEmotionLabel(sentiment, score) {
    if (sentiment === 'positive' || score >= 0.58) {
        if (score > 0.95) return 'Ecstatic';
        if (score > 0.88) return 'Delighted';
        if (score > 0.82) return 'Very Happy';
        if (score > 0.75) return 'Happy';
        if (score > 0.68) return 'Pleased';
        if (score > 0.62) return 'Content';
        return 'Satisfied';
    }
    if (sentiment === 'negative' || score <= 0.42) {
        if (score < 0.05) return 'Enraged';
        if (score < 0.10) return 'Furious';
        if (score < 0.15) return 'Very Frustrated';
        if (score < 0.22) return 'Frustrated';
        if (score < 0.28) return 'Upset';
        if (score < 0.34) return 'Disappointed';
        if (score < 0.40) return 'Slightly Unhappy';
        return 'Concerned';
    }
    if (score > 0.55) return 'Leaning Positive';
    if (score < 0.45) return 'Leaning Negative';
    return 'Neutral';
}

/** Convert label like "Very Frustrated" ' CSS class "very-frustrated" */
function _labelToClass(label) {
    return label.toLowerCase().replace(/\s+/g, '-');
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

/* ***********************************************************
   TAB 3: ANALYTICS  (Complete Redesign v2)
   Single API call → renders 8 KPIs + 4 chart sections
   *********************************************************** */
let _anxPeriod = 'today';
let _anxInitialized = false;

async function loadAnalytics() {
    // Setup period pills once
    if (!_anxInitialized) {
        _anxInitialized = true;
        document.querySelectorAll('.anx-period-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.anx-period-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                _anxPeriod = pill.dataset.period;
                loadedTabs['analytics'] = false;
                loadAnalytics();
            });
        });
    }

    try {
        const data = await API.getComprehensiveAnalytics(_anxPeriod);
        const k = data.kpis || {};

        // ── 8 KPI Cards ──
        _anxSetKpi('anxKpiConversations', (k.total_conversations ?? 0).toLocaleString());
        _anxSetKpi('anxKpiMessages', (k.total_messages ?? 0).toLocaleString());
        _anxSetKpi('anxKpiSentiment', (k.avg_sentiment != null && (k.total_conversations ?? 0) > 0) ? (k.avg_sentiment * 100).toFixed(0) + '%' : 'N/A');
        _anxSetKpi('anxKpiEscalation', k.escalation_rate != null ? k.escalation_rate.toFixed(1) + '%' : '0%');
        _anxSetKpi('anxKpiOrders', (k.total_orders ?? 0).toLocaleString());
        _anxSetKpi('anxKpiRevenue', '$' + (k.total_revenue ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}));
        _anxSetKpi('anxKpiProducts', (k.products ?? 0).toLocaleString());
        _anxSetKpi('anxKpiKbDocs', (k.kb_documents ?? 0).toLocaleString());

        // ── Period label ──
        const label = document.getElementById('anxPeriodLabel');
        if (label) label.textContent = `Updated just now · ${k.avg_response_time || '< 2s'} avg response`;

        // ── Sentiment Trend (smooth) ──
        _anxRenderSentimentChart(data.sentiment_trends || []);

        // ── Rich Sentiment Distribution ──
        _anxRenderRichSentiment(data.rich_sentiments || [], k.total_conversations || 0);

        // ── Orders Overview ──
        _anxRenderOrders(data.order_sources || {}, data.order_pipeline || {}, k.total_orders || 0);

        // ── Recent Orders (in Orders Overview card) ──
        try {
            const ordersData = await API.getOrders(1, 3);
            const orders = ordersData.orders || ordersData || [];
            _renderRecentOrdersInto('anxRecentOrders', orders, 3);
        } catch { _renderRecentOrdersInto('anxRecentOrders', [], 3); }

        // ── Language Detection ──
        _anxRenderLanguages(data.languages || [], k.total_conversations || 0);

    } catch (err) {
        console.error('Analytics load error:', err);
    }
}

function _anxSetKpi(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

/* ── Smooth SVG Line Chart (Cubic Bezier) ── */
function _anxRenderSentimentChart(trends) {
    const wrap = document.getElementById('anxSentimentChart');
    const xLabels = document.getElementById('anxChartXLabels');
    if (!wrap) return;

    if (!trends.length) {
        wrap.innerHTML = '<div class="anx-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg><span>No trend data yet</span></div>';
        if (xLabels) xLabels.innerHTML = '';
        return;
    }

    const W = 560, H = 190, PX = 30, PY = 20;
    const chartW = W - 2 * PX, chartH = H - 2 * PY;
    const n = trends.length;

    const maxVal = Math.max(...trends.map(t => Math.max(t.positive, t.neutral, t.negative)), 1);

    function getPoints(key) {
        return trends.map((t, i) => {
            const x = PX + (i / Math.max(n - 1, 1)) * chartW;
            const y = PY + chartH - (t[key] / maxVal) * chartH;
            return { x, y };
        });
    }

    // Smooth cubic bezier path
    function pointsToSmoothPath(pts) {
        if (pts.length < 2) return pts.length ? `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}` : '';
        let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
        for (let i = 1; i < pts.length; i++) {
            const prev = pts[i - 1];
            const curr = pts[i];
            const tension = 0.3;
            const dx = (curr.x - (pts[i - 2] ? pts[i - 2].x : prev.x)) * tension;
            const cp1x = prev.x + dx;
            const cp1y = prev.y;
            const dx2 = (curr.x - (pts[i + 1] ? pts[i + 1].x : curr.x)) * tension;
            const cp2x = curr.x + dx2;
            const cp2y = curr.y;
            d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${curr.x.toFixed(1)},${curr.y.toFixed(1)}`;
        }
        return d;
    }

    function pointsToSmoothArea(pts) {
        if (!pts.length) return '';
        const base = PY + chartH;
        return pointsToSmoothPath(pts) + ` L${pts[pts.length-1].x.toFixed(1)},${base} L${pts[0].x.toFixed(1)},${base} Z`;
    }

    const posP = getPoints('positive');
    const neuP = getPoints('neutral');
    const negP = getPoints('negative');

    // Grid
    let gridLines = '';
    for (let i = 0; i <= 4; i++) {
        const y = PY + (i / 4) * chartH;
        gridLines += `<line x1="${PX}" y1="${y}" x2="${W - PX}" y2="${y}" class="anx-chart-grid-line"/>`;
    }

    let svg = `<svg class="anx-chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
    svg += `<defs>
        <linearGradient id="anxGradPos" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--positive)" stop-opacity="0.25"/><stop offset="100%" stop-color="var(--positive)" stop-opacity="0"/></linearGradient>
        <linearGradient id="anxGradNeu" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--neutral)" stop-opacity="0.2"/><stop offset="100%" stop-color="var(--neutral)" stop-opacity="0"/></linearGradient>
        <linearGradient id="anxGradNeg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--negative)" stop-opacity="0.2"/><stop offset="100%" stop-color="var(--negative)" stop-opacity="0"/></linearGradient>
    </defs>`;
    svg += gridLines;

    // Gradient areas
    svg += `<path d="${pointsToSmoothArea(posP)}" fill="url(#anxGradPos)"/>`;
    svg += `<path d="${pointsToSmoothArea(neuP)}" fill="url(#anxGradNeu)"/>`;
    svg += `<path d="${pointsToSmoothArea(negP)}" fill="url(#anxGradNeg)"/>`;

    // Smooth lines
    svg += `<path d="${pointsToSmoothPath(posP)}" stroke="var(--positive)" class="anx-chart-line"/>`;
    svg += `<path d="${pointsToSmoothPath(neuP)}" stroke="var(--neutral)" class="anx-chart-line"/>`;
    svg += `<path d="${pointsToSmoothPath(negP)}" stroke="var(--negative)" class="anx-chart-line"/>`;

    // Dots
    posP.forEach(p => { svg += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" stroke="var(--positive)" class="anx-chart-dot"/>`; });
    neuP.forEach(p => { svg += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" stroke="var(--neutral)" class="anx-chart-dot"/>`; });
    negP.forEach(p => { svg += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" stroke="var(--negative)" class="anx-chart-dot"/>`; });

    svg += '</svg>';
    wrap.innerHTML = svg;

    if (xLabels) {
        xLabels.innerHTML = trends.map(t => `<span>${t.label || t.day || ''}</span>`).join('');
    }
}

/* ── Rich Sentiment Distribution (5 categories) ── */
function _anxRenderRichSentiment(sentiments, totalConvs) {
    const el = document.getElementById('anxRichSentiment');
    if (!el) return;

    if (!sentiments.length || !totalConvs) {
        // Show all 5 categories in dimmed state with two-line layout
        const placeholders = [
            { icon: '😊', label: 'Happy',      color: '#10b981' },
            { icon: '🙂', label: 'Satisfied',  color: '#22d3ee' },
            { icon: '😐', label: 'Neutral',    color: '#8b5cf6' },
            { icon: '😤', label: 'Frustrated', color: '#f59e0b' },
            { icon: '😡', label: 'Angry',      color: '#ef4444' },
        ];
        el.innerHTML = placeholders.map(s =>
            `<div class="sd-row" style="opacity:.35">
                <div class="sd-row-top">
                    <span class="sd-icon">${s.icon}</span>
                    <span class="sd-label">${s.label}</span>
                    <div class="anx-hbar-track"><div class="anx-hbar-fill" style="width:3%;background:${s.color}"></div></div>
                </div>
                <div class="sd-row-sub">0 conversations · 0%</div>
            </div>`
        ).join('');
        return;
    }

    const maxPct = Math.max(...sentiments.map(s => s.percent || 0), 1);

    el.innerHTML = sentiments.map(s => {
        const barW = Math.max((s.percent / maxPct) * 100, 3);
        const convWord = s.count === 1 ? 'conversation' : 'conversations';
        return `<div class="sd-row">
            <div class="sd-row-top">
                <span class="sd-icon">${s.icon || '●'}</span>
                <span class="sd-label">${esc(s.label)}</span>
                <div class="anx-hbar-track"><div class="anx-hbar-fill" style="width:${barW}%;background:${s.color}"></div></div>
            </div>
            <div class="sd-row-sub">${s.count} ${convWord} · ${s.percent}%</div>
        </div>`;
    }).join('');
}

/* ── Orders Overview (Source + Pipeline) ── */
function _anxRenderOrders(sources, pipeline, totalOrders) {
    const el = document.getElementById('anxOrdersOverview');
    const totalLabel = document.getElementById('anxOrderTotal');
    if (!el) return;
    if (totalLabel) totalLabel.textContent = totalOrders ? `${totalOrders} total` : '';

    if (!totalOrders) {
        const periodLabels = { today: 'today', '7d': 'in last 7 days', '30d': 'in last 30 days', all: 'yet' };
        const msg = 'No orders ' + (periodLabels[_anxPeriod] || 'yet');
        el.innerHTML = `<div class="anx-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg><span>${msg}</span></div>`;
        return;
    }

    // SVG icons for each source
    const sourceIcons = {
        csv: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        api: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--secondary-400)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
        simulator: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
        widget: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--positive)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><path d="M9 10l2 2 4-4"/></svg>',
    };
    const sourceLabels = {
        csv: 'CSV Import',
        api: 'API Sync',
        simulator: 'Simulator',
        widget: 'Confirmed through Widget',
    };

    // Source breakdown
    let html = '<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">';
    const entries = Object.entries(sources);
    entries.forEach(([src, info]) => {
        const icon = sourceIcons[src] || '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M12 12h.01"/></svg>';
        const label = sourceLabels[src] || (src.charAt(0).toUpperCase() + src.slice(1));
        html += `<div style="flex:1;min-width:130px;background:var(--bg-tertiary);border-radius:var(--radius-md);padding:12px 14px;border:1px solid var(--border-subtle)">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                ${icon}
                <span style="font-size:.75rem;color:var(--text-muted);font-weight:500">${esc(label)}</span>
            </div>
            <div style="font-size:1.25rem;font-weight:700;color:var(--text-primary)">${info.count}</div>
            <div style="font-size:.6875rem;color:var(--text-muted)">$${info.revenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>`;
    });
    html += '</div>';

    el.innerHTML = html;
}

/* ── Language Detection with Sentiment (all 6 langs, dimmed if undetected) ── */
function _anxRenderLanguages(languages, totalConvs) {
    const el = document.getElementById('anxLanguages');
    const countLabel = document.getElementById('anxLangCount');
    if (!el) return;

    const activeCount = languages.filter(l => l.active).length;
    if (countLabel) countLabel.textContent = activeCount ? `${activeCount} detected` : '';

    if (!languages.length) {
        el.innerHTML = '<div class="anx-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg><span>No language data yet</span></div>';
        return;
    }

    // Sentiment to color + emoji mapping
    function sentimentMeta(score) {
        if (score >= 0.75) return { color: '#10b981', icon: '😊', label: 'Happy' };
        if (score >= 0.55) return { color: '#22d3ee', icon: '🙂', label: 'Satisfied' };
        if (score >= 0.40) return { color: '#8b5cf6', icon: '😐', label: 'Neutral' };
        if (score >= 0.25) return { color: '#f59e0b', icon: '😤', label: 'Frustrated' };
        return { color: '#ef4444', icon: '😡', label: 'Angry' };
    }

    const maxCount = Math.max(...languages.filter(l => l.active).map(l => l.count || 0), 1);

    el.innerHTML = languages.map(l => {
        const isActive = l.active;
        const opacity = isActive ? '1' : '0.35';
        const sm = sentimentMeta(l.avg_sentiment || 0.5);
        const barW = isActive ? Math.max((l.count / maxCount) * 100, 4) : 3;
        const barColor = isActive ? sm.color : 'var(--text-muted)';
        const countText = isActive ? `${l.count} <span style="color:var(--text-muted);font-weight:400">(${l.percent}%)</span>` : '<span style="color:var(--text-muted)">—</span>';

        let html = `<div style="opacity:${opacity};margin-bottom:${isActive ? '2px' : '8px'}">
            <div class="anx-hbar-item" style="margin-bottom:2px">
                <span style="font-size:1.15rem;width:26px;text-align:center;flex-shrink:0">${l.flag || '🌐'}</span>
                <span class="anx-hbar-label" style="width:80px;font-weight:500">${esc(l.name || 'Unknown')}</span>
                <div class="anx-hbar-track"><div class="anx-hbar-fill" style="width:${barW}%;background:${barColor}"></div></div>
                <span class="anx-hbar-value" style="min-width:90px;display:flex;align-items:center;gap:4px">
                    ${countText}
                </span>
            </div>`;

        // Show sentiment row only for active languages
        if (isActive) {
            html += `<div style="display:flex;align-items:center;gap:5px;margin-left:26px;margin-bottom:6px">
                <span style="font-size:.85rem">${sm.icon}</span>
                <span style="font-size:.6875rem;color:${sm.color};font-weight:500">${sm.label}</span>
                <span style="font-size:.6rem;color:var(--text-muted)">· avg ${((l.avg_sentiment || 0.5) * 100).toFixed(0)}%</span>
            </div>`;
        }

        html += '</div>';
        return html;
    }).join('');
}







/* ***********************************************************
   TAB 5: WIDGET
   *********************************************************** */
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

    // Sync color picker <-> text
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
        const widgetTypeEl = document.getElementById('widgetType');
        const data = {
            bot_name: document.getElementById('widgetBotName').value,
            welcome_message: document.getElementById('widgetWelcome').value,
            primary_color: document.getElementById('widgetColor').value,
            position: document.getElementById('widgetPosition').value,
            widget_type: widgetTypeEl ? widgetTypeEl.value : 'full',
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

/* ***********************************************************
   TAB 6: SETTINGS — Single-page scrollable layout (V4.3)
   Five premium glassmorphism cards:
   1. Account Overview  2. Profile  3. Company
   4. Widget API Key    5. AI Behavior
   *********************************************************** */
async function loadSettings() {
    const c = document.getElementById('settingsContainer');
    if (!c) return;

    /* ---- Fetch data ---- */
    let profile = {}, tenant = {}, prefs = {}, apiKey = '';
    try {
        const resp = await API.getSettings();
        profile = resp.profile || {};
        tenant = resp.tenant || {};
        prefs = resp.settings || {};
        apiKey = (resp.api_key && resp.api_key.key) || '••••••••••••';
    } catch (err) {
        console.error('Settings load error:', err);
        c.innerHTML = '<div class="stg-error"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg><p>Failed to load settings</p></div>';
        return;
    }

    const userName = profile.name || profile.full_name || 'User';
    const userEmail = profile.email || '';
    const initials = userName.trim().split(/\s+/).length >= 2
        ? (userName.trim().split(/\s+/)[0][0] + userName.trim().split(/\s+/).slice(-1)[0][0]).toUpperCase()
        : userName.slice(0, 2).toUpperCase();
    // Set tenant timezone globally for all date formatting
    if (tenant.timezone) TENANT_TZ = tenant.timezone;
    const joinedDate = tzDate(tenant.created_at);
    const sensitivityVal = prefs.auto_escalation_threshold
        ? (prefs.auto_escalation_threshold / 100).toFixed(2)
        : '0.70';

    /* ---- Render all cards (Bento Grid layout) ---- */
    c.innerHTML = `
    <!-- ════════ 1. ACCOUNT OVERVIEW — full width ════════ -->
    <div class="stg-card stg-card--accent">
        <div class="stg-account-row">
            <div class="stg-avatar">${esc(initials)}</div>
            <div class="stg-account-info">
                <h3 class="stg-account-name">${esc(userName)}</h3>
                <p class="stg-account-email">${esc(userEmail)}</p>
            </div>
            <div class="stg-account-meta">
                <div class="stg-meta-chip">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    Joined ${esc(joinedDate)}
                </div>
                <div class="stg-meta-chip stg-meta-chip--green">
                    <span class="stg-status-dot"></span>
                    Active
                </div>
            </div>
        </div>
    </div>

    <!-- ════════ ROW 1: PROFILE + COMPANY ════════ -->
    <div class="stg-bento-row">
        <!-- 2. PROFILE -->
        <div class="stg-card">
            <div class="stg-card-header">
                <div class="stg-card-icon stg-card-icon--blue">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
                <div>
                    <h3 class="stg-card-title">Profile</h3>
                    <p class="stg-card-desc">Personal information &amp; password</p>
                </div>
            </div>
            <div class="stg-form-grid stg-form-grid--single">
                <div class="stg-field">
                    <label class="stg-label">Full Name</label>
                    <input type="text" class="stg-input" id="settingsName" value="${esc(userName)}">
                </div>
                <div class="stg-field">
                    <label class="stg-label">Email Address</label>
                    <input type="email" class="stg-input stg-input--disabled" id="settingsEmail" value="${esc(userEmail)}" disabled>
                </div>
                <div class="stg-field">
                    <label class="stg-label">New Password</label>
                    <input type="password" class="stg-input" id="settingsPassword" placeholder="Leave blank to keep">
                </div>
                <div class="stg-field">
                    <label class="stg-label">Confirm Password</label>
                    <input type="password" class="stg-input" id="settingsPasswordConfirm" placeholder="Repeat password">
                </div>
            </div>
            <div class="stg-actions">
                <button class="btn btn-primary btn--glow" id="saveProfileBtn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                    Save Profile
                </button>
            </div>
        </div>

        <!-- 3. COMPANY -->
        <div class="stg-card">
            <div class="stg-card-header">
                <div class="stg-card-icon stg-card-icon--purple">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                </div>
                <div>
                    <h3 class="stg-card-title">Company</h3>
                    <p class="stg-card-desc">Business details for your AI &amp; widget</p>
                </div>
            </div>
            <div class="stg-form-grid stg-form-grid--single">
                <div class="stg-field">
                    <label class="stg-label">Company Name</label>
                    <input type="text" class="stg-input" id="settingsCompanyName" value="${esc(tenant.business_name || profile.company_name || '')}">
                </div>
                <div class="stg-field">
                    <label class="stg-label">Industry</label>
                    <input type="text" class="stg-input" id="settingsIndustry" value="${esc(tenant.business_type || '')}" placeholder="e.g. Fashion, Electronics">
                </div>
                <div class="stg-field">
                    <label class="stg-label">Support Email</label>
                    <input type="email" class="stg-input" id="settingsSupportEmail" value="${esc(tenant.support_email || '')}" placeholder="support@company.com">
                </div>
                <div class="stg-field">
                    <label class="stg-label">Website URL</label>
                    <input type="url" class="stg-input" id="settingsWebsite" value="${esc(tenant.store_url || '')}" placeholder="https://your-store.com">
                </div>
            </div>
            <div class="stg-actions">
                <button class="btn btn-primary btn--glow" id="saveCompanyBtn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                    Save Company
                </button>
            </div>
        </div>
    </div>

    <!-- ════════ ROW 2: API KEY + AI BEHAVIOR ════════ -->
    <div class="stg-bento-row">
        <!-- 4. WIDGET API KEY -->
        <div class="stg-card">
            <div class="stg-card-header">
                <div class="stg-card-icon stg-card-icon--amber">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                </div>
                <div>
                    <h3 class="stg-card-title">Widget API Key</h3>
                    <p class="stg-card-desc">Embed key — regenerating invalidates old embeds</p>
                </div>
            </div>
            <div class="stg-api-key-box">
                <code class="stg-api-key-value" id="apiKeyValue">${esc(apiKey)}</code>
                <button class="stg-api-btn" id="copyApiKeyBtn" title="Copy to clipboard">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                </button>
            </div>
            <div class="stg-actions">
                <button class="btn btn-secondary" id="regenApiKeyBtn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                    Regenerate Key
                </button>
            </div>
        </div>

        <!-- 5. AI BEHAVIOR -->
        <div class="stg-card">
            <div class="stg-card-header">
                <div class="stg-card-icon stg-card-icon--green">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/></svg>
                </div>
                <div>
                    <h3 class="stg-card-title">AI Behavior</h3>
                    <p class="stg-card-desc">Control escalation sensitivity to human agents</p>
                </div>
            </div>
            <div class="stg-slider-group">
                <label class="stg-label">Auto-Escalation Sensitivity</label>
                <div class="stg-slider-row">
                    <span class="stg-slider-label">Low</span>
                    <input type="range" min="0" max="1" step="0.05" value="${sensitivityVal}" id="prefSensitivity" class="stg-slider">
                    <span class="stg-slider-label">High</span>
                    <span class="stg-slider-value" id="sensitivityValue">${sensitivityVal}</span>
                </div>
                <p class="stg-slider-hint">
                    <strong>Low</strong> = AI handles more &nbsp;·&nbsp; <strong>High</strong> = faster escalation to humans
                </p>
            </div>
            <div class="stg-actions">
                <button class="btn btn-primary btn--glow" id="savePrefsBtn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                    Save Preferences
                </button>
            </div>
        </div>
    </div>

    <!-- ════════ V5 NEW: REAL-TIME SYNC CONFIG ════════ -->
    <div class="stg-card" style="grid-column:1/-1">
        <div class="stg-card-header">
            <div class="stg-card-icon stg-card-icon--green">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
            </div>
            <div>
                <h3 class="stg-card-title">Real-Time CSV Sync</h3>
                <p class="stg-card-desc">Auto-sync Orders &amp; Products from external store CSV feeds</p>
            </div>
        </div>
        <div id="syncConfigsList" style="margin-bottom:16px">
            <div style="text-align:center;color:var(--text-muted);padding:16px;font-size:.8rem">Loading sync configs…</div>
        </div>
        <div style="border-top:1px solid var(--border);padding-top:16px">
            <h4 style="font-size:.85rem;font-weight:600;margin-bottom:12px;color:var(--text-primary)">Add Sync Config</h4>
            <div class="stg-form-grid stg-form-grid--single">
                <div class="stg-field" style="display:flex;gap:8px">
                    <div style="flex:1">
                        <label class="stg-label">Type</label>
                        <select class="stg-input" id="syncType">
                            <option value="orders">Orders</option>
                            <option value="products">Products</option>
                        </select>
                    </div>
                    <div style="flex:1">
                        <label class="stg-label">Interval</label>
                        <select class="stg-input" id="syncInterval">
                            <option value="15">Every 15 min</option>
                            <option value="30">Every 30 min</option>
                            <option value="60" selected>Every hour</option>
                            <option value="360">Every 6 hours</option>
                            <option value="1440">Daily</option>
                        </select>
                    </div>
                </div>
                <div class="stg-field">
                    <label class="stg-label">CSV URL</label>
                    <input type="url" class="stg-input" id="syncCsvUrl" placeholder="https://your-store.com/export/orders.csv">
                </div>
                <div class="stg-field" style="display:flex;gap:8px">
                    <div style="flex:1">
                        <label class="stg-label">Auth Header Name <small style="opacity:.5">(optional)</small></label>
                        <input type="text" class="stg-input" id="syncAuthName" placeholder="Authorization">
                    </div>
                    <div style="flex:1">
                        <label class="stg-label">Auth Header Value <small style="opacity:.5">(optional)</small></label>
                        <input type="text" class="stg-input" id="syncAuthValue" placeholder="Bearer sk-xxx">
                    </div>
                </div>
            </div>
            <div class="stg-actions">
                <button class="btn btn-primary btn--glow" id="addSyncConfigBtn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Add Sync
                </button>
            </div>
        </div>
    </div>

    <!-- ════════ 6. DANGER ZONE — full width ════════ -->
    <div class="stg-card stg-card--danger">
        <div class="stg-card-header">
            <div class="stg-card-icon stg-card-icon--red">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div>
                <h3 class="stg-card-title" style="color:#f87171;">Danger Zone</h3>
                <p class="stg-card-desc">Irreversible actions — proceed with caution</p>
            </div>
        </div>
        <div class="stg-danger-actions">
            <div class="stg-danger-row">
                <div>
                    <strong class="stg-danger-label">Clear All Conversations</strong>
                    <p class="stg-danger-hint">Delete all chat history and conversation data for this account</p>
                </div>
                <button class="btn stg-btn-danger" id="clearConversationsBtn">Clear Conversations</button>
            </div>
        </div>
    </div>
    `;

    /* ──────────── Event Handlers ──────────── */

    // Save profile
    document.getElementById('saveProfileBtn').onclick = async () => {
        const data = { full_name: document.getElementById('settingsName').value };
        const pw = document.getElementById('settingsPassword').value;
        if (pw) {
            if (pw !== document.getElementById('settingsPasswordConfirm').value) {
                showToast('Passwords do not match', 'error'); return;
            }
            data.password = pw;
        }
        try {
            const result = await API.updateProfile(data);
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (result.profile) {
                Object.assign(user, result.profile);
            } else if (data.full_name) {
                user.full_name = data.full_name;
                user.name = data.full_name;
                const parts = data.full_name.trim().split(/\s+/);
                user.initials = parts.length >= 2
                    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
                    : data.full_name.slice(0, 2).toUpperCase();
            }
            localStorage.setItem('user', JSON.stringify(user));
            loadUserInfo();
            showToast('Profile updated!', 'success');
            // Clear password fields
            document.getElementById('settingsPassword').value = '';
            document.getElementById('settingsPasswordConfirm').value = '';
        } catch { showToast('Update failed', 'error'); }
    };

    // Save company
    document.getElementById('saveCompanyBtn').onclick = async () => {
        const data = {
            business_name: document.getElementById('settingsCompanyName').value,
            business_type: document.getElementById('settingsIndustry').value,
            support_email: document.getElementById('settingsSupportEmail').value,
            store_url: document.getElementById('settingsWebsite').value,
        };
        try { await API.updateTenantSettings(data); showToast('Company settings updated!', 'success'); }
        catch { showToast('Update failed', 'error'); }
    };

    // Copy API key
    document.getElementById('copyApiKeyBtn').onclick = () => {
        const key = document.getElementById('apiKeyValue').textContent;
        navigator.clipboard.writeText(key).then(() => showToast('API key copied!', 'success'));
    };

    // Regenerate API key
    document.getElementById('regenApiKeyBtn').onclick = async () => {
        if (!confirm('Regenerate your API key? Your current embed code will stop working.')) return;
        try {
            const result = await API.regenerateApiKey();
            document.getElementById('apiKeyValue').textContent = result.new_key || result.api_key || '--';
            showToast('API key regenerated', 'success');
        } catch { showToast('Regeneration failed', 'error'); }
    };

    // Sensitivity slider
    document.getElementById('prefSensitivity').addEventListener('input', (e) => {
        document.getElementById('sensitivityValue').textContent = parseFloat(e.target.value).toFixed(2);
    });

    // Save preferences
    document.getElementById('savePrefsBtn').onclick = async () => {
        const data = {
            auto_escalation_threshold: Math.round(parseFloat(document.getElementById('prefSensitivity').value) * 100),
        };
        try { await API.updatePreferences(data); showToast('Preferences saved!', 'success'); }
        catch { showToast('Update failed', 'error'); }
    };

    // Clear conversations (Danger Zone)
    document.getElementById('clearConversationsBtn').onclick = async () => {
        const confirmText = prompt('Type "DELETE" to confirm clearing all conversations:');
        if (confirmText !== 'DELETE') {
            if (confirmText !== null) showToast('Cancelled — text did not match', 'info');
            return;
        }
        try {
            await API.request('/conversations/clear', { method: 'DELETE' });
            showToast('All conversations cleared', 'success');
        } catch { showToast('Clear failed — endpoint may not exist yet', 'error'); }
    };

    // ★ V5: Sync Config Handlers
    loadSyncConfigs();

    document.getElementById('addSyncConfigBtn').onclick = async () => {
        const csvUrl = document.getElementById('syncCsvUrl').value.trim();
        if (!csvUrl) { showToast('CSV URL is required', 'warning'); return; }
        const data = {
            sync_type: document.getElementById('syncType').value,
            csv_url: csvUrl,
            sync_interval_minutes: parseInt(document.getElementById('syncInterval').value) || 60,
            auth_header_name: document.getElementById('syncAuthName').value.trim() || null,
            auth_header_value: document.getElementById('syncAuthValue').value.trim() || null,
            is_active: true,
        };
        try {
            await API.createSyncConfig(data);
            showToast('Sync config added!', 'success');
            document.getElementById('syncCsvUrl').value = '';
            document.getElementById('syncAuthName').value = '';
            document.getElementById('syncAuthValue').value = '';
            loadSyncConfigs();
        } catch (e) {
            showToast('Failed to add: ' + (e.message || e), 'error');
        }
    };
}

async function loadSyncConfigs() {
    const container = document.getElementById('syncConfigsList');
    if (!container) return;
    try {
        const result = await API.getSyncConfigs();
        const configs = result.configs || result || [];
        if (!configs.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:16px;font-size:.8rem">No sync configs yet — add one below</div>';
            return;
        }
        const statusColors = { success: '#10b981', failed: '#ef4444', running: '#f59e0b', never: '#6b7280' };
        container.innerHTML = configs.map(c => {
            const st = c.last_sync_status || 'never';
            const stColor = statusColors[st] || '#6b7280';
            return `
            <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-radius:12px;background:var(--bg-tertiary);margin-bottom:8px;border:1px solid var(--border)">
                <div style="flex:0 0 auto;width:10px;height:10px;border-radius:50%;background:${stColor}"></div>
                <div style="flex:1;min-width:0">
                    <div style="font-weight:600;font-size:.8rem;color:var(--text-primary)">${esc(c.sync_type?.toUpperCase())} — ${esc(c.csv_url?.slice(0, 60))}${c.csv_url?.length > 60 ? '…' : ''}</div>
                    <div style="font-size:.7rem;color:var(--text-muted)">
                        Every ${c.sync_interval_minutes}m · Status: <span style="color:${stColor};font-weight:600">${st.toUpperCase()}</span>
                        ${c.last_synced_at ? ' · Last: ' + new Date(c.last_synced_at).toLocaleString() : ''}
                        ${c.last_sync_message ? ' · ' + esc(c.last_sync_message.slice(0, 80)) : ''}
                    </div>
                </div>
                <button class="btn btn-sm btn-secondary" onclick="triggerSyncConfig(${c.id})" title="Sync Now" style="padding:4px 10px">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                </button>
                <button class="btn btn-sm btn-ghost" onclick="deleteSyncConfig(${c.id})" title="Delete" style="padding:4px 8px;color:var(--negative)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:16px;font-size:.8rem">Could not load sync configs</div>';
    }
}

async function triggerSyncConfig(id) {
    try {
        showToast('Triggering sync…', 'info');
        const result = await API.triggerSync(id);
        showToast(result.message || 'Sync triggered!', 'success');
        setTimeout(loadSyncConfigs, 3000); // refresh after a few seconds
    } catch (e) {
        showToast('Sync trigger failed: ' + (e.message || e), 'error');
    }
}

async function deleteSyncConfig(id) {
    if (!confirm('Delete this sync config?')) return;
    try {
        await API.deleteSyncConfig(id);
        showToast('Sync config deleted', 'success');
        loadSyncConfigs();
    } catch (e) {
        showToast('Delete failed', 'error');
    }
}

/* ***********************************************************
   MOBILE MENU
   *********************************************************** */
function setupMobileMenu() {
    const toggle = document.getElementById('mobileToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!toggle || !sidebar) return; // Guard: elements must exist

    toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        if (overlay) {
            overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
        }
    });

    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.style.display = 'none';
        });
    }

    // Auto-close sidebar on mobile when a nav item is clicked
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
                if (overlay) overlay.style.display = 'none';
            }
        });
    });
}

/* ***********************************************************
   LOGOUT
   *********************************************************** */
function setupLogout() {
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/pages/login.html';
    });
}

/* ***********************************************************
   UTILITIES
   *********************************************************** */
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

/* ***********************************************************
   UPLOAD ZONES (drag-drop)
   *********************************************************** */
function setupUploadZones() {
    // Order CSV upload zone
    const orderZone = document.getElementById('orderUploadZone');
    const orderInput = document.getElementById('orderCsvInput');
    if (orderZone && orderInput) {
        orderZone.addEventListener('click', () => orderInput.click());
        orderZone.addEventListener('dragover', (e) => { e.preventDefault(); orderZone.classList.add('dragover'); });
        orderZone.addEventListener('dragleave', () => orderZone.classList.remove('dragover'));
        orderZone.addEventListener('drop', (e) => {
            e.preventDefault(); orderZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) { orderInput.files = e.dataTransfer.files; uploadOrderCSV(); }
        });
        orderInput.addEventListener('change', () => { if (orderInput.files.length) uploadOrderCSV(); });
    }
    // Product CSV upload
    const prodInput = document.getElementById('productCsvInput');
    const prodBtn = document.getElementById('importProductCsvBtn');
    if (prodBtn && prodInput) {
        prodBtn.addEventListener('click', () => prodInput.click());
        prodInput.addEventListener('change', () => { if (prodInput.files.length) uploadProductCSV(); });
    }
}

/* ***********************************************************
   TAB: ORDERS (V4 NEW)
   *********************************************************** */
let orderPage = 1;
async function loadOrders(page = 1) {
    orderPage = page;
    try {
        // Load stats
        const stats = await API.getOrderStats();
        document.getElementById('orderTotal').textContent = stats.total || 0;
        document.getElementById('orderPending').textContent = stats.by_status?.pending || 0;
        document.getElementById('orderShipped').textContent = stats.by_status?.shipped || 0;
        document.getElementById('orderDelivered').textContent = stats.by_status?.delivered || 0;

        // Load table
        const search = document.getElementById('orderSearch')?.value || '';
        const status = document.getElementById('orderStatusFilter')?.value || '';
        const source = document.getElementById('orderSourceFilter')?.value || '';
        const data = await API.getOrders(page, 20, search, status, source);
        renderOrderTable(data.orders || []);
        renderPagination('orderPagination', data.page || 1, data.total_pages || data.pages || 1, (p) => loadOrders(p));
    } catch (e) {
        console.error('Orders error:', e);
        showToast('Failed to load orders', 'error');
    }

    // Setup search/filter listeners (once)
    if (!loadedTabs._ordersListeners) {
        loadedTabs._ordersListeners = true;
        document.getElementById('orderSearch')?.addEventListener('input', debounce(() => loadOrders(1), 400));
        document.getElementById('orderStatusFilter')?.addEventListener('change', () => loadOrders(1));
        document.getElementById('orderSourceFilter')?.addEventListener('change', () => loadOrders(1));
    }
}

function renderOrderTable(orders) {
    const tbody = document.getElementById('orderTableBody');
    if (!orders.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:32px">No orders found</td></tr>';
        return;
    }
    const sourceColors = { csv: '#3b82f6', widget: '#8b5cf6', api: '#f59e0b', sync: '#10b981', simulator: '#6b7280' };
    const sourceIcons = { csv: '📄', widget: '🛍️', api: '🔌', sync: '🔄', simulator: '🎮' };
    tbody.innerHTML = orders.map(o => {
        const src = (o.source || 'csv').toLowerCase();
        const srcColor = sourceColors[src] || '#6b7280';
        const srcIcon = sourceIcons[src] || '❓';
        return `
        <tr>
            <td><strong>${esc(o.order_id)}</strong></td>
            <td>${esc(o.customer_name || '--')}</td>
            <td>${esc(o.customer_email || '--')}</td>
            <td><span class="order-status order-status--${(o.status || 'pending').toLowerCase()}">${esc(o.status || 'pending')}</span></td>
            <td><span style="display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:20px;font-size:.7rem;font-weight:600;background:${srcColor}18;color:${srcColor};border:1px solid ${srcColor}30">${srcIcon} ${src.toUpperCase()}</span></td>
            <td>${o.total_amount ? `${o.currency || '$'}${Number(o.total_amount).toFixed(2)}` : '--'}</td>
            <td>${o.order_date ? tzShortDate(o.order_date) : '--'}</td>
            <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-secondary" onclick="viewOrder('${esc(o.order_id)}')" title="View Details"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button>
                <button class="btn btn-sm btn-ghost" onclick="deleteOrder(${o.id})" title="Delete"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
            </td>
        </tr>
    `}).join('');
}

async function uploadOrderCSV() {
    const input = document.getElementById('orderCsvInput');
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        showToast('Uploading CSV', 'info');
        const result = await API.uploadOrderCSV(formData);
        showToast(`${result.created || 0} orders imported, ${result.skipped || 0} skipped!`, 'success');
        input.value = '';
        loadedTabs.orders = false;
        loadOrders(1);
    } catch (e) {
        showToast('CSV upload failed: ' + (e.message || e), 'error');
    }
}


async function deleteOrder(id) {
    if (!confirm('Delete this order?')) return;
    try {
        await API.deleteOrder(id);
        showToast('Order deleted', 'success');
        loadOrders(orderPage);
    } catch (e) {
        showToast('Delete failed', 'error');
    }
}

/* ***********************************************************
   TAB: PRODUCTS (V4 NEW)
   *********************************************************** */
let productPage = 1;
let editingProductId = null;

async function loadProducts(page = 1) {
    productPage = page;
    try {
        const search = document.getElementById('productSearch')?.value || '';
        const category = document.getElementById('productCategoryFilter')?.value || '';
        const data = await API.getProducts(page, 20, search, category);
        renderProductGrid(data.products || []);
        renderPagination('productPagination', data.page || 1, data.total_pages || data.pages || 1, (p) => loadProducts(p));
    } catch (e) {
        console.error('Products error:', e);
        document.getElementById('productGrid').innerHTML = '<div class="empty-state"><p>Failed to load products</p></div>';
    }

    if (!loadedTabs._productsListeners) {
        loadedTabs._productsListeners = true;
        document.getElementById('productSearch')?.addEventListener('input', debounce(() => loadProducts(1), 400));
        document.getElementById('productCategoryFilter')?.addEventListener('change', () => loadProducts(1));
        document.getElementById('addProductBtn')?.addEventListener('click', showProductForm);
        document.getElementById('cancelProductBtn')?.addEventListener('click', hideProductForm);
        document.getElementById('saveProductBtn')?.addEventListener('click', saveProduct);
    }
}

function renderProductGrid(products) {
    const grid = document.getElementById('productGrid');
    if (!products.length) {
        grid.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:48px;height:48px;margin-bottom:12px;opacity:.3"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/></svg><p>No products yet - add your first product or import via CSV</p></div>';
        return;
    }
    grid.innerHTML = products.map(p => `
        <div class="product-card">
            <div class="product-card-img">
                ${p.images && p.images.length ? `<img src="${esc(p.images[0])}" alt="${esc(p.name)}" style="width:100%;height:100%;object-fit:cover">` : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>'}
            </div>
            <div class="product-card-body">
                <div class="product-card-name">${esc(p.name)}</div>
                <div class="product-card-price">${p.price ? `${p.currency || 'USD'} ${Number(p.price).toFixed(2)}` : 'No price'}</div>
                <div class="product-card-meta">
                    ${p.sku ? `<span class="product-card-sku">SKU: ${esc(p.sku)}</span>` : ''}
                    <span class="product-card-stock product-card-stock--${p.in_stock ? 'in' : 'out'}">${p.in_stock ? 'In Stock' : 'Out of Stock'}</span>
                </div>
                <div class="product-card-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editProduct(${p.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})">Delete</button>
                </div>
            </div>
        </div>
    `).join('');
}

function showProductForm(editData = null) {
    document.getElementById('productFormWrap').style.display = 'block';
    if (editData && typeof editData === 'object') {
        document.getElementById('productFormTitle').textContent = 'Edit Product';
        document.getElementById('prodName').value = editData.name || '';
        document.getElementById('prodSku').value = editData.sku || '';
        document.getElementById('prodPrice').value = editData.price || '';
        document.getElementById('prodCategory').value = editData.category || '';
        document.getElementById('prodStock').value = editData.stock_quantity || 0;
        document.getElementById('prodInStock').checked = editData.in_stock !== false;
        document.getElementById('prodDescription').value = editData.description || '';
        document.getElementById('prodImageUrl').value = editData.image_url || (editData.images && editData.images[0]) || '';
        document.getElementById('prodEditId').value = editData.id || '';
        editingProductId = editData.id;
    } else {
        document.getElementById('productFormTitle').textContent = 'Add Product';
        document.getElementById('prodName').value = '';
        document.getElementById('prodSku').value = '';
        document.getElementById('prodPrice').value = '';
        document.getElementById('prodCategory').value = '';
        document.getElementById('prodStock').value = '';
        document.getElementById('prodInStock').checked = true;
        document.getElementById('prodDescription').value = '';
        document.getElementById('prodImageUrl').value = '';
        document.getElementById('prodEditId').value = '';
        editingProductId = null;
    }
}

function hideProductForm() {
    document.getElementById('productFormWrap').style.display = 'none';
    editingProductId = null;
}

async function saveProduct() {
    const data = {
        name: document.getElementById('prodName').value.trim(),
        sku: document.getElementById('prodSku').value.trim() || null,
        price: parseFloat(document.getElementById('prodPrice').value) || null,
        category: document.getElementById('prodCategory').value.trim() || null,
        stock_quantity: parseInt(document.getElementById('prodStock').value) || 0,
        in_stock: document.getElementById('prodInStock').checked,
        description: document.getElementById('prodDescription').value.trim() || null,
        image_url: document.getElementById('prodImageUrl').value.trim() || null,
    };
    if (!data.name) { showToast('Product name is required', 'warning'); return; }
    try {
        if (editingProductId) {
            await API.updateProduct(editingProductId, data);
            showToast('Product updated!', 'success');
        } else {
            await API.createProduct(data);
            showToast('Product created!', 'success');
        }
        hideProductForm();
        loadedTabs.products = false;
        loadProducts(1);
    } catch (e) {
        showToast('Save failed: ' + (e.message || e), 'error');
    }
}

async function editProduct(id) {
    try {
        const result = await API.getProduct(id);
        showProductForm(result.product || result);
    } catch (e) {
        showToast('Failed to load product', 'error');
    }
}

async function deleteProduct(id) {
    if (!confirm('Delete this product?')) return;
    try {
        await API.deleteProduct(id);
        showToast('Product deleted', 'success');
        loadProducts(productPage);
    } catch (e) {
        showToast('Delete failed', 'error');
    }
}

async function uploadProductCSV() {
    const input = document.getElementById('productCsvInput');
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        showToast('Uploading product CSV', 'info');
        const result = await API.uploadProductCSV(formData);
        showToast(`${result.created || 0} products imported!`, 'success');
        input.value = '';
        loadedTabs.products = false;
        loadProducts(1);
    } catch (e) {
        showToast('Import failed: ' + (e.message || e), 'error');
    }
}

/* ***********************************************************
   PAGINATION RENDERER (generic)
   *********************************************************** */
function renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const el = document.getElementById(containerId);
    if (!el || totalPages <= 1) { if (el) el.innerHTML = ''; return; }
    let html = `<button class="pagination-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="void(0)">Prev</button>`;
    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="void(0)">${i}</button>`;
    }
    html += `<button class="pagination-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="void(0)">Next</button>`;
    el.innerHTML = html;
    el.querySelectorAll('.pagination-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const txt = btn.textContent.trim();
            if (txt === 'Prev' && currentPage > 1) onPageChange(currentPage - 1);
            else if (txt === 'Next' && currentPage < totalPages) onPageChange(currentPage + 1);
            else if (!isNaN(txt)) onPageChange(parseInt(txt));
        });
    });
}

/* """ Debounce helper """"""""""""""""""""""""""""""""""""""" */
function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

/* ***********************************************************
   ORDER DETAIL MODAL
   *********************************************************** */
async function viewOrder(orderId) {
    const overlay = document.getElementById('orderDetailOverlay');
    const content = document.getElementById('orderDetailContent');
    if (!overlay || !content) return;

    // Show modal with loading state
    overlay.classList.add('active');
    content.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading order details</p></div>';

    try {
        const result = await API.getOrder(orderId);
        const o = result.order || result;

        // Format items list
        let itemsHtml = '<span class="order-detail-empty">No items</span>';
        const items = Array.isArray(o.items) ? o.items : [];
        if (items.length) {
            itemsHtml = '<div class="order-detail-items">' + items.map(item =>
                `<div class="order-detail-item-row">
                    <span class="order-detail-item-name">${esc(item.name || item.product || 'Item')}</span>
                    <span class="order-detail-item-qty">--${item.qty || item.quantity || 1}</span>
                    ${item.price ? `<span class="order-detail-item-price">${o.currency || 'USD'} ${Number(item.price).toFixed(2)}</span>` : ''}
                </div>`
            ).join('') + '</div>';
        }

        // Build detail rows
        const rows = [
            { label: 'Order ID', value: o.order_id, icon: '#' },
            { label: 'Status', value: `<span class="order-status order-status--${(o.status || 'pending').toLowerCase()}">${esc(o.status || 'pending')}</span>`, raw: true, icon: '*' },
            { label: 'Customer Name', value: o.customer_name, icon: '@' },
            { label: 'Customer Email', value: o.customer_email, icon: '@' },
            { label: 'Total Amount', value: o.total_amount ? `${o.currency || 'USD'} ${Number(o.total_amount).toFixed(2)}` : null, icon: '$' },
            { label: 'Currency', value: o.currency, icon: '$' },
            { label: 'Order Date', value: o.order_date ? tzDateTime(o.order_date) : null, icon: '>' },
            { label: 'Estimated Delivery', value: o.estimated_delivery ? tzDateTime(o.estimated_delivery) : null, icon: '>' },
            { label: 'Tracking Number', value: o.tracking_number, icon: '#' },
            { label: 'Carrier', value: o.carrier, icon: '>' },
            { label: 'Shipping Address', value: o.shipping_address, icon: '>' },
            { label: 'Items', value: itemsHtml, raw: true, icon: '*' },
            { label: 'Notes', value: o.notes, icon: '*' },
            { label: 'Source', value: o.source, icon: '>' },
            { label: 'Created At', value: o.created_at ? tzDateTime(o.created_at) : null, icon: '>' },
            { label: 'Updated At', value: o.updated_at ? tzDateTime(o.updated_at) : null, icon: '>' },
        ];

        content.innerHTML = `
            <div class="order-detail-header">
                <div>
                    <h3 class="order-detail-title">Order #${esc(o.order_id)}</h3>
                    <p class="order-detail-subtitle">${o.customer_name ? esc(o.customer_name) : 'Customer'} ${o.order_date ? '  ' + tzShortDate(o.order_date) : ''}</p>
                </div>
                <button class="order-detail-close" onclick="closeOrderModal()" title="Close">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="order-detail-body">
                ${rows.map(r => {
            const val = r.value;
            if (val === null || val === undefined || val === '') return '';
            const displayVal = r.raw ? val : esc(String(val));
            return `<div class="order-detail-row">
                        <div class="order-detail-label"><span class="order-detail-icon">${r.icon}</span>${r.label}</div>
                        <div class="order-detail-value">${displayVal}</div>
                    </div>`;
        }).join('')}
            </div>
        `;
    } catch (e) {
        content.innerHTML = `<div class="empty-state" style="padding:32px"><p>Failed to load order details</p><p style="font-size:.75rem;color:var(--text-muted)">${esc(e.message || '')}</p></div>`;
    }
}

function closeOrderModal() {
    const overlay = document.getElementById('orderDetailOverlay');
    if (overlay) overlay.classList.remove('active');
}


/* ===============================================================
   RESTRICTIONS / RULES TAB - Premium glassmorphism UI (V4.3)
   Saves to tenant.description → injected into LLM system prompt
   =============================================================== */

var SVG_SHIELD = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
var SVG_UPLOAD = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>';
var SVG_EDIT = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
var SVG_IMAGE = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
var SVG_FOLDER = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>';
var SVG_CATEGORY = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>';
var SVG_SPARKLE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>';
var SVG_LIGHTBULB = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 00-4 12.7V17h8v-2.3A7 7 0 0012 2z"/></svg>';

var RESTRICTION_SUGGESTIONS = [
    'Do not show any product images in responses',
    'Always respond in a formal and professional tone',
    'Never mention competitor brands or products',
    'Do not discuss pricing or discounts unless asked',
    'Always recommend contacting support for refund requests',
    'Keep all responses under 3 sentences',
    'Do not share internal company policies with customers',
    'Always greet the customer by name if available',
];

async function loadRestrictionsTab() {
    var panel = document.querySelector('#panel-kb-about .kb-panel');
    if (!panel) return;

    var chipHtml = RESTRICTION_SUGGESTIONS.map(function (s) {
        return '<button class="restriction-chip" type="button">' + SVG_SPARKLE + ' ' + esc(s) + '</button>';
    }).join('');

    panel.innerHTML =
        '<div class="kb-section restrictions-section">' +
        // Hero Card
        '<div class="kb-card kb-card--glass kb-card--restrictions">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon kb-card-icon--shield">' + SVG_SHIELD + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">AI Restrictions &amp; Rules</h3>' +
        '<p class="kb-card-desc">Define instructions and boundaries for your AI chatbot. These rules are injected directly into the AI\'s system prompt and override default behavior.</p>' +
        '</div>' +
        '</div>' +
        '<div class="restriction-status" id="restrictionStatus">' +
        '<span class="restriction-status-dot restriction-status-dot--loading"></span>' +
        '<span class="restriction-status-text">Loading current restrictions...</span>' +
        '</div>' +
        '<div class="restriction-editor">' +
        '<textarea class="kb-textarea kb-textarea--restrictions" id="restrictionText" rows="8" placeholder="Enter your AI restrictions and rules here...\n\nExamples:\n• Do not show any product images\n• Always respond in formal English\n• Never mention competitor products\n• Keep responses under 3 sentences"></textarea>' +
        '<div class="restriction-footer">' +
        '<span class="restriction-char-count" id="restrictionCharCount">0 / 2000 characters</span>' +
        '<div class="restriction-actions">' +
        '<button class="btn btn-sm btn-ghost" id="restrictionClearBtn" type="button">Clear All</button>' +
        '<button class="btn btn-sm btn-primary btn--glow" id="restrictionSaveBtn" type="button">' + SVG_SHIELD + ' Save Restrictions</button>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>' +
        // Suggestion Chips
        '<div class="kb-card kb-card--glass">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon kb-card-icon--idea">' + SVG_LIGHTBULB + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Quick Suggestions</h3>' +
        '<p class="kb-card-desc">Click any suggestion to add it to your restrictions</p>' +
        '</div>' +
        '</div>' +
        '<div class="restriction-chips">' + chipHtml + '</div>' +
        '</div>' +
        // How it works
        '<div class="kb-card kb-card--glass kb-card--pipeline">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon kb-card-icon--info"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg></div>' +
        '<div>' +
        '<h3 class="kb-card-title">How It Works</h3>' +
        '<p class="kb-card-desc">Your restrictions flow through the AI pipeline</p>' +
        '</div>' +
        '</div>' +
        '<div class="pipeline-flow">' +
        '<div class="pipeline-step"><div class="pipeline-step-num">1</div><div class="pipeline-step-label">You write restrictions here</div></div>' +
        '<div class="pipeline-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div>' +
        '<div class="pipeline-step"><div class="pipeline-step-num">2</div><div class="pipeline-step-label">Saved as AI guidelines</div></div>' +
        '<div class="pipeline-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div>' +
        '<div class="pipeline-step"><div class="pipeline-step-num">3</div><div class="pipeline-step-label">Injected into LLM system prompt</div></div>' +
        '<div class="pipeline-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div>' +
        '<div class="pipeline-step pipeline-step--final"><div class="pipeline-step-num">' + SVG_SPARKLE + '</div><div class="pipeline-step-label">AI follows your rules</div></div>' +
        '</div>' +
        '</div>' +
        '</div>';

    // --- Load existing restrictions ---
    var textarea = document.getElementById('restrictionText');
    var charCount = document.getElementById('restrictionCharCount');
    var statusEl = document.getElementById('restrictionStatus');

    function updateCharCount() {
        var len = textarea.value.length;
        charCount.textContent = len + ' / 2000 characters';
        charCount.classList.toggle('over-limit', len > 2000);
    }
    textarea.addEventListener('input', updateCharCount);

    try {
        var resp = await API.getRestrictions();
        textarea.value = resp.restrictions || '';
        updateCharCount();
        if (resp.restrictions && resp.restrictions.trim()) {
            statusEl.innerHTML = '<span class="restriction-status-dot restriction-status-dot--active"></span>' +
                '<span class="restriction-status-text">' + resp.restrictions.trim().split('\n').length + ' restriction(s) active</span>';
        } else {
            statusEl.innerHTML = '<span class="restriction-status-dot restriction-status-dot--empty"></span>' +
                '<span class="restriction-status-text">No restrictions set — AI uses default behavior</span>';
        }
    } catch (err) {
        statusEl.innerHTML = '<span class="restriction-status-dot restriction-status-dot--empty"></span>' +
            '<span class="restriction-status-text">Could not load restrictions</span>';
    }

    // --- Save restrictions ---
    document.getElementById('restrictionSaveBtn').addEventListener('click', async function () {
        var text = textarea.value.trim();
        if (text.length > 2000) { showToast('Restrictions too long (max 2000 chars)', 'warning'); return; }
        try {
            var data = await API.updateRestrictions(text);
            showToast('Restrictions saved — AI will follow these rules', 'success');
            var lines = text ? text.split('\n').filter(function (l) { return l.trim(); }).length : 0;
            statusEl.innerHTML = lines > 0
                ? '<span class="restriction-status-dot restriction-status-dot--active"></span><span class="restriction-status-text">' + lines + ' restriction(s) active</span>'
                : '<span class="restriction-status-dot restriction-status-dot--empty"></span><span class="restriction-status-text">No restrictions set — AI uses default behavior</span>';
        } catch (err) { showToast('Failed to save: ' + err.message, 'error'); }
    });

    // --- Clear ---
    document.getElementById('restrictionClearBtn').addEventListener('click', function () {
        if (!confirm('Clear all restrictions? This will not save automatically.')) return;
        textarea.value = '';
        updateCharCount();
    });

    // --- Suggestion chips ---
    document.querySelectorAll('.restriction-chip').forEach(function (chip) {
        chip.addEventListener('click', function () {
            var suggestion = chip.textContent.trim();
            var current = textarea.value.trim();
            if (current && !current.endsWith('\n')) current += '\n';
            textarea.value = current + '• ' + suggestion + '\n';
            updateCharCount();
            textarea.scrollTop = textarea.scrollHeight;
            chip.classList.add('restriction-chip--used');
        });
    });
}

/* ===============================================================
   CUSTOM DATA TAB - Premium enhanced with categories (V4.3)
   =============================================================== */

var CUSTOM_CATEGORIES = [
    {
        value: 'privacy_policy', label: 'Privacy Policy', color: '#6366f1',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
    },
    {
        value: 'refund_policy', label: 'Return / Refund', color: '#f59e0b',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>'
    },
    {
        value: 'about_company', label: 'About Company', color: '#3b82f6',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
    },
    {
        value: 'faq', label: 'FAQs', color: '#10b981',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    },
    {
        value: 'contact_info', label: 'Contact Info', color: '#8b5cf6',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.8 19.79 19.79 0 01.06 1.18 2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.72 6.72l1.28-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>'
    },
    {
        value: 'shipping_policy', label: 'Shipping', color: '#ec4899',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>'
    },
    {
        value: 'terms_of_service', label: 'Terms &amp; Conditions', color: '#14b8a6',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>'
    },
    {
        value: 'general', label: 'Other / General', color: '#64748b',
        svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>'
    },
];

async function loadCustomDataTab() {
    var panel = document.querySelector('#panel-kb-custom .kb-panel');
    if (!panel) return;

    // Build category cards with SVG icons
    var catCardsHtml = CUSTOM_CATEGORIES.map(function (c, i) {
        var active = i === 0 ? ' kb-cat-card--active' : '';
        return '<button class="kb-cat-card' + active + '" data-cat="' + c.value + '" style="--cat-color:' + c.color + '" type="button">' +
            '<span class="kb-cat-card-icon">' + c.svg + '</span>' +
            '<span class="kb-cat-card-label">' + c.label + '</span>' +
            '</button>';
    }).join('');

    panel.innerHTML =
        '<div class="kb-section custom-data-section">' +

        // ── Category Selector ──────────────────────────────────────────
        '<div class="kb-card kb-card--glass">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon kb-card-icon--category">' + SVG_CATEGORY + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Select Category</h3>' +
        '<p class="kb-card-desc">Choose the type of knowledge to keep your AI\'s data organised</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-cat-grid" id="customCatGrid">' + catCardsHtml + '</div>' +
        '</div>' +

        // ── Input Mode Toggle + Panes ──────────────────────────────────
        '<div class="kb-card kb-card--glass">' +
        '<div class="kb-input-mode-toggle">' +
        '<button class="kb-mode-btn kb-mode-btn--active" data-mode="upload" type="button">' +
        SVG_UPLOAD + ' <span>Upload File</span></button>' +
        '<button class="kb-mode-btn" data-mode="text" type="button">' +
        SVG_EDIT + ' <span>Paste Text</span></button>' +
        '<button class="kb-mode-btn" data-mode="image" type="button">' +
        SVG_IMAGE + ' <span>Upload Image</span></button>' +
        '</div>' +

        // Upload pane
        '<div class="kb-input-pane kb-input-pane--active" id="customPane-upload">' +
        '<div class="kb-upload-zone" id="kbUpload-kb-custom">' +
        '<div class="kb-upload-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>' +
        '<p class="kb-upload-title">Drag &amp; drop files or <span class="kb-upload-link" id="kbBrowseTrigger">browse</span></p>' +
        '<p class="kb-upload-hint">PDF, DOCX, TXT, CSV, JSON, MD, XLSX, RTF — multi-file supported</p>' +
        '<input type="file" id="kbFile-kb-custom" accept=".csv,.pdf,.docx,.doc,.txt,.json,.md,.xlsx,.xls,.rtf,.pptx,.ppt" style="display:none" multiple>' +
        '</div>' +
        '<div class="kb-progress" id="kbProgress-kb-custom" style="display:none"><div class="kb-progress-bar"><div class="kb-progress-fill"></div></div><span class="kb-progress-text">Uploading...</span></div>' +
        '</div>' +

        // Text pane
        '<div class="kb-input-pane" id="customPane-text">' +
        '<textarea class="kb-textarea" id="kbText-kb-custom" rows="8" placeholder="Paste or type your custom knowledge here...&#10;&#10;Examples:&#10;• Return Policy: Items can be returned within 30 days of receipt.&#10;• Operating Hours: We are open Monday to Friday, 9 AM to 5 PM EST.&#10;• Contact Info: Reach our support team at support@example.com&#10;• General Rules: Only members can access the premium lounge."></textarea>' +
        '<div class="kb-text-actions">' +
        '<button class="btn btn-primary btn--glow" id="kbSaveText-kb-custom" type="button">' +
        SVG_EDIT + ' Save to Knowledge Base' +
        '</button>' +
        '</div>' +
        '</div>' +

        // Image pane
        '<div class="kb-input-pane" id="customPane-image">' +
        '<div class="kb-upload-zone kb-upload-zone--image" id="kbImgZone-kb-custom">' +
        '<div class="kb-upload-icon">' + SVG_IMAGE + '</div>' +
        '<p class="kb-upload-title">Drag &amp; drop an image or <span class="kb-upload-link" id="kbImgBrowseTrigger">browse</span></p>' +
        '<p class="kb-upload-hint">PNG, JPG, JPEG, WEBP</p>' +
        '<input type="file" id="kbImg-kb-custom" accept="image/*" style="display:none">' +
        '</div>' +
        '<div class="kb-progress" id="kbImgProgress-kb-custom" style="display:none"><div class="kb-progress-bar"><div class="kb-progress-fill"></div></div><span class="kb-progress-text">Uploading image...</span></div>' +
        '</div>' +

        '</div>' + // end kb-card

        // ── Documents Table ────────────────────────────────────────────
        '<div class="kb-card kb-card--glass">' +
        '<div class="kb-docs-header">' +
        '<h3 class="kb-docs-title">' + SVG_FOLDER + ' Knowledge Base Documents</h3>' +
        '<span class="kb-docs-count" id="kbCount-kb-custom">loading...</span>' +
        '</div>' +
        '<div class="kb-docs-table-wrap" id="kbDocs-kb-custom"><div class="loading-state"><div class="spinner"></div><p>Loading...</p></div></div>' +
        '</div>' +

        '</div>'; // end kb-section

    // ── Selected category state ────────────────────────────────────────
    var selectedCat = CUSTOM_CATEGORIES[0].value;

    document.querySelectorAll('.kb-cat-card').forEach(function (card) {
        card.addEventListener('click', function () {
            document.querySelectorAll('.kb-cat-card').forEach(function (c) {
                c.classList.remove('kb-cat-card--active');
            });
            card.classList.add('kb-cat-card--active');
            selectedCat = card.dataset.cat;
        });
    });

    function getDocType() { return selectedCat; }

    // ── Mode toggle ────────────────────────────────────────────────────
    document.querySelectorAll('.kb-mode-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.kb-mode-btn').forEach(function (b) {
                b.classList.remove('kb-mode-btn--active');
            });
            btn.classList.add('kb-mode-btn--active');
            document.querySelectorAll('.kb-input-pane').forEach(function (p) {
                p.classList.remove('kb-input-pane--active');
            });
            var pane = document.getElementById('customPane-' + btn.dataset.mode);
            if (pane) pane.classList.add('kb-input-pane--active');
        });
    });

    // ── File upload zone — click ANYWHERE in zone opens file picker ──
    var zone = document.getElementById('kbUpload-kb-custom');
    var fileInput = document.getElementById('kbFile-kb-custom');

    // Clicking anywhere inside the upload zone triggers the file picker
    zone.addEventListener('click', function (e) {
        // Don't re-trigger if user somehow clicked the hidden input itself
        if (e.target === fileInput) return;
        fileInput.click();
    });
    zone.addEventListener('dragover', function (e) {
        e.preventDefault(); zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', function () { zone.classList.remove('drag-over'); });
    zone.addEventListener('drop', function (e) {
        e.preventDefault(); zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            kbUploadFiles('kb-custom', getDocType(), 'Custom Data', Array.from(e.dataTransfer.files));
        }
    });
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length) {
            kbUploadFiles('kb-custom', getDocType(), 'Custom Data', Array.from(fileInput.files));
        }
        fileInput.value = '';
    });

    // ── Text save ─────────────────────────────────────────────────────
    document.getElementById('kbSaveText-kb-custom').addEventListener('click', function () {
        var dt = getDocType();
        var cat = CUSTOM_CATEGORIES.find(function (c) { return c.value === dt; });
        kbSaveText('kb-custom', dt, cat ? cat.label : 'Custom');
    });

    // ── Image upload zone ──────────────────────────────────────────────
    var imgZone = document.getElementById('kbImgZone-kb-custom');
    var imgInput = document.getElementById('kbImg-kb-custom');
    var imgBrowse = document.getElementById('kbImgBrowseTrigger');

    imgBrowse.addEventListener('click', function (e) {
        e.stopPropagation();
        imgInput.click();
    });
    imgZone.addEventListener('click', function () { imgInput.click(); });
    imgZone.addEventListener('dragover', function (e) {
        e.preventDefault(); imgZone.classList.add('drag-over');
    });
    imgZone.addEventListener('dragleave', function () { imgZone.classList.remove('drag-over'); });
    imgZone.addEventListener('drop', function (e) {
        e.preventDefault(); imgZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            kbUploadImgFiles(getDocType(), Array.from(e.dataTransfer.files));
        }
    });
    imgInput.addEventListener('change', function () {
        if (imgInput.files.length) {
            kbUploadImgFiles(getDocType(), Array.from(imgInput.files));
            imgInput.value = '';
        }
    });

    await kbLoadAllCustomDocuments();
}

// Separate image upload helper so it uses the image progress bar
async function kbUploadImgFiles(docType, files) {
    var progress = document.getElementById('kbImgProgress-kb-custom');
    if (progress) progress.style.display = 'flex';
    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        var fd = new FormData();
        fd.append('file', file);
        fd.append('doc_type', docType);
        fd.append('category', docType);
        try {
            var data = await API.uploadKnowledgeFile(fd);
            if (data.success) {
                showToast('"' + file.name + '" indexed (' + data.chunks_created + ' chunks)', 'success');
            } else {
                showToast('Failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (err) {
            showToast('Upload error: ' + err.message, 'error');
        }
    }
    if (progress) progress.style.display = 'none';
    await kbLoadAllCustomDocuments();
}

/* ===============================================================
   KB SHARED HELPERS
   =============================================================== */

function kbWireUploadZone(tabId, docType, label) {
    var zone = document.getElementById('kbUpload-' + tabId);
    var fileInput = document.getElementById('kbFile-' + tabId);
    if (!zone || !fileInput) return;
    zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', function () { zone.classList.remove('drag-over'); });
    zone.addEventListener('drop', function (e) {
        e.preventDefault(); zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) kbUploadFiles(tabId, docType, label, Array.from(e.dataTransfer.files));
    });
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length) kbUploadFiles(tabId, docType, label, Array.from(fileInput.files));
        fileInput.value = '';
    });
}

async function kbUploadFiles(tabId, docType, label, files) {
    var progress = document.getElementById('kbProgress-' + tabId);
    if (progress) progress.style.display = 'flex';

    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        var fd = new FormData();
        fd.append('file', file);
        fd.append('doc_type', docType);
        fd.append('category', docType);
        try {
            var data = await API.uploadKnowledgeFile(fd);
            if (data.success) {
                showToast('"' + file.name + '" indexed (' + data.chunks_created + ' chunks)', 'success');
            } else {
                showToast('Failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (err) {
            showToast('Upload error: ' + err.message, 'error');
        }
    }

    if (progress) progress.style.display = 'none';
    if (tabId === 'kb-custom') { await kbLoadAllCustomDocuments(); }
    else { await kbLoadDocuments(tabId, docType); }
}

async function kbSaveText(tabId, docType, label) {
    var textArea = document.getElementById('kbText-' + tabId);
    var text = textArea.value.trim();
    if (!text) { showToast('Please enter some text first', 'warning'); return; }
    try {
        var data = await API.addKnowledgeText(text, 'manual_' + docType, docType, docType);
        if (data.success) {
            showToast(label + ' saved (' + data.chunks_created + ' chunks)', 'success');
            textArea.value = '';
            if (tabId === 'kb-custom') { await kbLoadAllCustomDocuments(); }
            else { await kbLoadDocuments(tabId, docType); }
        } else {
            showToast('Failed: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (err) { showToast('Save error: ' + err.message, 'error'); }
}

async function kbLoadDocuments(tabId, docType) {
    var container = document.getElementById('kbDocs-' + tabId);
    var countEl = document.getElementById('kbCount-' + tabId);
    if (!container) return;
    try {
        var data = await API.getKnowledgeDocuments();
        var docs = (data.documents || []).filter(function (d) { return d.doc_type === docType; });
        if (countEl) countEl.textContent = docs.length + ' document' + (docs.length !== 1 ? 's' : '');
        kbRenderDocsTable(container, docs, tabId, docType);
    } catch (err) {
        container.innerHTML = '<div class="kb-empty"><p>Failed to load documents</p></div>';
    }
}

async function kbLoadAllCustomDocuments() {
    var container = document.getElementById('kbDocs-kb-custom');
    var countEl = document.getElementById('kbCount-kb-custom');
    if (!container) return;
    var excludeTypes = ['product', 'order', 'about'];
    try {
        var data = await API.getKnowledgeDocuments();
        var docs = (data.documents || []).filter(function (d) { return excludeTypes.indexOf(d.doc_type) === -1; });
        if (countEl) countEl.textContent = docs.length + ' document' + (docs.length !== 1 ? 's' : '');
        kbRenderDocsTable(container, docs, 'kb-custom', null);
    } catch (err) {
        container.innerHTML = '<div class="kb-empty"><p>Failed to load documents</p></div>';
    }
}

function kbRenderDocsTable(container, docs, tabId, docType) {
    if (!docs.length) {
        container.innerHTML = '<div class="kb-empty"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>No documents uploaded yet</p></div>';
        return;
    }
    var catMap = {};
    CUSTOM_CATEGORIES.forEach(function (c) { catMap[c.value] = c.label; });

    var rows = docs.map(function (d) {
        var size = d.file_size ? (d.file_size / 1024).toFixed(1) + ' KB' : '--';
        var date = d.created_at ? tzShortDate(d.created_at) : '--';
        var chunks = d.chunk_count || '--';
        var name = esc(d.filename || d.id);
        var catLabel = catMap[d.doc_type] || d.doc_type || '--';
        var delType = docType || d.doc_type || 'general';
        return '<tr>' +
            '<td class="kb-doc-name" title="' + name + '">' + name + '</td>' +
            '<td><span class="kb-cat-pill">' + catLabel + '</span></td>' +
            '<td>' + size + '</td>' +
            '<td>' + chunks + '</td>' +
            '<td>' + date + '</td>' +
            '<td class="kb-doc-actions">' +
            '<button class="kb-btn kb-btn-view" onclick="kbViewDoc(\'' + d.id + '\',\'' + esc(d.filename) + '\')" title="View"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button>' +
            '<button class="kb-btn kb-btn-del" onclick="kbDeleteDoc(\'' + d.id + '\',\'' + tabId + '\',\'' + delType + '\')" title="Delete"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>' +
            '</td></tr>';
    }).join('');

    container.innerHTML = '<table class="kb-table"><thead><tr><th>Document</th><th>Category</th><th>Size</th><th>Chunks</th><th>Date</th><th>Actions</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

async function kbDeleteDoc(docId, tabId, docType) {
    if (!confirm('Delete this document from the knowledge base?')) return;
    try {
        await API.deleteKnowledgeDocument(docId);
        showToast('Document deleted', 'success');
        if (tabId === 'kb-custom') { await kbLoadAllCustomDocuments(); }
        else { await kbLoadDocuments(tabId, docType); }
    } catch (err) { showToast('Delete failed: ' + err.message, 'error'); }
}

function kbViewDoc(docId, filename) {
    const modal = document.getElementById('docViewModal');
    const titleEl = document.getElementById('docViewTitle');
    const loadingEl = document.getElementById('docViewLoading');
    const textEl = document.getElementById('docViewText');

    if (!modal) {
        showToast('Document Viewer not initialized.', 'error');
        return;
    }

    modal.style.display = 'flex';
    titleEl.textContent = 'Loading...';
    loadingEl.style.display = 'flex';
    textEl.style.display = 'none';
    textEl.textContent = '';

    API.getKnowledgeDocumentContent(docId).then(result => {
        if (result && result.error) {
            titleEl.textContent = 'Error';
            textEl.textContent = result.error || 'Failed to load document content.';
        } else if (result) {
            titleEl.textContent = result.filename || filename || 'Document Content';
            textEl.textContent = result.content || 'Document is empty.';
        } else {
            titleEl.textContent = 'Error';
            textEl.textContent = 'Unknown error occurred.';
        }
    }).catch(err => {
        console.error('View document error:', err);
        titleEl.textContent = 'Error';
        textEl.textContent = 'A network error occurred while loading the document.';
    }).finally(() => {
        loadingEl.style.display = 'none';
        textEl.style.display = 'block';
    });
}

// Make KB functions globally accessible
window.kbDeleteDoc = kbDeleteDoc;
window.kbViewDoc = kbViewDoc;

// Make all onclick-referenced functions globally accessible
window.switchTab = switchTab;
window.selectConversation = selectConversation;
window.deleteOrder = deleteOrder;
window.viewOrder = viewOrder;
window.closeOrderModal = closeOrderModal;
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
