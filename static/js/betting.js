// ===== FORCE MOBILE BET SLIP =====
window.openMobileBetSlip = function () {
    alert('MOBILE BUTTON CLICKED');

    const el = document.getElementById('betslipOffcanvas');

    if (!el) {
        alert('OFFCANVAS NOT FOUND');
        return;
    }

    el.classList.add('show');
    el.style.display = 'block';
    el.style.visibility = 'visible';
};
