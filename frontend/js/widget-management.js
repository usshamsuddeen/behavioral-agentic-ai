/**
 * Widget Management Page — FR-3.5
 * Handles widget config CRUD, live preview, embed code, and API key management.
 */

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════
let widgetConfig = null;
let embedCode = '';

// ═══════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    loadWidgetConfig();
    loadWidgetAnalytics();

    // Live preview updates
    document.getElementById('themeColor')?.addEventListener('input', updatePreview);
    document.getElementById('themeColorHex')?.addEventListener('input', (e) => {
        const hex = e.target.value;
        if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
            document.getElementById('themeColor').value = hex;
            updatePreview();
        }
    });
    document.getElementById('botName')?.addEventListener('input', updatePreview);
    document.getElementById('welcomeMessage')?.addEventListener('input', updatePreview);
    document.getElementById('placeholderText')?.addEventListener('input', updatePreview);
    document.getElementById('showBranding')?.addEventListener('change', updatePreview);
    document.getElementById('widgetPosition')?.addEventListener('change', updatePreview);
});


// ═══════════════════════════════════════════════════════════════════
// WIDGET ANALYTICS (FR-3.5.6)
// ═══════════════════════════════════════════════════════════════════
async function loadWidgetAnalytics() {
    try {
        const data = await API.getWidgetAnalytics();

        // Update UI
        document.getElementById('totalLoads').textContent = (data.total_loads || 0).toLocaleString();
        document.getElementById('conversationsStarted').textContent = (data.conversations_started || 0).toLocaleString();
        document.getElementById('avgSessionDuration').textContent = formatDuration(data.avg_session_duration || 0);
    } catch (error) {
        console.error('Failed to load widget analytics:', error);
        // Keep placeholders on error
        document.getElementById('totalLoads').textContent = '--';
        document.getElementById('conversationsStarted').textContent = '--';
        document.getElementById('avgSessionDuration').textContent = '--';
    }
}

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}


// ═══════════════════════════════════════════════════════════════════
// LOAD CONFIG
// ═══════════════════════════════════════════════════════════════════
async function loadWidgetConfig() {
    try {
        widgetConfig = await API.getWidgetConfig();
        if (!widgetConfig) return;

        // Populate form fields
        document.getElementById('themeColor').value = widgetConfig.theme_color || '#6366f1';
        document.getElementById('themeColorHex').value = widgetConfig.theme_color || '#6366f1';
        document.getElementById('widgetPosition').value = widgetConfig.position || 'bottom-right';
        document.getElementById('botName').value = widgetConfig.bot_name || 'AI Assistant';
        document.getElementById('welcomeMessage').value = widgetConfig.welcome_message || 'Hello! How can I help?';
        document.getElementById('placeholderText').value = widgetConfig.placeholder_text || 'Type your message...';
        document.getElementById('showBranding').checked = widgetConfig.show_branding !== false;
        document.getElementById('preChatForm').checked = !!widgetConfig.pre_chat_form_enabled;

        // Update status
        updateWidgetStatus(widgetConfig.is_active);

        // Set embed code
        embedCode = widgetConfig.embed_code || '';
        document.getElementById('embedCodeBlock').textContent = embedCode;

        // API Key
        document.getElementById('apiKeyDisplay').textContent = widgetConfig.api_key || '—';

        // Update preview
        updatePreview();
    } catch (e) {
        console.error('Failed to load widget config:', e);
        showToast('Failed to load widget configuration', 'error');
    }
}


// ═══════════════════════════════════════════════════════════════════
// SAVE CONFIG
// ═══════════════════════════════════════════════════════════════════
async function saveWidgetConfig() {
    try {
        const data = {
            theme_color: document.getElementById('themeColor').value,
            position: document.getElementById('widgetPosition').value,
            bot_name: document.getElementById('botName').value,
            welcome_message: document.getElementById('welcomeMessage').value,
            placeholder_text: document.getElementById('placeholderText').value,
            show_branding: document.getElementById('showBranding').checked,
            pre_chat_form_enabled: document.getElementById('preChatForm').checked
        };

        await API.updateWidgetConfig(data);

        showToast('Widget configuration saved successfully!', 'success');
    } catch (e) {
        console.error('Failed to save widget config:', e);
        showToast('Failed to save configuration: ' + e.message, 'error');
    }
}
window.saveWidgetConfig = saveWidgetConfig;


// ═══════════════════════════════════════════════════════════════════
// TOGGLE WIDGET
// ═══════════════════════════════════════════════════════════════════
async function toggleWidget() {
    try {
        const result = await API.toggleWidget();
        if (!result) return;

        updateWidgetStatus(result.is_active);
        showToast(result.message, 'success');
    } catch (e) {
        showToast('Failed to toggle widget: ' + e.message, 'error');
    }
}
window.toggleWidget = toggleWidget;

function updateWidgetStatus(isActive) {
    const dot = document.getElementById('widgetStatusDot');
    const label = document.getElementById('widgetStatusLabel');
    const desc = document.getElementById('widgetStatusDesc');
    const btn = document.getElementById('widgetToggleBtn');

    if (isActive) {
        dot.classList.add('active');
        label.textContent = 'Widget Active';
        desc.textContent = 'Your chat widget is live and accepting customer conversations.';
        btn.textContent = 'Disable Widget';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
    } else {
        dot.classList.remove('active');
        label.textContent = 'Widget Inactive';
        desc.textContent = 'Enable the widget to start receiving customer conversations.';
        btn.textContent = 'Enable Widget';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
    }
}


// ═══════════════════════════════════════════════════════════════════
// LIVE PREVIEW
// ═══════════════════════════════════════════════════════════════════
function updatePreview() {
    const color = document.getElementById('themeColor')?.value || '#6366f1';
    const botName = document.getElementById('botName')?.value || 'AI Assistant';
    const welcome = document.getElementById('welcomeMessage')?.value || 'Hello!';
    const placeholder = document.getElementById('placeholderText')?.value || 'Type your message...';
    const showBranding = document.getElementById('showBranding')?.checked;
    const position = document.getElementById('widgetPosition')?.value || 'bottom-right';

    // Update hex display
    document.getElementById('themeColorHex').value = color;

    // Update header
    const header = document.getElementById('wpHeader');
    if (header) header.style.background = color;

    // Update bot name
    const nameEl = document.getElementById('wpBotName');
    if (nameEl) nameEl.textContent = botName;

    // Update welcome
    const welcomeEl = document.getElementById('wpWelcome');
    if (welcomeEl) welcomeEl.textContent = welcome;

    // Update placeholder
    const inputEl = document.getElementById('wpInput');
    if (inputEl) inputEl.placeholder = placeholder;

    // Update bubble
    const bubble = document.getElementById('wpBubble');
    if (bubble) bubble.style.background = color;

    // Update send button
    const send = document.getElementById('wpSend');
    if (send) send.style.background = color;

    // Update customer message bubble
    const custMsg = document.getElementById('wpCustomerMsg');
    if (custMsg) custMsg.style.background = color;

    // Update branding
    const branding = document.getElementById('wpBranding');
    if (branding) branding.style.display = showBranding ? 'block' : 'none';

    // Position preview
    const frame = document.querySelector('.widget-preview-frame');
    const bubbleEl = document.querySelector('.wp-bubble');
    if (frame && bubbleEl) {
        if (position === 'bottom-left') {
            frame.style.right = 'auto';
            frame.style.left = '20px';
            bubbleEl.style.right = 'auto';
            bubbleEl.style.left = '20px';
        } else {
            frame.style.left = 'auto';
            frame.style.right = '20px';
            bubbleEl.style.left = 'auto';
            bubbleEl.style.right = '20px';
        }
    }
}


// ═══════════════════════════════════════════════════════════════════
// COPY & KEY MANAGEMENT
// ═══════════════════════════════════════════════════════════════════
async function copyEmbedCode() {
    try {
        await navigator.clipboard.writeText(embedCode);
        showToast('Embed code copied to clipboard!', 'success');
    } catch {
        showToast('Failed to copy — please select and copy manually', 'error');
    }
}
window.copyEmbedCode = copyEmbedCode;

async function copyApiKey() {
    const key = document.getElementById('apiKeyDisplay')?.textContent || '';
    try {
        await navigator.clipboard.writeText(key);
        showToast('API key copied to clipboard!', 'success');
    } catch {
        showToast('Failed to copy', 'error');
    }
}
window.copyApiKey = copyApiKey;

async function regenerateApiKey() {
    if (!confirm('Are you sure you want to regenerate the API key? The old key will stop working immediately.')) return;

    try {
        const result = await API.regenerateApiKey();
        if (!result) return;

        document.getElementById('apiKeyDisplay').textContent = result.new_key;
        showToast('API key regenerated. Update your embed code.', 'success');

        // Reload to get new embed code
        await loadWidgetConfig();
    } catch (e) {
        showToast('Failed to regenerate key: ' + e.message, 'error');
    }
}
window.regenerateApiKey = regenerateApiKey;


// ═══════════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════════
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => { toast.classList.remove('show'); }, 3000);
}
