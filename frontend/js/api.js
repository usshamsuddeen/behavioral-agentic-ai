/**
 * Behavioral Agentic AI - API Service
 * Handles all communication with the FastAPI backend
 * All requests are JWT-authenticated via Auth module.
 */

const API = {
    // Backend URL - auto-detects production vs local
    BASE_URL: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? 'http://localhost:8000/api'
        : window.location.origin + '/api',

    /**
     * Make authenticated API request with error handling.
     * JWT token is injected automatically from Auth.getAuthHeader().
     */
    async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;

        // Merge auth headers — Auth module provides Bearer token
        const authHeaders = (typeof Auth !== 'undefined') ? Auth.getAuthHeader() : {};

        const mergedHeaders = {
            'Content-Type': 'application/json',
            ...authHeaders,
            ...(options.headers || {}),
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers: mergedHeaders,
            });

            // Handle 401 — token expired or invalid
            if (response.status === 401) {
                if (typeof Auth !== 'undefined') {
                    const refreshed = await Auth.refreshAccessToken();
                    if (refreshed) {
                        // Retry with new token
                        mergedHeaders['Authorization'] = `Bearer ${Auth.getAccessToken()}`;
                        const retryResponse = await fetch(url, { ...options, headers: mergedHeaders });
                        if (!retryResponse.ok) {
                            throw new Error(`API Error: ${retryResponse.status} ${retryResponse.statusText}`);
                        }
                        return await retryResponse.json();
                    } else {
                        Auth.redirectToLogin();
                        throw new Error('Session expired');
                    }
                }
            }

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Request Failed: ${endpoint}`, error);
            throw error;
        }
    },

    /**
     * Make a request that sends FormData (file uploads).
     * Does NOT set Content-Type (browser sets multipart boundary).
     */
    async upload(endpoint, formData) {
        const url = `${this.BASE_URL}${endpoint}`;
        const authHeaders = (typeof Auth !== 'undefined') ? Auth.getAuthHeader() : {};

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { ...authHeaders },
                body: formData,
            });

            // Handle auth expiry
            if (response.status === 401) {
                if (typeof Auth !== 'undefined') {
                    const refreshed = await Auth.refreshAccessToken();
                    if (refreshed) {
                        const retryResp = await fetch(url, {
                            method: 'POST',
                            headers: { ...Auth.getAuthHeader() },
                            body: formData,
                        });
                        if (!retryResp.ok) {
                            const errData = await retryResp.json().catch(() => ({}));
                            throw new Error(errData.detail || errData.error || `Upload failed (${retryResp.status})`);
                        }
                        return await retryResp.json();
                    } else {
                        Auth.redirectToLogin();
                        throw new Error('Session expired');
                    }
                }
                Auth.redirectToLogin();
                throw new Error('Session expired');
            }

            if (!response.ok) {
                // Parse the FastAPI error body for a human-readable message
                let errMsg = `Upload failed (${response.status})`;
                try {
                    const errData = await response.json();
                    errMsg = errData.detail || errData.error || errData.message || errMsg;
                    // FastAPI validation errors come as [{loc, msg, type}]
                    if (Array.isArray(errMsg)) {
                        errMsg = errMsg.map(e => e.msg || JSON.stringify(e)).join('; ');
                    }
                } catch (_) { /* keep default msg */ }
                throw new Error(errMsg);
            }

            return await response.json();
        } catch (error) {
            console.error(`Upload Failed: ${endpoint}`, error);
            throw error;
        }
    },

    // ==========================================
    // HEALTH & STATUS
    // ==========================================

    async healthCheck() {
        // Health endpoint is unauthenticated — skip auth header
        try {
            const response = await fetch(`${this.BASE_URL}/health`);
            if (!response.ok) throw new Error('Health check failed');
            return await response.json();
        } catch (error) {
            throw error;
        }
    },

    // ==========================================
    // CONVERSATIONS
    // ==========================================

    /**
     * Get all conversations (tenant-scoped)
     * @param {string} status - Filter by status (active, pending, escalated, resolved)
     * @param {number} limit - Max results
     * @param {string} search - Search query
     */
    async getConversations(status = null, limit = 20, search = null) {
        let endpoint = `/conversations?limit=${limit}`;
        if (status) endpoint += `&status=${status}`;
        if (search) endpoint += `&search=${encodeURIComponent(search)}`;
        return this.request(endpoint);
    },

    /**
     * Get single conversation with messages
     * @param {number} id - Conversation ID
     */
    async getConversation(id) {
        return this.request(`/conversations/${id}`);
    },

    /**
     * Create new conversation
     */
    async createConversation(customerName, customerEmail, language = 'en') {
        return this.request(`/conversations?customer_name=${encodeURIComponent(customerName)}&customer_email=${encodeURIComponent(customerEmail)}&language=${language}`, {
            method: 'POST'
        });
    },

    /**
     * Escalate conversation
     */
    async escalateConversation(id, reason = 'Manual escalation') {
        return this.request(`/conversations/${id}/escalate`, {
            method: 'PUT',
            body: JSON.stringify({ reason })
        });
    },

    /**
     * Resolve conversation
     */
    async resolveConversation(id) {
        return this.request(`/conversations/${id}/resolve`, {
            method: 'PUT'
        });
    },

    /**
     * Agent takeover (FR-3.2.5)
     */
    async takeoverConversation(id) {
        return this.request(`/conversations/${id}/takeover`, {
            method: 'POST'
        });
    },

    /**
     * Agent respond to conversation (FR-3.2.7)
     */
    async respondToConversation(id, content) {
        return this.request(`/conversations/${id}/respond`, {
            method: 'POST',
            body: JSON.stringify({ content })
        });
    },

    // ==========================================
    // MESSAGES
    // ==========================================

    /**
     * Send a message (JSON body, matching backend SendMessageRequest schema)
     * @param {number} conversationId - Conversation ID
     * @param {string} content - Message content
     * @param {string} senderType - customer, agent, or ai
     * @param {string} senderName - Sender name
     */
    async sendMessage(conversationId, content, senderType = 'customer', senderName = null) {
        const body = { content, sender_type: senderType };
        if (senderName) body.sender_name = senderName;

        return this.request(`/conversations/${conversationId}/messages`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    /**
     * Get messages for conversation
     * @param {number} conversationId - Conversation ID
     */
    async getMessages(conversationId) {
        return this.request(`/conversations/${conversationId}/messages`);
    },

    // ==========================================
    // SENTIMENT ANALYSIS
    // ==========================================

    async analyzeSentiment(text) {
        return this.request('/analyze/sentiment', {
            method: 'POST',
            body: JSON.stringify({ text })
        });
    },

    async detectLanguage(text) {
        return this.request('/analyze/language', {
            method: 'POST',
            body: JSON.stringify({ text })
        });
    },

    async fullAnalysis(text) {
        return this.request('/analyze/full', {
            method: 'POST',
            body: JSON.stringify({ text })
        });
    },

    // ==========================================
    // ANALYTICS (Tenant-Scoped)
    // ==========================================

    async getDashboardMetrics() {
        return this.request('/analytics/dashboard');
    },

    async getSentimentTrends(days = 7) {
        return this.request(`/analytics/sentiment-trends?days=${days}`);
    },

    async getHourlyActivity() {
        return this.request('/analytics/hourly-activity');
    },

    async getEscalationTriggers() {
        return this.request('/analytics/escalation-triggers');
    },

    async getSentimentByLanguage() {
        return this.request('/analytics/sentiment-by-language');
    },

    async getComprehensiveAnalytics(days = 7) {
        return this.request(`/analytics/comprehensive?days=${days}`);
    },

    // ==========================================
    // SETTINGS (Tenant-Scoped, FR-3.6)
    // ==========================================

    async getSettings() {
        return this.request('/settings');
    },

    async updateProfile(data) {
        return this.request('/settings/profile', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async updateTenantSettings(data) {
        return this.request('/settings/tenant', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async updatePreferences(data) {
        return this.request('/settings/preferences', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async inviteTeamMember(data) {
        return this.request('/settings/invite-team', {
            method: 'POST',
            body: JSON.stringify({ name: data.name, email: data.email, role: data.role || 'agent' })
        });
    },

    async removeTeamMember(memberId) {
        return this.request(`/settings/team/${memberId}`, {
            method: 'DELETE'
        });
    },

    async regenerateApiKey() {
        return this.request('/settings/regenerate-key', {
            method: 'POST'
        });
    },

    // ==========================================
    // WIDGET CONFIG (Tenant-Scoped, FR-3.5)
    // ==========================================

    async getWidgetConfig() {
        return this.request('/widget/config');
    },

    async updateWidgetConfig(data) {
        return this.request('/widget/config', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async getEmbedCode() {
        return this.request('/widget/embed-code');
    },

    async toggleWidget() {
        return this.request('/widget/toggle', {
            method: 'POST'
        });
    },

    async getWidgetAnalytics() {
        return this.request('/widget/analytics');
    },

    // ==========================================
    // ORDERS (V4 NEW — Zone 8)
    // ==========================================

    async getOrders(page = 1, limit = 20, search = '', status = '', source = '') {
        let url = `/orders?page=${page}&limit=${limit}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status) url += `&status=${encodeURIComponent(status)}`;
        if (source) url += `&source=${encodeURIComponent(source)}`;
        return this.request(url);
    },

    async getOrderStats() {
        return this.request('/orders/stats');
    },

    async uploadOrderCSV(formData) {
        return this.upload('/orders/upload-csv', formData);
    },

    async simulateOrders(count = 50) {
        return this.request('/orders/simulate', {
            method: 'POST',
            body: JSON.stringify({ count })
        });
    },

    async deleteOrder(id) {
        return this.request(`/orders/${id}`, { method: 'DELETE' });
    },

    async getOrder(orderId) {
        return this.request(`/orders/${encodeURIComponent(orderId)}`);
    },

    // ==========================================
    // PRODUCTS (V4 NEW — Zone 3)
    // ==========================================

    async getProducts(page = 1, limit = 20, search = '', category = '') {
        let url = `/products?page=${page}&limit=${limit}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        return this.request(url);
    },

    async getProduct(id) {
        return this.request(`/products/${id}`);
    },

    async createProduct(data) {
        return this.request('/products', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateProduct(id, data) {
        return this.request(`/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteProduct(id) {
        return this.request(`/products/${id}`, { method: 'DELETE' });
    },

    async uploadProductCSV(formData) {
        return this.upload('/products/upload-csv', formData);
    },

    // ==========================================
    // KNOWLEDGE BASE (Tenant-Scoped, FR-7.3)
    // ==========================================

    async searchKnowledge(query, topK = 5) {
        return this.request('/knowledge/search', {
            method: 'POST',
            body: JSON.stringify({ query, top_k: topK })
        });
    },

    async getKnowledgeStats() {
        return this.request('/knowledge/stats');
    },

    async getKnowledgeDocuments() {
        return this.request('/knowledge/documents');
    },

    async deleteKnowledgeDocument(documentId) {
        return this.request(`/knowledge/document/${documentId}`, {
            method: 'DELETE'
        });
    },

    async deleteAllKnowledge() {
        return this.request('/knowledge?confirm=true', {
            method: 'DELETE'
        });
    },

    async addKnowledgeText(text, source = 'manual_entry', docType = 'general', category = 'general') {
        return this.request('/knowledge/text', {
            method: 'POST',
            body: JSON.stringify({ text, source, doc_type: docType, category })
        });
    },

    async getKnowledgeDocumentContent(documentId) {
        return this.request(`/knowledge/document/${documentId}/content`);
    },

    async uploadKnowledgeFile(formData) {
        return this.upload('/knowledge/upload', formData);
    },

    // ==========================================
    // AI RESTRICTIONS (stored in tenant.ai_restrictions → LLM system prompt)
    // ==========================================

    async getRestrictions() {
        return this.request('/settings/restrictions');
    },

    async updateRestrictions(text) {
        return this.request('/settings/restrictions', {
            method: 'PUT',
            body: JSON.stringify({ restrictions: text })
        });
    },

    // ==========================================
    // SYNC API (V5 NEW — Real-Time CSV Sync)
    // ==========================================

    async getSyncConfigs() {
        return this.request('/sync/configs');
    },

    async createSyncConfig(data) {
        return this.request('/sync/config', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async deleteSyncConfig(id) {
        return this.request(`/sync/configs/${id}`, { method: 'DELETE' });
    },

    async triggerSync(id) {
        return this.request(`/sync/trigger/${id}`, { method: 'POST' });
    },

    async getSyncStatus(id) {
        return this.request(`/sync/status/${id}`);
    }
};

// ==========================================
// UI HELPER FUNCTIONS
// ==========================================

const UIHelpers = {
    showLoading(elementId) {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerHTML = `
                <div class="loading-state">
                    <div class="loading-spinner"></div>
                    <span>Loading...</span>
                </div>
            `;
        }
    },

    showError(elementId, message = 'Failed to load data') {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerHTML = `
                <div class="error-state">
                    <span class="error-icon">⚠️</span>
                    <span>${message}</span>
                    <button onclick="location.reload()" class="btn btn-sm btn-secondary">Retry</button>
                </div>
            `;
        }
    },

    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },

    getSentimentClass(sentiment) {
        const classes = {
            positive: 'positive',
            neutral: 'neutral',
            negative: 'negative'
        };
        return classes[sentiment] || 'neutral';
    },

    async checkBackendStatus() {
        try {
            await API.healthCheck();
            return true;
        } catch (error) {
            console.warn('Backend not available:', error.message);
            return false;
        }
    }
};

// Export for use in other files
window.API = API;
window.UIHelpers = UIHelpers;

// Check backend on load
document.addEventListener('DOMContentLoaded', async () => {
    const isBackendRunning = await UIHelpers.checkBackendStatus();
    if (!isBackendRunning) {
        console.warn('⚠️ Backend server not running. Using demo data.');
    } else {
        console.log('✅ Backend connected successfully!');
    }
});
