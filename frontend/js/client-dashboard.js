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

const TAB_META = {
    overview: { title: 'Overview', subtitle: 'Welcome back - here\'s what\'s happening today' },
    conversations: { title: 'Conversations', subtitle: 'Monitor and respond to customer conversations' },
    orders: { title: 'Order Data', subtitle: 'Manage order data for AI order-tracking queries' },
    products: { title: 'Products', subtitle: 'Manage product listings for your AI catalog' },
    widget: { title: 'Widget Config', subtitle: 'Configure and deploy your chat widget' },
    analytics: { title: 'Analytics', subtitle: 'Insights into sentiment, escalations, and performance' },
    settings: { title: 'Settings', subtitle: 'Manage your profile, company, and preferences' },
    'kb-about': { title: 'About Company', subtitle: 'Company description, mission, contact, and key info for AI' },
    'kb-custom': { title: 'Custom Data', subtitle: 'Upload policies, rules, FAQs, and any knowledge base documents' },
};

/* --- Init ------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    // Auth guard
    const token = localStorage.getItem('access_token');
    if (!token) { window.location.href = '/pages/login.html'; return; }

    loadUserInfo();
    setupTabNavigation();

    setupMobileMenu();
    setupSettingsSubNav();
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
        case 'kb-about': loadAboutCompanyTab(); break;
        case 'kb-custom': loadCustomDataTab(); break;
    }
}

/* ***********************************************************
   TAB 1: OVERVIEW
   *********************************************************** */
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
            <p>No escalations - all clear!</p>
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
        if (m.sentiment_label || m.sentiment_score != null) {
            const score = m.sentiment_score != null ? m.sentiment_score : 0.5;
            const pct = Math.round(score * 100);

            if (type === 'ai') {
                // AI responses -> white/subtle pill
                const emotionLabel = _getEmotionLabel('positive', score);
                sentimentBadge = `<span class="msg-sentiment-pill msg-sentiment-pill--ai">` +
                    `<span class="msg-sentiment-dot"></span>${emotionLabel} | ${pct}%</span>`;
            } else {
                // Customer messages -> colorful pill by emotion
                const sentiment = m.sentiment_label || (score > 0.58 ? 'positive' : score < 0.42 ? 'negative' : 'neutral');
                const emotionLabel = _getEmotionLabel(sentiment, score);
                const cssClass = _labelToClass(emotionLabel);
                sentimentBadge = `<span class="msg-sentiment-pill msg-sentiment-pill--${cssClass}">` +
                    `<span class="msg-sentiment-dot"></span>${emotionLabel} | ${pct}%</span>`;
            }
        }

        const time = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

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
   TAB 3: ANALYTICS
   *********************************************************** */
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
   TAB 6: SETTINGS
   *********************************************************** */
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

        // Company — backend returns business_name, business_type, store_url, support_email
        document.getElementById('settingsCompanyName').value = tenant.business_name || profile.company_name || '';
        document.getElementById('settingsIndustry').value = tenant.business_type || '';
        document.getElementById('settingsSupportEmail').value = tenant.support_email || '';
        document.getElementById('settingsWebsite').value = tenant.store_url || '';

        // Team
        renderTeamList(team);

        // API key — backend returns { key: '...', is_active: bool }
        document.getElementById('apiKeyValue').textContent = (resp.api_key && resp.api_key.key) || '************';

        // Preferences (from settings sub-object)
        if (prefs) {
            document.getElementById('prefSensitivity').value = prefs.auto_escalation_threshold ? (prefs.auto_escalation_threshold / 100) : 0.7;
            document.getElementById('sensitivityValue').textContent = prefs.auto_escalation_threshold ? (prefs.auto_escalation_threshold / 100).toFixed(2) : '0.70';
        }
    } catch (err) {
        console.error('Settings load error:', err);
    }

    // Save profile — backend expects 'full_name' (not 'name')
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
            // Update localStorage so sidebar/UI reflects the new name immediately
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (result.profile) {
                Object.assign(user, result.profile);
            } else if (data.full_name) {
                user.full_name = data.full_name;
                user.name = data.full_name;
                // Recompute initials
                const parts = data.full_name.trim().split(/\s+/);
                user.initials = parts.length >= 2
                    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
                    : data.full_name.slice(0, 2).toUpperCase();
            }
            localStorage.setItem('user', JSON.stringify(user));
            loadUserInfo(); // Refresh sidebar user name/avatar
            showToast('Profile updated!', 'success');
        }
        catch { showToast('Update failed', 'error'); }
    };

    // Save company — backend expects business_name, business_type, store_url, support_email
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

    // Invite
    document.getElementById('inviteBtn').onclick = async () => {
        const data = {
            name: document.getElementById('inviteName').value,
            email: document.getElementById('inviteEmail').value,
        };
        if (!data.email) { showToast('Email is required', 'error'); return; }
        try {
            await API.inviteTeamMember(data);
            showToast('Team member added!', 'success');
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
            document.getElementById('apiKeyValue').textContent = result.new_key || result.api_key || '--';
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
            auto_escalation_threshold: Math.round(parseFloat(document.getElementById('prefSensitivity').value) * 100),
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

/* ***********************************************************
   SETTINGS SUB-NAV
   *********************************************************** */
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
        const data = await API.getOrders(page, 20, search, status);
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
    }
}

function renderOrderTable(orders) {
    const tbody = document.getElementById('orderTableBody');
    if (!orders.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:32px">No orders found</td></tr>';
        return;
    }
    tbody.innerHTML = orders.map(o => `
        <tr>
            <td><strong>${esc(o.order_id)}</strong></td>
            <td>${esc(o.customer_name || '--')}</td>
            <td>${esc(o.customer_email || '--')}</td>
            <td><span class="order-status order-status--${(o.status || 'pending').toLowerCase()}">${esc(o.status || 'pending')}</span></td>
            <td>${o.total_amount ? `${o.currency || '$'}${Number(o.total_amount).toFixed(2)}` : '--'}</td>
            <td>${o.order_date ? new Date(o.order_date).toLocaleDateString() : '--'}</td>
            <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-secondary" onclick="viewOrder('${esc(o.order_id)}')" title="View Details"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button>
                <button class="btn btn-sm btn-ghost" onclick="deleteOrder(${o.id})" title="Delete"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
            </td>
        </tr>
    `).join('');
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
            { label: 'Order Date', value: o.order_date ? new Date(o.order_date).toLocaleString() : null, icon: '>' },
            { label: 'Estimated Delivery', value: o.estimated_delivery ? new Date(o.estimated_delivery).toLocaleString() : null, icon: '>' },
            { label: 'Tracking Number', value: o.tracking_number, icon: '#' },
            { label: 'Carrier', value: o.carrier, icon: '>' },
            { label: 'Shipping Address', value: o.shipping_address, icon: '>' },
            { label: 'Items', value: itemsHtml, raw: true, icon: '*' },
            { label: 'Notes', value: o.notes, icon: '*' },
            { label: 'Source', value: o.source, icon: '>' },
            { label: 'Created At', value: o.created_at ? new Date(o.created_at).toLocaleString() : null, icon: '>' },
            { label: 'Updated At', value: o.updated_at ? new Date(o.updated_at).toLocaleString() : null, icon: '>' },
        ];

        content.innerHTML = `
            <div class="order-detail-header">
                <div>
                    <h3 class="order-detail-title">Order #${esc(o.order_id)}</h3>
                    <p class="order-detail-subtitle">${o.customer_name ? esc(o.customer_name) : 'Customer'} ${o.order_date ? '  ' + new Date(o.order_date).toLocaleDateString() : ''}</p>
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
   ABOUT COMPANY TAB - Enhanced, structured UI (V4.2)
   =============================================================== */

var SVG_BUILDING = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/><path d="M9 9h1"/><path d="M9 13h1"/><path d="M9 17h1"/></svg>';
var SVG_CLIP = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>';
var SVG_UPLOAD = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>';
var SVG_EDIT = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
var SVG_IMAGE = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
var SVG_FOLDER = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>';
var SVG_CATEGORY = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>';

async function loadAboutCompanyTab() {
    var panel = document.querySelector('#panel-kb-about .kb-panel');
    if (!panel) return;

    panel.innerHTML =
        '<div class="kb-section">' +
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_BUILDING + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Company Information</h3>' +
        '<p class="kb-card-desc">This data helps your AI respond accurately about your business</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-form-grid">' +
        '<div class="kb-field"><label class="kb-field-label">Company Name</label><input type="text" class="kb-input" id="aboutCompanyName" placeholder="e.g. Acme Corporation"></div>' +
        '<div class="kb-field"><label class="kb-field-label">Industry</label><input type="text" class="kb-input" id="aboutIndustry" placeholder="e.g. E-Commerce, Technology"></div>' +
        '<div class="kb-field"><label class="kb-field-label">Email</label><input type="email" class="kb-input" id="aboutEmail" placeholder="support@company.com"></div>' +
        '<div class="kb-field"><label class="kb-field-label">Phone</label><input type="tel" class="kb-input" id="aboutPhone" placeholder="+1 (555) 123-4567"></div>' +
        '<div class="kb-field"><label class="kb-field-label">Website</label><input type="url" class="kb-input" id="aboutWebsite" placeholder="https://www.company.com"></div>' +
        '<div class="kb-field"><label class="kb-field-label">Address</label><input type="text" class="kb-input" id="aboutAddress" placeholder="123 Main St, City, Country"></div>' +
        '</div>' +
        '<div class="kb-field" style="margin-top:12px">' +
        '<label class="kb-field-label">Company Mission / Description</label>' +
        '<textarea class="kb-textarea" id="aboutMission" rows="4" placeholder="Tell us about your company - mission, values, what you do, key offerings..."></textarea>' +
        '</div>' +
        '<div class="kb-text-actions" style="margin-top:14px">' +
        '<button class="btn btn-sm btn-primary" id="aboutSaveBtn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Save Company Info to Knowledge Base</button>' +
        '</div>' +
        '</div>' +
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_CLIP + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Upload Company Documents</h3>' +
        '<p class="kb-card-desc">Upload brochures, about-us pages, or brand guidelines</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-upload-zone" id="kbUpload-kb-about">' +
        '<div class="kb-upload-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>' +
        '<p class="kb-upload-title">Drag & drop files or <label class="kb-upload-link" for="kbFile-kb-about">browse</label></p>' +
        '<p class="kb-upload-hint">PDF, DOCX, TXT, CSV, PNG, JPG</p>' +
        '<input type="file" id="kbFile-kb-about" accept=".csv,.pdf,.docx,.doc,.txt,.json,.md,.png,.jpg,.jpeg,.webp" style="display:none" multiple>' +
        '</div>' +
        '<div class="kb-progress" id="kbProgress-kb-about" style="display:none"><div class="kb-progress-bar"><div class="kb-progress-fill"></div></div><span class="kb-progress-text">Uploading...</span></div>' +
        '</div>' +
        '</div>' +
        '<div class="kb-docs-section">' +
        '<div class="kb-docs-header">' +
        '<h3 class="kb-docs-title">' + SVG_FOLDER + ' Company Documents</h3>' +
        '<span class="kb-docs-count" id="kbCount-kb-about">loading...</span>' +
        '</div>' +
        '<div class="kb-docs-table-wrap" id="kbDocs-kb-about"><div class="loading-state"><div class="spinner"></div><p>Loading...</p></div></div>' +
        '</div>';

    // Wire save button
    document.getElementById('aboutSaveBtn').addEventListener('click', async function () {
        var fields = {
            name: document.getElementById('aboutCompanyName').value.trim(),
            industry: document.getElementById('aboutIndustry').value.trim(),
            email: document.getElementById('aboutEmail').value.trim(),
            phone: document.getElementById('aboutPhone').value.trim(),
            website: document.getElementById('aboutWebsite').value.trim(),
            address: document.getElementById('aboutAddress').value.trim(),
            mission: document.getElementById('aboutMission').value.trim(),
        };
        var parts = [];
        if (fields.name) parts.push('Company Name: ' + fields.name);
        if (fields.industry) parts.push('Industry: ' + fields.industry);
        if (fields.email) parts.push('Email: ' + fields.email);
        if (fields.phone) parts.push('Phone: ' + fields.phone);
        if (fields.website) parts.push('Website: ' + fields.website);
        if (fields.address) parts.push('Address: ' + fields.address);
        if (fields.mission) parts.push('About / Mission:\n' + fields.mission);
        if (!parts.length) { showToast('Please fill in at least one field', 'warning'); return; }

        var text = parts.join('\n');
        try {
            var data = await API.addKnowledgeText(text, 'company_info', 'about', 'about');
            if (data.success) {
                showToast('Company info saved (' + data.chunks_created + ' chunks)', 'success');
                ['aboutCompanyName', 'aboutIndustry', 'aboutEmail', 'aboutPhone', 'aboutWebsite', 'aboutAddress', 'aboutMission'].forEach(function (id) { document.getElementById(id).value = ''; });
                await kbLoadDocuments('kb-about', 'about');
            } else {
                showToast('Failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (err) { showToast('Error: ' + err.message, 'error'); }
    });

    kbWireUploadZone('kb-about', 'about', 'About Company');
    await kbLoadDocuments('kb-about', 'about');
}

/* ===============================================================
   CUSTOM DATA TAB - Enhanced with category selector (V4.2)
   =============================================================== */

var CUSTOM_CATEGORIES = [
    { value: 'privacy_policy', label: 'Privacy Policies' },
    { value: 'refund_policy', label: 'Refund Policies' },
    { value: 'company_rules', label: 'Company Rules' },
    { value: 'terms_of_service', label: 'Terms of Service' },
    { value: 'shipping_policy', label: 'Shipping Policies' },
    { value: 'faq', label: 'FAQs' },
    { value: 'contact_info', label: 'Contact Information' },
    { value: 'general', label: 'Other / General' },
];

async function loadCustomDataTab() {
    var panel = document.querySelector('#panel-kb-custom .kb-panel');
    if (!panel) return;

    var catOptions = CUSTOM_CATEGORIES.map(function (c) {
        return '<option value="' + c.value + '">' + c.label + '</option>';
    }).join('');

    panel.innerHTML =
        '<div class="kb-section">' +
        // Category Selector
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_CATEGORY + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Data Category</h3>' +
        '<p class="kb-card-desc">Select the type of data you are uploading to keep your knowledge base organized</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-category-selector">' +
        '<select class="kb-select" id="customCategory">' + catOptions + '</select>' +
        '<div class="kb-category-badge" id="customCategoryBadge">Privacy Policies</div>' +
        '</div>' +
        '</div>' +
        // Upload Zone
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_UPLOAD + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Upload Documents</h3>' +
        '<p class="kb-card-desc">Upload files to the selected category</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-upload-zone" id="kbUpload-kb-custom">' +
        '<div class="kb-upload-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>' +
        '<p class="kb-upload-title">Drag & drop files or <label class="kb-upload-link" for="kbFile-kb-custom">browse</label></p>' +
        '<p class="kb-upload-hint">CSV, PDF, DOCX, TXT, PNG, JPG - multi-file supported</p>' +
        '<input type="file" id="kbFile-kb-custom" accept=".csv,.pdf,.docx,.doc,.txt,.json,.md,.png,.jpg,.jpeg,.webp" style="display:none" multiple>' +
        '</div>' +
        '<div class="kb-progress" id="kbProgress-kb-custom" style="display:none"><div class="kb-progress-bar"><div class="kb-progress-fill"></div></div><span class="kb-progress-text">Uploading...</span></div>' +
        '</div>' +
        // Manual Text
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_EDIT + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Add Text Manually</h3>' +
        '<p class="kb-card-desc">Type or paste content directly</p>' +
        '</div>' +
        '</div>' +
        '<textarea class="kb-textarea" id="kbText-kb-custom" rows="4" placeholder="Type or paste content here..."></textarea>' +
        '<div class="kb-text-actions" style="margin-top:10px"><button class="btn btn-sm btn-primary" id="kbSaveText-kb-custom"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Save Text</button></div>' +
        '</div>' +
        // Image Upload
        '<div class="kb-card">' +
        '<div class="kb-card-header">' +
        '<div class="kb-card-icon">' + SVG_IMAGE + '</div>' +
        '<div>' +
        '<h3 class="kb-card-title">Add Image</h3>' +
        '<p class="kb-card-desc">Upload images to attach to this category</p>' +
        '</div>' +
        '</div>' +
        '<div class="kb-img-upload-row">' +
        '<label class="btn btn-sm btn-outline" for="kbImg-kb-custom" style="cursor:pointer"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> Choose Image</label>' +
        '<input type="file" id="kbImg-kb-custom" accept="image/*" style="display:none">' +
        '<span class="kb-img-name" id="kbImgName-kb-custom">No file chosen</span>' +
        '</div>' +
        '</div>' +
        '</div>' +
        // Documents
        '<div class="kb-docs-section">' +
        '<div class="kb-docs-header">' +
        '<h3 class="kb-docs-title">' + SVG_FOLDER + ' All Custom Documents</h3>' +
        '<span class="kb-docs-count" id="kbCount-kb-custom">loading...</span>' +
        '</div>' +
        '<div class="kb-docs-table-wrap" id="kbDocs-kb-custom"><div class="loading-state"><div class="spinner"></div><p>Loading...</p></div></div>' +
        '</div>';

    // Category selector
    var catSelect = document.getElementById('customCategory');
    var catBadge = document.getElementById('customCategoryBadge');
    catSelect.addEventListener('change', function () {
        var cat = CUSTOM_CATEGORIES.find(function (c) { return c.value === catSelect.value; });
        catBadge.textContent = cat ? cat.label : catSelect.value;
    });
    function getDocType() { return catSelect.value; }

    // File upload
    var zone = document.getElementById('kbUpload-kb-custom');
    var fileInput = document.getElementById('kbFile-kb-custom');
    zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', function () { zone.classList.remove('drag-over'); });
    zone.addEventListener('drop', function (e) {
        e.preventDefault(); zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) kbUploadFiles('kb-custom', getDocType(), 'Custom Data', Array.from(e.dataTransfer.files));
    });
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length) kbUploadFiles('kb-custom', getDocType(), 'Custom Data', Array.from(fileInput.files));
        fileInput.value = '';
    });

    // Manual text
    document.getElementById('kbSaveText-kb-custom').addEventListener('click', function () {
        var dt = getDocType();
        var cat = CUSTOM_CATEGORIES.find(function (c) { return c.value === dt; });
        kbSaveText('kb-custom', dt, cat ? cat.label : 'Custom');
    });

    // Image
    var imgInput = document.getElementById('kbImg-kb-custom');
    imgInput.addEventListener('change', function () {
        if (imgInput.files.length) {
            document.getElementById('kbImgName-kb-custom').textContent = imgInput.files[0].name;
            kbUploadFiles('kb-custom', getDocType(), 'Custom Data', Array.from(imgInput.files));
            imgInput.value = '';
        }
    });

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
        var date = d.created_at ? new Date(d.created_at).toLocaleDateString() : '--';
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
    showToast(filename + ' - ID: ' + docId, 'info');
}

// Make KB functions globally accessible
window.kbDeleteDoc = kbDeleteDoc;
window.kbViewDoc = kbViewDoc;

// Make all onclick-referenced functions globally accessible
window.switchTab = switchTab;
window.selectConversation = selectConversation;
window.removeTeamMember = removeTeamMember;
window.deleteOrder = deleteOrder;
window.viewOrder = viewOrder;
window.closeOrderModal = closeOrderModal;
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
