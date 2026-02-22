/**
 * Behavioral Agentic AI — Embeddable Chat Widget
 * FRD v3.0 Zone 6: Customer-Facing Widget
 *
 * Usage:
 *   <script src="path/to/widget.js" data-key="WIDGET_API_KEY"></script>
 *
 * This script self-initialises: it injects CSS, renders the chat bubble
 * and panel, and communicates with the Widget API endpoints.
 */
(function () {
    'use strict';

    // ── Configuration ──────────────────────────────────────────────
    const SCRIPT_TAG = document.currentScript || document.querySelector('script[data-key]');
    const API_KEY    = SCRIPT_TAG?.getAttribute('data-key') || '';
    const API_BASE   = SCRIPT_TAG?.getAttribute('data-api')  || 'http://localhost:8000';
    const POSITION   = SCRIPT_TAG?.getAttribute('data-pos')  || 'bottom-right';

    if (!API_KEY) {
        console.warn('[Behavioral AI] Missing data-key attribute on widget script tag.');
        return;
    }

    // ── State ──────────────────────────────────────────────────────
    let sessionId    = null;
    let config       = {};
    let isOpen       = false;
    let hasGreeted   = false;

    // ── Inject Styles ──────────────────────────────────────────────
    const style = document.createElement('style');
    style.textContent = `
        #bai-widget-root, #bai-widget-root * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

        /* Bubble */
        #bai-bubble {
            position: fixed; ${POSITION === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'} bottom: 24px;
            width: 60px; height: 60px; border-radius: 50%; z-index: 999998;
            background: var(--bai-color, #667eea); cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3); transition: transform 0.3s ease;
        }
        #bai-bubble:hover { transform: scale(1.1); }
        #bai-bubble svg { width: 28px; height: 28px; color: #fff; }

        /* Panel */
        #bai-panel {
            position: fixed; ${POSITION === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'} bottom: 96px;
            width: 380px; max-height: 540px; border-radius: 20px; overflow: hidden;
            background: #111118; border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 24px 64px rgba(0,0,0,0.5); z-index: 999999;
            display: flex; flex-direction: column;
            transform: scale(0.9); opacity: 0; pointer-events: none;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }
        #bai-panel.open { transform: scale(1); opacity: 1; pointer-events: auto; }

        /* Header */
        #bai-panel-header {
            padding: 1rem 1.25rem; display: flex; align-items: center; gap: 10px;
            background: var(--bai-color, #667eea); color: #fff;
        }
        #bai-panel-header .title { font-weight: 600; font-size: 1rem; flex: 1; }
        #bai-panel-header .close-btn { background: none; border: none; color: rgba(255,255,255,0.8); cursor: pointer; font-size: 1.25rem; }

        /* Pre-chat form */
        #bai-prechat {
            padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
        }
        #bai-prechat h3 { color: #fff; font-size: 1rem; margin-bottom: 0.25rem; }
        #bai-prechat input {
            width: 100%; padding: 0.7rem 0.9rem; border-radius: 10px;
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
            color: #fff; font-size: 0.9rem;
        }
        #bai-prechat input::placeholder { color: rgba(255,255,255,0.3); }
        #bai-prechat input:focus { outline:none; border-color: var(--bai-color, #667eea); }
        #bai-start-btn {
            padding: 0.75rem; border-radius: 10px; border: none;
            background: var(--bai-color, #667eea); color: #fff; font-weight: 600;
            cursor: pointer; font-size: 0.95rem; transition: opacity 0.2s;
        }
        #bai-start-btn:hover { opacity: 0.9; }

        /* Messages */
        #bai-messages {
            flex: 1; overflow-y: auto; padding: 1rem; display: none; flex-direction: column; gap: 0.75rem;
            min-height: 260px; max-height: 360px;
        }
        .bai-msg {
            max-width: 80%; padding: 0.7rem 1rem; border-radius: 14px; font-size: 0.9rem;
            line-height: 1.45; animation: bai-fade 0.3s ease;
        }
        @keyframes bai-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .bai-msg.bot { background: rgba(255,255,255,0.06); color: #e0e0e0; align-self: flex-start; border-bottom-left-radius: 4px; }
        .bai-msg.user { background: var(--bai-color, #667eea); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
        .bai-msg.system { background: rgba(245,87,108,0.12); color: #f5576c; align-self: center; font-size: 0.8rem; border-radius: 8px; }

        .bai-typing { display: flex; gap: 4px; align-self: flex-start; padding: 0.6rem 1rem; }
        .bai-typing span { width: 6px; height: 6px; background: rgba(255,255,255,0.3); border-radius: 50%; animation: bai-bounce 1.4s infinite ease-in-out; }
        .bai-typing span:nth-child(2) { animation-delay: 0.2s; }
        .bai-typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bai-bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }

        /* Input */
        #bai-input-area {
            padding: 0.75rem; border-top: 1px solid rgba(255,255,255,0.06);
            display: none; gap: 0.5rem; align-items: center;
        }
        #bai-input {
            flex: 1; padding: 0.7rem 1rem; border-radius: 12px;
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
            color: #fff; font-size: 0.9rem; outline: none;
        }
        #bai-input:focus { border-color: var(--bai-color, #667eea); }
        #bai-send-btn {
            width: 38px; height: 38px; border-radius: 50%; border: none;
            background: var(--bai-color, #667eea); color: #fff; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: transform 0.2s;
        }
        #bai-send-btn:hover { transform: scale(1.1); }
        #bai-send-btn svg { width: 18px; height: 18px; }

        @media (max-width: 480px) {
            #bai-panel { width: calc(100vw - 32px); ${POSITION === 'bottom-left' ? 'left: 16px;' : 'right: 16px;'} bottom: 80px; max-height: 70vh; }
        }
    `;
    document.head.appendChild(style);

    // ── Build DOM ──────────────────────────────────────────────────
    const root = document.createElement('div');
    root.id = 'bai-widget-root';
    root.innerHTML = `
        <div id="bai-bubble">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
        </div>
        <div id="bai-panel">
            <div id="bai-panel-header">
                <span class="title">Chat Support</span>
                <button class="close-btn" id="bai-close">&times;</button>
            </div>
            <div id="bai-prechat">
                <h3>Welcome! 👋</h3>
                <input type="text" id="bai-name" placeholder="Your name" />
                <input type="email" id="bai-email" placeholder="Email (optional)" />
                <button id="bai-start-btn">Start Chat</button>
            </div>
            <div id="bai-messages"></div>
            <div id="bai-input-area">
                <input type="text" id="bai-input" placeholder="Type a message…" />
                <button id="bai-send-btn">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(root);

    // ── Element references ─────────────────────────────────────────
    const bubble    = document.getElementById('bai-bubble');
    const panel     = document.getElementById('bai-panel');
    const closeBtn  = document.getElementById('bai-close');
    const prechat   = document.getElementById('bai-prechat');
    const messages  = document.getElementById('bai-messages');
    const inputArea = document.getElementById('bai-input-area');
    const input     = document.getElementById('bai-input');
    const sendBtn   = document.getElementById('bai-send-btn');
    const startBtn  = document.getElementById('bai-start-btn');

    // ── Load Config ────────────────────────────────────────────────
    async function loadConfig() {
        try {
            const res = await fetch(`${API_BASE}/api/widget/config`, {
                headers: { 'X-Widget-Key': API_KEY }
            });
            if (res.ok) {
                config = await res.json();
                applyConfig();
            }
        } catch (e) {
            console.warn('[Behavioral AI] Could not load widget config:', e);
        }
    }

    function applyConfig() {
        const color = config.theme_color || '#667eea';
        root.style.setProperty('--bai-color', color);
        if (config.bot_name) {
            panel.querySelector('.title').textContent = config.bot_name;
        }
        if (config.welcome_message) {
            prechat.querySelector('h3').textContent = config.welcome_message;
        }
    }

    // ── Toggle Panel ───────────────────────────────────────────────
    bubble.addEventListener('click', () => { isOpen = !isOpen; panel.classList.toggle('open', isOpen); });
    closeBtn.addEventListener('click', () => { isOpen = false; panel.classList.remove('open'); });

    // ── Start Session ──────────────────────────────────────────────
    startBtn.addEventListener('click', async () => {
        const name  = document.getElementById('bai-name').value.trim();
        const email = document.getElementById('bai-email').value.trim();
        if (!name) { document.getElementById('bai-name').style.borderColor = '#f5576c'; return; }

        startBtn.textContent = 'Starting…';
        startBtn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/api/widget/session/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Widget-Key': API_KEY },
                body: JSON.stringify({ customer_name: name, customer_email: email || null })
            });
            const data = await res.json();
            sessionId = data.session_id;

            prechat.style.display = 'none';
            messages.style.display = 'flex';
            inputArea.style.display = 'flex';

            if (!hasGreeted) {
                addMessage('bot', config.greeting_message || `Hi ${name}! How can I help you today?`);
                hasGreeted = true;
            }
        } catch (e) {
            console.error('[Behavioral AI] Session start failed:', e);
            startBtn.textContent = 'Start Chat';
            startBtn.disabled = false;
        }
    });

    // ── Send Message ───────────────────────────────────────────────
    async function sendMessage() {
        const text = input.value.trim();
        if (!text || !sessionId) return;

        addMessage('user', text);
        input.value = '';
        showTyping();

        try {
            const res = await fetch(`${API_BASE}/api/widget/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Widget-Key': API_KEY },
                body: JSON.stringify({ session_id: sessionId, message: text })
            });
            const data = await res.json();
            hideTyping();
            addMessage('bot', data.response || 'Sorry, I could not process that.');

            if (data.escalated) {
                addMessage('system', '⚡ You have been connected to a human agent.');
            }
        } catch (e) {
            hideTyping();
            addMessage('bot', 'Apologies, something went wrong. Please try again.');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

    // ── Helpers ────────────────────────────────────────────────────
    function addMessage(type, text) {
        const div = document.createElement('div');
        div.className = `bai-msg ${type}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        const t = document.createElement('div');
        t.className = 'bai-typing'; t.id = 'bai-typing-indicator';
        t.innerHTML = '<span></span><span></span><span></span>';
        messages.appendChild(t);
        messages.scrollTop = messages.scrollHeight;
    }
    function hideTyping() {
        const t = document.getElementById('bai-typing-indicator');
        if (t) t.remove();
    }

    // ── Init ───────────────────────────────────────────────────────
    loadConfig();

})();
