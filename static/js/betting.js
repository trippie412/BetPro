// ===== GUARANTEED MOBILE BET SLIP =====
window.openMobileBetSlip = function () {
    let panel = document.getElementById('mobileBetSlipPanel');

    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'mobileBetSlipPanel';

        panel.style.position = 'fixed';
        panel.style.top = '0';
        panel.style.right = '0';
        panel.style.width = '90%';
        panel.style.maxWidth = '380px';
        panel.style.height = '100%';
        panel.style.background = '#111827';
        panel.style.color = '#fff';
        panel.style.zIndex = '99999';
        panel.style.padding = '20px';
        panel.style.overflowY = 'auto';
        panel.style.boxShadow = '-4px 0 20px rgba(0,0,0,.5)';

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                <h3 style="margin:0;color:#facc15;">Bet Slip</h3>
                <button id="closeMobileSlip" style="background:none;border:none;color:#fff;font-size:28px;cursor:pointer;">&times;</button>
            </div>

            <div id="mobileSlipContent">
                <p style="color:#9ca3af;">Your selected bets will appear here.</p>
            </div>

            <div style="margin-top:24px;">
                <label style="display:block;margin-bottom:8px;">Stake (KES)</label>
                <input type="number" placeholder="Minimum 10"
                       style="width:100%;padding:12px;border-radius:10px;border:1px solid #374151;background:#1f2937;color:#fff;">

                <div style="margin-top:16px;padding:12px;border-radius:10px;background:#064e3b;color:#d1fae5;display:flex;justify-content:space-between;">
                    <span>Potential Win</span>
                    <strong>KES 0.00</strong>
                </div>

                <button style="width:100%;margin-top:16px;padding:14px;border:none;border-radius:10px;background:#facc15;color:#111827;font-weight:700;font-size:16px;">
                    Place Bet
                </button>
            </div>
        `;

        document.body.appendChild(panel);

        document.getElementById('closeMobileSlip').onclick = function () {
            panel.remove();
        };
    }
};
