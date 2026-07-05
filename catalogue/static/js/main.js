/**
 * ShopFlow Electronics - Main JavaScript
 * Handles category filtering, tooltips, and interactive features
 */

(function() {
    'use strict';

    // ==========================================================================
    // Initialize Bootstrap Tooltips
    // ==========================================================================
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // ==========================================================================
    // Category Filtering
    // ==========================================================================
    function initCategoryFilters() {
        const filterButtons = document.querySelectorAll('.category-filter');
        const productItems = document.querySelectorAll('.product-item');

        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                const category = this.dataset.category;

                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Filter products with animation
                productItems.forEach((item, index) => {
                    const itemCategory = item.dataset.category;

                    if (category === 'all' || itemCategory === category) {
                        item.style.display = 'block';
                        // Stagger animation
                        setTimeout(() => {
                            item.style.opacity = '1';
                            item.style.transform = 'translateY(0)';
                        }, index * 30);
                    } else {
                        item.style.opacity = '0';
                        item.style.transform = 'translateY(20px)';
                        setTimeout(() => {
                            item.style.display = 'none';
                        }, 300);
                    }
                });
            });
        });
    }

    // ==========================================================================
    // Add to Cart Buttons (Visual Feedback)
    // ==========================================================================
    function initAddToCart() {
        const addToCartButtons = document.querySelectorAll('.btn-add-cart');

        addToCartButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const productId = this.dataset.productId;
                const originalHtml = this.innerHTML;

                // Visual feedback
                this.innerHTML = '<i class="bi bi-check-lg me-1"></i>Added!';
                this.classList.remove('btn-primary');
                this.classList.add('btn-success');
                this.disabled = true;

                // Show toast notification
                showToast(`Product ${productId} added to cart!`, 'success');

                // Reset after 2 seconds
                setTimeout(() => {
                    this.innerHTML = originalHtml;
                    this.classList.remove('btn-success');
                    this.classList.add('btn-primary');
                    this.disabled = false;
                }, 2000);
            });
        });
    }

    // ==========================================================================
    // Toast Notifications
    // ==========================================================================
    function showToast(message, type = 'info') {
        // Remove existing toasts
        const existingToast = document.querySelector('.shopflow-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `shopflow-toast toast align-items-center text-white bg-${type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.style.cssText = 'position: fixed; bottom: 2rem; right: 2rem; z-index: 9999; min-width: 280px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);';

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        document.body.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    // ==========================================================================
    // Newsletter Form (Visual Only)
    // ==========================================================================
    function initNewsletterForm() {
        const form = document.getElementById('newsletter-form');
        if (!form) return;

        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value.trim();

            if (!email) {
                showToast('Please enter your email address', 'warning');
                return;
            }

            if (!isValidEmail(email)) {
                showToast('Please enter a valid email address', 'warning');
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Subscribing...';
            submitBtn.disabled = true;

            // Simulate API call
            setTimeout(() => {
                showToast('Thanks for subscribing!', 'success');
                emailInput.value = '';
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    // ==========================================================================
    // Smooth Scroll for Anchor Links
    // ==========================================================================
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;

                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    const navbarHeight = document.querySelector('.navbar').offsetHeight;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navbarHeight;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Update URL without jumping
                    history.pushState(null, null, targetId);
                }
            });
        });
    }

    // ==========================================================================
    // Navbar Scroll Effect
    // ==========================================================================
    function initNavbarScroll() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        let lastScroll = 0;

        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;

            if (currentScroll > 100) {
                navbar.classList.add('shadow-md');
                navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.98)';
            } else {
                navbar.classList.remove('shadow-md');
                navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
            }

            lastScroll = currentScroll;
        }, { passive: true });
    }

    // ==========================================================================
    // Product Card Hover Enhancement (Touch Devices)
    // ==========================================================================
    function initTouchSupport() {
        const productCards = document.querySelectorAll('.product-card');

        productCards.forEach(card => {
            card.addEventListener('touchstart', function() {
                // Trigger hover state on touch
                this.classList.add('touch-active');
            }, { passive: true });

            card.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 300);
            }, { passive: true });
        });
    }

    // ==========================================================================
    // Intersection Observer for Animations
    // ==========================================================================
    function initScrollAnimations() {
        if (!('IntersectionObserver' in window)) return;

        const observerOptions = {
            root: null,
            rootMargin: '0px 0px -50px 0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe elements
        document.querySelectorAll('.trust-item, .category-card, .product-card').forEach(el => {
            observer.observe(el);
        });
    }

    // ==========================================================================
    // Search Input Enhancement
    // ==========================================================================
    function initSearchEnhancement() {
        const searchInput = document.querySelector('.search-wrapper .form-control');
        if (!searchInput) return;

        searchInput.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });

        searchInput.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });

        // Clear button on input
        searchInput.addEventListener('input', function() {
            const clearBtn = this.parentElement.querySelector('.search-clear');
            if (this.value.length > 0) {
                if (!clearBtn) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'btn btn-link text-muted p-0 search-clear';
                    btn.innerHTML = '<i class="bi bi-x-circle fs-5"></i>';
                    btn.setAttribute('aria-label', 'Clear search');
                    btn.addEventListener('click', () => {
                        this.value = '';
                        this.focus();
                        btn.remove();
                    });
                    this.parentElement.querySelector('.input-group-text:last-child').before(btn);
                }
            } else if (clearBtn) {
                clearBtn.remove();
            }
        });
    }

    // ==========================================================================
    // Keyboard Navigation Enhancement
    // ==========================================================================
    function initKeyboardNavigation() {
        document.addEventListener('keydown', function(e) {
            // Escape key closes mobile navbar
            if (e.key === 'Escape') {
                const navbarCollapse = document.querySelector('.navbar-collapse.show');
                if (navbarCollapse) {
                    const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                    if (bsCollapse) bsCollapse.hide();
                }

                // Clear search
                const searchInput = document.querySelector('.search-wrapper .form-control');
                if (searchInput === document.activeElement) {
                    searchInput.blur();
                }
            }
        });
    }

    // ==========================================================================
    // Initialize All
    // ==========================================================================
    document.addEventListener('DOMContentLoaded', function() {
        initTooltips();
        initCategoryFilters();
        initAddToCart();
        initNewsletterForm();
        initSmoothScroll();
        initNavbarScroll();
        initTouchSupport();
        initScrollAnimations();
        initSearchEnhancement();
        initKeyboardNavigation();

        console.log('ShopFlow Electronics initialized');
    });

    // ==========================================================================
    // Export for testing (if needed)
    // ==========================================================================
    window.ShopFlow = {
        showToast,
        isValidEmail
    };

})();