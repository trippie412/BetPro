// ===== FINAL MOBILE BET SLIP FIX =====
window.openMobileBetSlip = function () {

    const el = document.getElementById('betslipOffcanvas');

    if (!el) {
        alert('OFFCANVAS NOT FOUND');
        return;
    }

    // Use Bootstrap offcanvas properly
    if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {

        const instance = bootstrap.Offcanvas.getOrCreateInstance(el);
        instance.show();

    } else {

        // Fallback if Bootstrap is missing
        el.classList.add('show');
        el.style.display = 'block';
        el.style.visibility = 'visible';
    }
};
