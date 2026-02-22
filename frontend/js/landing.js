/**
 * =========================================================
 * BEHAVIORAL AGENTIC AI - Landing Page JavaScript
 * =========================================================
 */

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', () => {
    initSmoothScroll();
    initNavbarScroll();
    initAnimations();
});

/**
 * Smooth scrolling for anchor links
 */
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href === '#') return;

            e.preventDefault();
            const target = document.querySelector(href);

            if (target) {
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/**
 * Navbar background change on scroll
 */
function initNavbarScroll() {
    const nav = document.querySelector('.landing-nav');

    if (!nav) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
}

/**
 * Intersection Observer for scroll animations
 */
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements with animation classes
    const animatedElements = document.querySelectorAll(
        '.feature-card, .lang-card, .hero-stat'
    );

    animatedElements.forEach(el => {
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });
}

/**
 * Add CSS for animations
 */
const animationStyles = document.createElement('style');
animationStyles.textContent = `
    .animate-on-scroll {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.6s ease-out, transform 0.6s ease-out;
    }
    
    .animate-on-scroll.visible {
        opacity: 1;
        transform: translateY(0);
    }
    
    .landing-nav.scrolled {
        background: rgba(10, 10, 15, 0.95);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    /* Stagger children animations */
    .features-grid .feature-card:nth-child(1) { transition-delay: 0s; }
    .features-grid .feature-card:nth-child(2) { transition-delay: 0.1s; }
    .features-grid .feature-card:nth-child(3) { transition-delay: 0.2s; }
    .features-grid .feature-card:nth-child(4) { transition-delay: 0.3s; }
    
    .process-steps .process-step:nth-child(1) { transition-delay: 0s; }
    .process-steps .process-step:nth-child(2) { transition-delay: 0.1s; }
    .process-steps .process-step:nth-child(3) { transition-delay: 0.2s; }
    .process-steps .process-step:nth-child(4) { transition-delay: 0.3s; }
    .process-steps .process-step:nth-child(5) { transition-delay: 0.4s; }
    
    .languages-grid .language-item:nth-child(1) { transition-delay: 0s; }
    .languages-grid .language-item:nth-child(2) { transition-delay: 0.05s; }
    .languages-grid .language-item:nth-child(3) { transition-delay: 0.1s; }
    .languages-grid .language-item:nth-child(4) { transition-delay: 0.15s; }
    .languages-grid .language-item:nth-child(5) { transition-delay: 0.2s; }
    .languages-grid .language-item:nth-child(6) { transition-delay: 0.25s; }
    .languages-grid .language-item:nth-child(7) { transition-delay: 0.3s; }
    .languages-grid .language-item:nth-child(8) { transition-delay: 0.35s; }
    .languages-grid .language-item:nth-child(9) { transition-delay: 0.4s; }
    .languages-grid .language-item:nth-child(10) { transition-delay: 0.45s; }
`;
document.head.appendChild(animationStyles);

/**
 * Typing effect for demo messages (optional enhancement)
 */
function typeText(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';

    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }

    type();
}

/**
 * Counter animation for stats
 */
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    function update() {
        current += increment;
        if (current < target) {
            element.textContent = Math.floor(current);
            requestAnimationFrame(update);
        } else {
            element.textContent = target;
        }
    }

    update();
}

// Export for potential use
window.BehavioralAI = {
    typeText,
    animateCounter
};
