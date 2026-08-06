// ===== FORCE MOBILE BET SLIP VISIBLE =====
window.openMobileBetSlip = function () {

    const el = document.getElementById('betslipOffcanvas');

    if (!el) {
        alert('OFFCANVAS NOT FOUND');
        return;
    }

    // Force the panel to appear
    el.style.display = 'block';
    el.style.visibility = 'visible';
    el.style.opacity = '1';
    el.style.transform = 'translateX(0)';
    el.classList.add('show');

    // Add backdrop
    if (!document.getElementById('betslipBackdrop')) {
        const backdrop = document.createElement('div');
        backdrop.id = 'betslipBackdrop';
        backdrop.style.position = 'fixed';
        backdrop.style.top = '0';
        backdrop.style.left = '0';
        backdrop.style.width = '100%';
        backdrop.style.height = '100%';
        backdrop.style.background = 'rgba(0,0,0,0.5)';
        backdrop.style.zIndex = '1040';
        backdrop.onclick = function () {
            el.classList.remove('show');
            el.style.display = 'none';
            backdrop.remove();
        };
        document.body.appendChild(backdrop);
    }

    // Make sure panel is above backdrop
    el.style.zIndex = '1050';
};
