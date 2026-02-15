/**
 * Behavioral Agentic AI — Embeddable Chat Widget
 * FRD v3.0 Zone 6: Customer Chat Layer
 * 
 * FR-6.1: Platform-agnostic embeddable widget via <script> tag
 * FR-6.2: Full chat interface with pre-chat form, typing indicator, session persistence
 * 
 * Usage:
 *   <script src="https://your-api.com/widget/embed.js" data-widget-key="wk_..." async></script>
 */
(function () {
    'use strict';

    // ═══════════════════════════════════════════════════════════════
    // CONFIGURATION
    // ═══════════════════════════════════════════════════════════════
    // document.currentScript is null for async/defer scripts, so use fallback
    const SCRIPT = document.currentScript
        || document.querySelector('script[data-widget-key]')
        || document.querySelector('script[data-key]')
        || document.querySelector('script[src*="embed.js"]');

    // Accept both data-widget-key (canonical) and data-key (shorthand)
    const API_KEY = SCRIPT?.getAttribute('data-widget-key')
        || SCRIPT?.getAttribute('data-key');
    const API_BASE = SCRIPT?.src ? new URL(SCRIPT.src).origin : window.location.origin;

    if (!API_KEY) {
        console.error('[BehavioralAI] ❌ Widget cannot start: missing data-widget-key or data-key attribute on the script tag.');
        console.error('[BehavioralAI] Example: <script src=".../widget/embed.js" data-widget-key="wk_..."></script>');
        return;
    }

    // Session persistence — FR-6.2.14
    const STORAGE_KEY = `bai_session_${API_KEY.slice(0, 8)}`;
    const getSession = () => {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); } catch { return null; }
    };
    const setSession = (data) => {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { }
    };

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════
    let widgetConfig = null;
    let session = getSession();
    let messages = [];
    let isOpen = false;
    let isLoading = false;
    let preChatDone = !!session;

    // ═══════════════════════════════════════════════════════════════
    // API CALLS
    // ═══════════════════════════════════════════════════════════════
    async function apiCall(path, options = {}) {
        const url = `${API_BASE}${path}`;
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!res.ok) throw new Error(`API ${res.status}`);
        return res.json();
    }

    async function loadConfig() {
        try {
            const raw = await apiCall(`/api/widget/${API_KEY}/config`);
            // Defensive: handle both flat and wrapped {config: {...}} response shapes
            widgetConfig = raw?.config || raw;
            return widgetConfig;
        } catch (e) {
            console.warn('[BehavioralAI] Config load failed, retrying...', e);
            // Single retry after 1s
            await new Promise(r => setTimeout(r, 1000));
            const raw = await apiCall(`/api/widget/${API_KEY}/config`);
            widgetConfig = raw?.config || raw;
            return widgetConfig;
        }
    }

    async function startSession(name, email) {
        const data = await apiCall(`/api/widget/${API_KEY}/session`, {
            method: 'POST',
            body: JSON.stringify({ customer_name: name, customer_email: email })
        });
        session = { session_id: data.session_id, name, email };
        setSession(session);
        return data;
    }

    async function sendMessage(text) {
        return apiCall(`/api/widget/${API_KEY}/chat`, {
            method: 'POST',
            body: JSON.stringify({
                session_id: session.session_id,
                message: text,
                customer_name: session.name
            })
        });
    }

    async function loadHistory() {
        try {
            const data = await apiCall(`/api/widget/${API_KEY}/history?session_id=${session.session_id}`);
            return data.messages || [];
        } catch { return []; }
    }

    // ═══════════════════════════════════════════════════════════════
    // STYLES (injected into Shadow DOM) — FR-6.1.3
    // ═══════════════════════════════════════════════════════════════
    function getStyles(config) {
        const color = config?.theme_color || '#6366f1';
        return `
      :host { all: initial; font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif; }
      * { box-sizing: border-box; margin: 0; padding: 0; }

      /* ── Bubble ── */
      .bai-bubble {
        position: fixed; ${config?.position === 'bottom-left' ? 'left: 24px' : 'right: 24px'}; bottom: 24px;
        width: 60px; height: 60px; border-radius: 50%;
        background: ${color}; color: #fff; border: none; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 24px rgba(0,0,0,0.2); z-index: 2147483647;
        transition: transform 0.2s, box-shadow 0.2s;
      }
      .bai-bubble:hover { transform: scale(1.1); box-shadow: 0 6px 32px rgba(0,0,0,0.3); }
      .bai-bubble svg { width: 28px; height: 28px; fill: currentColor; }

      /* ── Panel ── */
      .bai-panel {
        position: fixed; ${config?.position === 'bottom-left' ? 'left: 24px' : 'right: 24px'}; bottom: 100px;
        width: 380px; max-width: calc(100vw - 48px); height: 520px; max-height: calc(100vh - 140px);
        background: #fff; border-radius: 16px; overflow: hidden;
        box-shadow: 0 16px 64px rgba(0,0,0,0.16); z-index: 2147483647;
        display: flex; flex-direction: column;
        opacity: 0; transform: translateY(16px) scale(0.95);
        transition: opacity 0.3s, transform 0.3s;
        pointer-events: none;
      }
      .bai-panel.open { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }

      /* ── Header ── */
      .bai-header {
        background: ${color}; color: #fff; padding: 16px 20px;
        display: flex; align-items: center; gap: 12px; flex-shrink: 0;
      }
      .bai-header-avatar {
        width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.2);
        display: flex; align-items: center; justify-content: center; font-size: 18px;
      }
      .bai-header-info { flex: 1; }
      .bai-header-name { font-weight: 600; font-size: 15px; }
      .bai-header-status { font-size: 12px; opacity: 0.85; display: flex; align-items: center; gap: 4px; }
      .bai-header-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; display: inline-block; }
      .bai-close { background: none; border: none; color: #fff; cursor: pointer; padding: 4px; border-radius: 6px; }
      .bai-close:hover { background: rgba(255,255,255,0.15); }
      .bai-close svg { width: 20px; height: 20px; fill: currentColor; }

      /* ── Messages ── */
      .bai-messages {
        flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;
        background: #f8fafc;
      }
      .bai-messages::-webkit-scrollbar { width: 4px; }
      .bai-messages::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

      .bai-msg { max-width: 85%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.5; word-wrap: break-word; }
      .bai-msg.customer { align-self: flex-end; background: ${color}; color: #fff; border-bottom-right-radius: 4px; }
      .bai-msg.ai, .bai-msg.agent { align-self: flex-start; background: #fff; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 4px; }
      .bai-msg.system { align-self: center; background: #fef3c7; color: #92400e; font-size: 12px; padding: 6px 12px; border-radius: 20px; }
      .bai-msg-time { font-size: 11px; opacity: 0.6; margin-top: 4px; }
      .bai-msg-sender { font-size: 11px; font-weight: 600; margin-bottom: 2px; opacity: 0.7; }

      /* ── Typing Indicator — FR-6.2.7 ── */
      .bai-typing { align-self: flex-start; display: flex; gap: 4px; padding: 12px 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; }
      .bai-typing span { width: 7px; height: 7px; background: #94a3b8; border-radius: 50%; animation: bai-bounce 1.4s infinite ease-in-out; }
      .bai-typing span:nth-child(2) { animation-delay: 0.2s; }
      .bai-typing span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes bai-bounce { 0%, 80%, 100% { transform: scale(0.6); } 40% { transform: scale(1); } }

      /* ── Welcome ── */
      .bai-welcome { text-align: center; padding: 30px 20px; color: #64748b; font-size: 14px; line-height: 1.6; }
      .bai-welcome-emoji { font-size: 32px; margin-bottom: 8px; }
      .bai-welcome-title { font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 4px; }

      /* ── Input ── */
      .bai-input-area {
        padding: 12px 16px; background: #fff; border-top: 1px solid #e2e8f0;
        display: flex; gap: 8px; align-items: center; flex-shrink: 0;
      }
      .bai-input {
        flex: 1; border: 1px solid #e2e8f0; border-radius: 24px; padding: 10px 16px;
        font-size: 14px; outline: none; font-family: inherit; background: #f8fafc;
        transition: border-color 0.2s;
      }
      .bai-input:focus { border-color: ${color}; background: #fff; }
      .bai-send {
        width: 40px; height: 40px; border: none; border-radius: 50%;
        background: ${color}; color: #fff; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: opacity 0.2s; flex-shrink: 0;
      }
      .bai-send:disabled { opacity: 0.5; cursor: not-allowed; }
      .bai-send svg { width: 18px; height: 18px; fill: currentColor; }

      /* ── Pre-Chat Form — FR-6.2.1 ── */
      .bai-prechat { padding: 24px 20px; flex: 1; display: flex; flex-direction: column; gap: 16px; }
      .bai-prechat-title { font-size: 16px; font-weight: 600; color: #1e293b; }
      .bai-prechat-desc { font-size: 13px; color: #64748b; }
      .bai-field { display: flex; flex-direction: column; gap: 4px; }
      .bai-field label { font-size: 13px; font-weight: 500; color: #475569; }
      .bai-field input {
        border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;
        font-size: 14px; outline: none; font-family: inherit; transition: border-color 0.2s;
      }
      .bai-field input:focus { border-color: ${color}; }
      .bai-prechat-btn {
        background: ${color}; color: #fff; border: none; border-radius: 10px;
        padding: 12px; font-size: 15px; font-weight: 600; cursor: pointer;
        transition: opacity 0.2s; margin-top: auto;
      }
      .bai-prechat-btn:hover { opacity: 0.9; }

      /* ── Branding ── */
      .bai-branding { text-align: center; padding: 6px; font-size: 11px; color: #94a3b8; background: #fff; border-top: 1px solid #f1f5f9; }
      .bai-branding a { color: #94a3b8; text-decoration: none; }

      /* ── Mobile — FR-6.1.10 ── */
      @media (max-width: 480px) {
        .bai-panel { width: 100vw; height: 100vh; max-height: 100vh; bottom: 0; right: 0; left: 0; border-radius: 0; }
        .bai-bubble { width: 52px; height: 52px; bottom: 16px; right: 16px; }
      }
    `;
    }

    // ═══════════════════════════════════════════════════════════════
    // RENDER
    // ═══════════════════════════════════════════════════════════════
    function createWidget(config) {
        // FR-6.1.3: Shadow DOM isolation
        const host = document.createElement('div');
        host.id = 'behavioral-ai-widget';
        const shadow = host.attachShadow({ mode: 'closed' });

        // Styles
        const style = document.createElement('style');
        style.textContent = getStyles(config);
        shadow.appendChild(style);

        // Chat bubble — FR-6.1.5
        const bubble = document.createElement('button');
        bubble.className = 'bai-bubble';
        bubble.setAttribute('aria-label', 'Open chat');
        bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/></svg>`;
        shadow.appendChild(bubble);

        // Chat panel
        const panel = document.createElement('div');
        panel.className = 'bai-panel';
        shadow.appendChild(panel);

        // State references
        const refs = { shadow, host, bubble, panel, config };

        // Render panel content
        renderPanel(refs);

        // Toggle open/close
        bubble.addEventListener('click', () => {
            isOpen = !isOpen;
            panel.classList.toggle('open', isOpen);
            if (isOpen && session && preChatDone) {
                loadAndDisplayHistory(refs);
            }
        });

        document.body.appendChild(host);
        return refs;
    }

    function renderPanel(refs) {
        const { panel, config } = refs;
        const botName = config?.bot_name || 'AI Assistant';
        const welcomeMsg = config?.welcome_message || 'Hello! How can I help you today?';

        panel.innerHTML = `
      <div class="bai-header">
        <div class="bai-header-avatar">🤖</div>
        <div class="bai-header-info">
          <div class="bai-header-name">${botName}</div>
          <div class="bai-header-status"><span class="bai-header-dot"></span> Online</div>
        </div>
        <button class="bai-close" aria-label="Close chat">
          <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
      <div class="bai-messages" id="bai-msgs">
        <div class="bai-welcome">
          <div class="bai-welcome-emoji">👋</div>
          <div class="bai-welcome-title">${welcomeMsg}</div>
          <div>Ask me anything about our products or services.</div>
        </div>
      </div>
      <div class="bai-input-area">
        <input class="bai-input" id="bai-input" placeholder="${config?.placeholder_text || 'Type your message...'}" autocomplete="off" />
        <button class="bai-send" id="bai-send" disabled aria-label="Send message">
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
      ${config?.show_branding !== false ? '<div class="bai-branding">Powered by <a href="#">Behavioral AI</a></div>' : ''}
    `;

        // Close button
        panel.querySelector('.bai-close').addEventListener('click', () => {
            isOpen = false;
            panel.classList.remove('open');
        });

        // Show pre-chat or chat
        if (!preChatDone && config?.pre_chat_form_enabled) {
            showPreChat(refs);
        } else if (!session) {
            // Auto-start anonymous session
            preChatDone = true;
            startSession('Visitor', '').then(() => {
                setupChatInput(refs);
            }).catch(() => {
                setupChatInput(refs);
            });
        } else {
            setupChatInput(refs);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // PRE-CHAT FORM — FR-6.2.1
    // ═══════════════════════════════════════════════════════════════
    function showPreChat(refs) {
        const { panel, config } = refs;
        const msgsEl = panel.querySelector('#bai-msgs');
        const inputArea = panel.querySelector('.bai-input-area');
        inputArea.style.display = 'none';

        msgsEl.innerHTML = '';
        msgsEl.className = 'bai-prechat';
        msgsEl.innerHTML = `
      <div class="bai-prechat-title">Start a conversation</div>
      <div class="bai-prechat-desc">Please enter your details so we can assist you better.</div>
      <div class="bai-field"><label>Name</label><input type="text" id="bai-pc-name" placeholder="Your name" required /></div>
      <div class="bai-field"><label>Email</label><input type="email" id="bai-pc-email" placeholder="you@example.com" /></div>
      <button class="bai-prechat-btn" id="bai-pc-submit">Start Chat</button>
    `;

        panel.querySelector('#bai-pc-submit').addEventListener('click', async () => {
            const name = panel.querySelector('#bai-pc-name').value.trim();
            const email = panel.querySelector('#bai-pc-email').value.trim();
            if (!name) { panel.querySelector('#bai-pc-name').style.borderColor = '#ef4444'; return; }

            try {
                await startSession(name, email);
                preChatDone = true;
                renderPanel(refs);
            } catch (e) {
                console.error('[BehavioralAI] Session start failed:', e);
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // CHAT INPUT
    // ═══════════════════════════════════════════════════════════════
    function setupChatInput(refs) {
        const { panel } = refs;
        const input = panel.querySelector('#bai-input');
        const sendBtn = panel.querySelector('#bai-send');
        if (!input || !sendBtn) return;

        input.addEventListener('input', () => {
            sendBtn.disabled = !input.value.trim();
        });

        const doSend = async () => {
            const text = input.value.trim();
            if (!text || isLoading) return;

            input.value = '';
            sendBtn.disabled = true;

            addMessage({ content: text, sender_type: 'customer', created_at: new Date().toISOString() }, refs);
            showTyping(refs);

            isLoading = true;
            try {
                const response = await sendMessage(text);
                hideTyping(refs);

                if (response.response) {
                    addMessage({
                        content: response.response,
                        sender_type: response.is_human_agent ? 'agent' : 'ai',
                        sender_name: response.is_human_agent ? 'Support Agent' : (refs.config?.bot_name || 'AI Assistant'),
                        created_at: new Date().toISOString()
                    }, refs);
                }

                // FR-6.2.11: Human agent transition banner
                if (response.is_escalated) {
                    addMessage({
                        content: '\u{1F514} This conversation has been escalated to a human agent for better assistance.',
                        sender_type: 'system',
                        created_at: new Date().toISOString()
                    }, refs);

                    // Update header status to show escalation
                    const statusEl = refs.panel.querySelector('.bai-header-status');
                    if (statusEl) {
                        statusEl.innerHTML = '<span class="bai-header-dot" style="background:#f59e0b"></span> Connecting to agent...';
                    }
                }
            } catch (e) {
                hideTyping(refs);
                addMessage({
                    content: 'Sorry, something went wrong. Please try again.',
                    sender_type: 'system',
                    created_at: new Date().toISOString()
                }, refs);
            }
            isLoading = false;
        };

        sendBtn.addEventListener('click', doSend);
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); } });
    }

    // ═══════════════════════════════════════════════════════════════
    // MESSAGE RENDERING
    // ═══════════════════════════════════════════════════════════════
    function addMessage(msg, refs) {
        const { panel } = refs;
        const msgsEl = panel.querySelector('#bai-msgs');
        if (!msgsEl) return;

        // Remove welcome message on first message
        const welcome = msgsEl.querySelector('.bai-welcome');
        if (welcome) welcome.remove();

        const div = document.createElement('div');
        div.className = `bai-msg ${msg.sender_type}`;

        let html = '';
        if (msg.sender_type === 'agent') {
            html += `<div class="bai-msg-sender">${msg.sender_name || 'Agent'}</div>`;
        }
        html += msg.content;
        if (msg.created_at) {
            const time = new Date(msg.created_at);
            html += `<div class="bai-msg-time">${time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>`;
        }

        div.innerHTML = html;
        msgsEl.appendChild(div);
        msgsEl.scrollTop = msgsEl.scrollHeight;
        messages.push(msg);
    }

    function showTyping(refs) {
        const msgsEl = refs.panel.querySelector('#bai-msgs');
        if (!msgsEl) return;
        const typing = document.createElement('div');
        typing.className = 'bai-typing';
        typing.id = 'bai-typing';
        typing.innerHTML = '<span></span><span></span><span></span>';
        msgsEl.appendChild(typing);
        msgsEl.scrollTop = msgsEl.scrollHeight;
    }

    function hideTyping(refs) {
        const typing = refs.panel.querySelector('#bai-typing');
        if (typing) typing.remove();
    }

    async function loadAndDisplayHistory(refs) {
        if (!session?.session_id || messages.length > 0) return;
        try {
            const history = await loadHistory();
            const msgsEl = refs.panel.querySelector('#bai-msgs');
            if (!msgsEl || history.length === 0) return;

            const welcome = msgsEl.querySelector('.bai-welcome');
            if (welcome) welcome.remove();

            for (const msg of history) {
                addMessage(msg, refs);
            }
        } catch (e) {
            console.error('[BehavioralAI] History load failed:', e);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // INIT — FR-6.1.7
    // ═══════════════════════════════════════════════════════════════
    async function init() {
        try {
            console.log(`[BehavioralAI] 🚀 Widget loading... API_BASE=${API_BASE}, KEY=${API_KEY.slice(0, 10)}...`);
            const config = await loadConfig();
            if (!config || config.is_active === false) {
                console.warn('[BehavioralAI] ⚠️ Widget is inactive for this key — not rendering.');
                return;
            }
            console.log('[BehavioralAI] ✅ Widget config loaded, creating widget...');
            createWidget(config);
            console.log('[BehavioralAI] ✅ Widget rendered successfully.');
        } catch (e) {
            console.error('[BehavioralAI] ❌ Widget initialization failed:', e.message || e);
            console.error('[BehavioralAI] Check: Is the backend running at ' + API_BASE + '? Is CORS enabled?');
        }
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
