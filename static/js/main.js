/**
 * BetPro - Main JavaScript
 * Handles UI interactions, bet slip, notifications, and AJAX calls.
 */

// ===================================================================
// DOM READY
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initFlashMessages();
    initBetSlip();
    initOddsSelection();
    initNotifications();
    initTooltips();
    initAutoDismiss();
    initMobileMenu();

    // Auto-hide flash messages
    setTimeout(function() {
        document.querySelectorAll('.flash-container .alert').forEach(function(el) {
            var bsAlert = new bootstrap.Alert(el);
            bsAlert.close();
        });
    }, 6000);
});

// ===================================================================
// SIDEBAR
// ===================================================================
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
    document.body.classList.toggle('sidebar-open');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth < 992) {
        sidebar.classList.remove('open');
        document.body.classList.remove('sidebar-open');
    }
}

// ===================================================================
// FLASH MESSAGES
// ===================================================================
function initFlashMessages() {
    document.querySelectorAll('.flash-container .alert').forEach(function(alert) {
        alert.classList.add('animate-slide-right');
    });
}

function initAutoDismiss() {
    document.querySelectorAll('[data-bs-dismiss="alert"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var alert = this.closest('.alert');
            alert.style.transition = 'all 0.3s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
        });
    });
}

// ===================================================================
// BET SLIP
// ===================================================================
let betSlipSelections = [];

function initBetSlip() {
    // Load bet slip from session storage
    try {
        const saved = sessionStorage.getItem('betpro_betslip');
        if (saved) {
            betSlipSelections = JSON.parse(saved);
            updateBetSlipUI();
        }
    } catch(e) {}

    // Close bet slip button
    const closeBtn = document.getElementById('betslipClose');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeBetSlip();
        });
    }

    // Clear bet slip
    const clearBtn = document.getElementById('betslipClear');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            clearBetSlip();
        });
    }
}

function toggleBetSlip() {
    const panel = document.getElementById('betslipPanelInline');
    if (panel) {
        panel.classList.toggle('open');
    }
}

function openBetSlip() {
    const panel = document.getElementById('betslipPanelInline');
    if (panel) panel.classList.add('open');
}

function closeBetSlip() {
    const panel = document.getElementById('betslipPanelInline');
    if (panel) panel.classList.remove('open');
}

function addToBetSlip(matchId, matchName, selectionType, selectionLabel, odds) {
    // Check if same match + selection already exists
    const existingIndex = betSlipSelections.findIndex(
        s => s.match_id === matchId && s.selection_type === selectionType
    );

    if (existingIndex >= 0) {
        // Remove if already selected (toggle)
        betSlipSelections.splice(existingIndex, 1);
        updateOddsButtonState(matchId, selectionType, false);
    } else {
        // Add new selection
        betSlipSelections.push({
            match_id: matchId,
            match_name: matchName,
            selection_type: selectionType,
            selection_label: selectionLabel,
            odds: odds
        });
        updateOddsButtonState(matchId, selectionType, true);
    }

    saveBetSlip();
    updateBetSlipUI();
    openBetSlip();
}

function removeFromBetSlip(index) {
    if (index >= 0 && index < betSlipSelections.length) {
        const sel = betSlipSelections[index];
        updateOddsButtonState(sel.match_id, sel.selection_type, false);
        betSlipSelections.splice(index, 1);
        saveBetSlip();
        updateBetSlipUI();
    }
}

function clearBetSlip() {
    // Reset all odds button states
    betSlipSelections.forEach(function(sel) {
        updateOddsButtonState(sel.match_id, sel.selection_type, false);
    });
    betSlipSelections = [];
    saveBetSlip();
    updateBetSlipUI();
}

function saveBetSlip() {
    try {
        sessionStorage.setItem('betpro_betslip', JSON.stringify(betSlipSelections));
    } catch(e) {}
}

function updateOddsButtonState(matchId, selectionType, selected) {
    const selector = `button[data-match-id="${matchId}"][data-selection-type="${selectionType}"]`;
    document.querySelectorAll(selector).forEach(function(btn) {
        if (selected) {
            btn.classList.add('selected');
            btn.style.borderColor = '#ffd700';
            btn.style.background = 'rgba(255, 215, 0, 0.2)';
        } else {
            btn.classList.remove('selected');
            btn.style.borderColor = '';
            btn.style.background = '';
        }
    });
}

function updateBetSlipUI() {
    const container = document.getElementById('betslipSelections');
    const countEl = document.getElementById('betslipCount');
    const countEl2 = document.getElementById('betslipCount2');
    const totalOddsEl = document.getElementById('betslipTotalOdds');
    const potentialEl = document.getElementById('betslipPotential');
    const stakeInput = document.getElementById('betslipStake');
    const placeBtn = document.getElementById('betslipPlaceBtn');
    const emptyState = document.getElementById('betslipEmpty');
    const selectionsArea = document.getElementById('betslipSelectionsArea');
    const footerEl = document.getElementById('betslipFooter');
    const floatingBadge = document.getElementById('betslipFloatingCount');

    // Update count
    if (countEl) countEl.textContent = betSlipSelections.length;
    if (countEl2) countEl2.textContent = betSlipSelections.length;
    if (floatingBadge) floatingBadge.textContent = betSlipSelections.length;

    // Toggle empty state
    if (betSlipSelections.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
        if (selectionsArea) selectionsArea.style.display = 'none';
        if (footerEl) footerEl.style.display = 'none';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (selectionsArea) selectionsArea.style.display = 'block';
    if (footerEl) footerEl.style.display = 'block';

    // Render selections
    if (container) {
        container.innerHTML = '';
        betSlipSelections.forEach(function(sel, index) {
            const div = document.createElement('div');
            div.className = 'betslip-selection d-flex justify-content-between align-items-center';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <div class="small text-muted">${sel.match_name}</div>
                    <div class="fw-bold small">${sel.selection_label}</div>
                    <div class="text-gold fw-bold" style="font-size: 13px;">@${parseFloat(sel.odds).toFixed(2)}</div>
                </div>
                <button class="btn btn-link text-danger p-1" onclick="removeFromBetSlip(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }

    // Calculate totals
    let totalOdds = 1.0;
    betSlipSelections.forEach(function(sel) {
        totalOdds *= parseFloat(sel.odds) || 1;
    });
    totalOdds = Math.round(totalOdds * 100) / 100;

    if (totalOddsEl) totalOddsEl.textContent = totalOdds.toFixed(2);

    const betType = betSlipSelections.length > 1 ? 'Accumulator' : 'Single';
    document.getElementById('betslipType') && (document.getElementById('betslipType').textContent = betType);

    // Calculate potential on stake input
    if (stakeInput) {
        stakeInput.addEventListener('input', function() {
            calculatePotential();
        });
        calculatePotential();
    }
}

function calculatePotential() {
    const stake = parseFloat(document.getElementById('betslipStake')?.value) || 0;
    const totalOdds = parseFloat(document.getElementById('betslipTotalOdds')?.textContent) || 1;
    const potential = stake * totalOdds;
    const potentialEl = document.getElementById('betslipPotential');
    if (potentialEl) {
        potentialEl.textContent = potential.toFixed(2);
    }
    return potential;
}

// ===================================================================
// ODDS SELECTION
// ===================================================================
function initOddsSelection() {
    document.querySelectorAll('.team-odds').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const matchId = parseInt(this.dataset.matchId);
            const matchName = this.dataset.matchName;
            const selectionType = this.dataset.selectionType;
            const selectionLabel = this.dataset.selectionLabel;
            const odds = parseFloat(this.dataset.odds);

            if (!matchId || !selectionType || !odds) return;
            addToBetSlip(matchId, matchName, selectionType, selectionLabel, odds);
        });
    });
}

// ===================================================================
// PLACE BET
// ===================================================================
function placeBet() {
    const stake = parseFloat(document.getElementById('betslipStake')?.value);
    const useBonus = document.getElementById('betslipUseBonus')?.checked || false;

    if (!stake || stake <= 0) {
        showToast('warning', 'Please enter a valid stake amount.');
        return;
    }

    if (betSlipSelections.length === 0) {
        showToast('warning', 'Your bet slip is empty.');
        return;
    }

    const minStake = 10;

    if (stake < minStake) {
        showToast('warning', `Minimum stake is KES ${minStake}.`);
        return;
    }

    const data = {
        selections: betSlipSelections.map(function(selection) {
            return {
                match_id: selection.match_id,
                selection_type: selection.selection_type
            };
        }),
        stake: stake,
        use_bonus: useBonus
    };

    const btn = document.getElementById('betslipPlaceBtn');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            '<i class="fas fa-spinner fa-spin me-1"></i> Placing Bet...';
    }

    fetch('/betting/place-bet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {

        if (!response.ok) {
            return response.json().then(function(err) {
                throw err;
            });
        }

        return response.json();
    })
    .then(function(result) {

        if (!result.success) {
            throw result;
        }

        // Success message
        showToast(
            'success',
            '✅ Bet placed successfully! Ref: ' + result.bet_reference
        );

        // Disable placing another bet immediately
        if (btn) {
            btn.disabled = true;
        }

        // Wait a second before clearing
        setTimeout(function () {

            clearBetSlip();
            closeBetSlip();

            // Refresh wallet balance
            updateWalletDisplay();

        }, 1000);

    })
    .catch(function(error) {

        console.error(error);

        showToast(
            'danger',
            '❌ ' + (error.error || 'Failed to place bet. Please try again.')
        );

        // Keep the bet slip intact so user can retry
    })
    .finally(function() {

        if (btn) {
            btn.disabled = false;
            btn.innerHTML =
                '<i class="fas fa-check me-1"></i> Place Bet';
        }

    });
}

// ===================================================================
// TOAST NOTIFICATIONS
// ===================================================================
function showToast(category, message) {
    const container = document.querySelector('.flash-container') || (function() {
        const div = document.createElement('div');
        div.className = 'flash-container position-fixed top-0 end-0 p-3 z-3';
        div.style.zIndex = '9999';
        document.body.appendChild(div);
        return div;
    })();

    const alert = document.createElement('div');
    alert.className = 'alert alert-' + category + ' alert-dismissible fade show glass-card shadow-lg mb-2 animate-slide-right';
    alert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${category === 'success' ? 'check-circle' : category === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    setTimeout(function() {
        if (alert.parentNode) {
            alert.style.transition = 'all 0.3s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
            setTimeout(function() {
                if (alert.parentNode) alert.parentNode.removeChild(alert);
            }, 300);
        }
    }, 5000);
}

// ===================================================================
// NOTIFICATIONS
// ===================================================================
function initNotifications() {
    // Mark single notification as read
    document.querySelectorAll('[data-mark-read]').forEach(function(el) {
        el.addEventListener('click', function() {
            const notifId = this.dataset.markRead;
            markNotificationRead(notifId);
        });
    });
}

function markNotificationRead(notificationId) {
    fetch('/dashboard/mark-notification-read/' + notificationId, {
        method: 'GET',
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            const el = document.querySelector('[data-notif-id="' + notificationId + '"]');
            if (el) {
                el.classList.remove('bg-dark');
                el.classList.add('text-muted');
            }
            updateNotificationBadge();
        }
    });
}

function markAllNotificationsRead() {
    fetch('/dashboard/mark-all-read', {
        method: 'GET',
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        document.querySelectorAll('[data-notif-id]').forEach(function(el) {
            el.classList.remove('bg-dark', 'fw-bold');
        });
        updateNotificationBadge();
    });
}

function updateNotificationBadge() {
    fetch('/api/v1/health')
        .then(function(r) { return r.json(); })
        .then(function() {
            // Simple page reload for badge update; could be enhanced
            location.reload();
        });
}

// ===================================================================
// WALLET DISPLAY
// ===================================================================
function updateWalletDisplay() {
    // Reload page to reflect balance changes
    location.reload();
}

// ===================================================================
// UTILITY
// ===================================================================
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });
}

function initMobileMenu() {
    // Close sidebar on overlay click for mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth < 992) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !e.target.closest('#sidebarToggle')) {
                    closeSidebar();
                }
            }
        }
    });
}

// ===================================================================
// FORMAT HELPERS
// ===================================================================
function formatCurrency(amount) {
    return 'KSh ' + Number(amount).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-KE', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatDateTime(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-KE', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ===================================================================
// CHART INIT HELPERS
// ===================================================================
function initChart(canvasId, type, labels, data, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#9aa0a6', font: { family: 'Inter' } }
            }
        },
        scales: {
            x: {
                ticks: { color: '#9aa0a6', font: { family: 'Inter', size: 11 } },
                grid: { color: 'rgba(255,255,255,0.05)' }
            },
            y: {
                ticks: { color: '#9aa0a6', font: { family: 'Inter', size: 11 } },
                grid: { color: 'rgba(255,255,255,0.05)' }
            }
        }
    };

    const mergedOptions = Object.assign({}, defaultOptions, options);
    return new Chart(ctx, {
        type: type,
        data: {
            labels: labels,
            datasets: data
        },
        options: mergedOptions
    });
}