/**
 * Pi Touch Optimization
 * =====================
 * Optimizes JavaScript interactions for Raspberry Pi touchscreen.
 * Include this script on Pi devices to improve touch responsiveness.
 */

(function() {
    'use strict';
    
    // Detect if running on Pi (ARM architecture passed from server)
    const isPi = document.body.dataset.platform && 
                 document.body.dataset.platform.includes('arm');
    
    // Also check for touch capability
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    if (!isPi && !isTouchDevice) {
        console.log('Pi touch optimizations skipped (not a touch device)');
        return;
    }
    
    console.log('🍓 Pi touch optimizations enabled');
    
    // ==========================================================================
    // 1. Fast Touch Click - Eliminates 300ms delay
    // ==========================================================================
    
    const touchedElements = new WeakSet();
    const lastTapTime = new WeakMap();
    const DEBOUNCE_MS = 300;
    
    function handleFastTap(element, originalEvent) {
        // Debounce rapid taps
        const now = Date.now();
        const lastTap = lastTapTime.get(element) || 0;
        
        if (now - lastTap < DEBOUNCE_MS) {
            console.log('Tap debounced');
            return false;
        }
        
        lastTapTime.set(element, now);
        
        // Add visual feedback
        element.classList.add('pi-touch-active');
        setTimeout(() => element.classList.remove('pi-touch-active'), 150);
        
        // Trigger click
        if (element.click) {
            element.click();
        } else {
            element.dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            }));
        }
        
        return true;
    }
    
    // Attach fast-tap to interactive elements
    document.addEventListener('touchstart', function(e) {
        const target = e.target.closest('button, a, .menu-item, .btn, .clickable, [onclick]');
        if (target && !touchedElements.has(target)) {
            touchedElements.add(target);
            target.addEventListener('touchend', function onTouchEnd(te) {
                // Only trigger if it's a tap (not a scroll/swipe)
                if (te.changedTouches.length === 1) {
                    const touch = te.changedTouches[0];
                    const dx = Math.abs(touch.clientX - e.touches[0].clientX);
                    const dy = Math.abs(touch.clientY - e.touches[0].clientY);
                    
                    // If finger moved less than 10px, it's a tap
                    if (dx < 10 && dy < 10) {
                        te.preventDefault();
                        handleFastTap(target, te);
                    }
                }
            }, { once: true, passive: false });
        }
    }, { passive: true });
    
    // ==========================================================================
    // 2. Prevent double-tap zoom
    // ==========================================================================
    
    let lastTouchEnd = 0;
    
    document.addEventListener('touchend', function(e) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            e.preventDefault();
        }
        lastTouchEnd = now;
    }, { passive: false });
    
    // ==========================================================================
    // 3. Improve slider/range input handling
    // ==========================================================================
    
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        // Make sliders more touch-friendly
        slider.style.height = '40px';
        slider.style.cursor = 'pointer';
        
        // Track touch on slider
        let isSliding = false;
        
        slider.addEventListener('touchstart', function(e) {
            isSliding = true;
            updateSliderFromTouch(slider, e.touches[0]);
        }, { passive: true });
        
        slider.addEventListener('touchmove', function(e) {
            if (isSliding) {
                e.preventDefault();
                updateSliderFromTouch(slider, e.touches[0]);
            }
        }, { passive: false });
        
        slider.addEventListener('touchend', function() {
            isSliding = false;
        });
    });
    
    function updateSliderFromTouch(slider, touch) {
        const rect = slider.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const percent = Math.max(0, Math.min(1, x / rect.width));
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 100;
        const value = min + percent * (max - min);
        
        slider.value = value;
        slider.dispatchEvent(new Event('input', { bubbles: true }));
    }
    
    // ==========================================================================
    // 4. Smooth scrolling for lists
    // ==========================================================================
    
    document.querySelectorAll('.scrollable, .device-list, .call-list, .places-list, ul, ol').forEach(el => {
        el.style.webkitOverflowScrolling = 'touch';
        el.style.overflowY = 'auto';
    });
    
    // ==========================================================================
    // 5. Input focus improvements
    // ==========================================================================
    
    document.querySelectorAll('input[type="text"], input[type="search"], textarea').forEach(input => {
        // Scroll into view when focused
        input.addEventListener('focus', function() {
            setTimeout(() => {
                this.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        });
        
        // Enlarge on focus for easier typing
        input.addEventListener('focus', function() {
            this.style.fontSize = '18px';
        });
        
        input.addEventListener('blur', function() {
            this.style.fontSize = '';
        });
    });
    
    // ==========================================================================
    // 6. Touch feedback CSS injection
    // ==========================================================================
    
    const touchStyles = document.createElement('style');
    touchStyles.textContent = `
        /* Touch feedback */
        .pi-touch-active {
            transform: scale(0.97) !important;
            opacity: 0.8 !important;
            transition: transform 0.1s, opacity 0.1s !important;
        }
        
        /* Larger touch targets */
        button, .btn, .menu-item, a.button {
            min-height: 48px;
            min-width: 48px;
        }
        
        /* Better focus visibility */
        :focus {
            outline: 3px solid #667eea !important;
            outline-offset: 2px !important;
        }
        
        /* Prevent text selection on touch */
        button, .btn, .menu-item, .clickable {
            -webkit-user-select: none;
            user-select: none;
        }
        
        /* Smooth transitions */
        button, .btn, a {
            transition: transform 0.15s ease, background 0.15s ease;
        }
        
        /* Active states */
        button:active, .btn:active, .menu-item:active {
            transform: scale(0.97);
        }
        
        /* Larger range inputs */
        input[type="range"] {
            height: 40px;
            -webkit-appearance: none;
            appearance: none;
            background: transparent;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            border: 3px solid white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        input[type="range"]::-webkit-slider-runnable-track {
            width: 100%;
            height: 8px;
            background: #ddd;
            border-radius: 4px;
        }
        
        /* Loading spinner */
        .loading-spinner {
            width: 24px;
            height: 24px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: pi-spin 0.8s linear infinite;
        }
        
        @keyframes pi-spin {
            to { transform: rotate(360deg); }
        }
        
        /* Notification improvements */
        #notification-container {
            pointer-events: none;
        }
        
        #notification-container > div {
            pointer-events: auto;
            font-size: 16px;
            padding: 16px 24px;
        }
    `;
    document.head.appendChild(touchStyles);
    
    // ==========================================================================
    // 7. Button debouncing for async actions
    // ==========================================================================
    
    // Wrap fetch to add loading states
    const originalFetch = window.fetch;
    const pendingButtons = new WeakMap();
    
    // Auto-disable buttons during fetch
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('button');
        if (btn && !btn.disabled) {
            // Mark button as pending
            pendingButtons.set(btn, {
                originalText: btn.innerHTML,
                originalDisabled: btn.disabled
            });
        }
    }, { capture: true });
    
    // ==========================================================================
    // 8. Keyboard handling for Pi
    // ==========================================================================
    
    // Hide virtual keyboard when pressing Enter
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
                if (activeEl.type !== 'textarea') {
                    activeEl.blur();
                }
            }
        }
    });
    
    // ==========================================================================
    // 9. Error handling improvements
    // ==========================================================================
    
    // Show user-friendly errors
    window.addEventListener('error', function(e) {
        console.error('Pi Error:', e.message);
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Pi Promise Error:', e.reason);
    });
    
    // ==========================================================================
    // 10. Performance: Reduce animations on Pi
    // ==========================================================================
    
    // Reduce motion for better performance on Pi
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || isPi) {
        const motionStyles = document.createElement('style');
        motionStyles.textContent = `
            *, *::before, *::after {
                animation-duration: 0.1s !important;
                transition-duration: 0.1s !important;
            }
        `;
        document.head.appendChild(motionStyles);
    }
    
    // Log initialization complete
    console.log('✅ Pi touch optimizations loaded');
    
})();

