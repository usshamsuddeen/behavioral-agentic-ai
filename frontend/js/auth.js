/**
 * Authentication Helper Module
 * Handles JWT tokens, auth state, and protected route checks
 */

const Auth = {
    // API Base URL
    API_BASE: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? 'http://localhost:8000'
        : window.location.origin,

    /**
     * Get stored access token
     */
    getAccessToken() {
        return localStorage.getItem('access_token');
    },

    /**
     * Get stored refresh token
     */
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    /**
     * Get stored user data
     */
    getUser() {
        const userData = localStorage.getItem('user');
        return userData ? JSON.parse(userData) : null;
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.getAccessToken();
    },

    /**
     * Store auth tokens and user data
     */
    setAuth(accessToken, refreshToken, user) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        localStorage.setItem('user', JSON.stringify(user));
    },

    /**
     * Clear all auth data (logout)
     */
    clearAuth() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },

    /**
     * Get Authorization header for API requests
     */
    getAuthHeader() {
        const token = this.getAccessToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },

    /**
     * Make authenticated API request
     */
    async authFetch(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...this.getAuthHeader(),
            ...options.headers
        };

        const response = await fetch(`${this.API_BASE}${url}`, {
            ...options,
            headers
        });

        // Handle token expiration
        if (response.status === 401) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                // Retry with new token
                headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
                return fetch(`${this.API_BASE}${url}`, {
                    ...options,
                    headers
                });
            } else {
                // Refresh failed, redirect to login
                this.redirectToLogin();
                throw new Error('Session expired');
            }
        }

        return response;
    },

    /**
     * Refresh the access token using refresh token
     */
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) return false;

        try {
            const response = await fetch(`${this.API_BASE}/api/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh_token: refreshToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.setAuth(data.access_token, data.refresh_token, data.user);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }

        return false;
    },

    /**
     * Verify current token is valid
     */
    async verifyToken() {
        const token = this.getAccessToken();
        if (!token) return false;

        try {
            const response = await fetch(`${this.API_BASE}/api/auth/status`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    },

    /**
     * Logout user
     */
    async logout() {
        try {
            await this.authFetch('/api/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout request failed:', error);
        }
        this.clearAuth();
        this.redirectToLogin();
    },

    /**
     * Redirect to login page
     */
    redirectToLogin() {
        const currentPath = window.location.pathname;
        // Don't redirect if already on auth pages
        if (!currentPath.includes('login') && !currentPath.includes('signup')) {
            window.location.href = '/pages/login.html';
        }
    },

    /**
     * Redirect to dashboard or onboarding
     */
    redirectToDashboard() {
        const user = this.getUser();
        if (user && !user.onboarding_completed) {
            window.location.href = '/pages/onboarding.html';
        } else {
            window.location.href = '/pages/client-dashboard.html';
        }
    },

    /**
     * Check auth and redirect if not authenticated
     * Call this at the start of protected pages
     */
    async requireAuth() {
        if (!this.isAuthenticated()) {
            this.redirectToLogin();
            return false;
        }

        const valid = await this.verifyToken();
        if (!valid) {
            // Try refresh
            const refreshed = await this.refreshAccessToken();
            if (!refreshed) {
                this.clearAuth();
                this.redirectToLogin();
                return false;
            }
        }

        return true;
    },

    /**
     * Initialize auth check on page load
     * Use this for protected pages
     */
    initProtectedPage() {
        document.addEventListener('DOMContentLoaded', async () => {
            const isValid = await this.requireAuth();
            if (!isValid) return;

            // Update UI with user info
            this.updateUserUI();

            // Dispatch event for page-specific initialization
            window.dispatchEvent(new CustomEvent('authReady', { detail: this.getUser() }));
        });
    },

    /**
     * Update UI elements with user info
     */
    updateUserUI() {
        const user = this.getUser();
        if (!user) return;

        // Update user name displays
        document.querySelectorAll('.user-name, .sidebar-user-name').forEach(el => {
            el.textContent = user.name || user.full_name || user.email.split('@')[0];
        });

        // Update user role displays
        document.querySelectorAll('.user-role, .sidebar-user-role').forEach(el => {
            el.textContent = user.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'User';
        });

        // Update avatars
        document.querySelectorAll('.avatar, .user-avatar').forEach(el => {
            el.textContent = user.initials || user.avatar_initials || user.email.substring(0, 2).toUpperCase();
        });

        // Setup logout handlers
        document.querySelectorAll('.logout-btn, [data-logout]').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        });
    }
};

// Export for use in other scripts
window.Auth = Auth;
