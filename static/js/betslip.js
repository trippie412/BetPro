/* ==========================================================================
   BETPRO BETSLIP ENGINE — full working version (delegation-based)
========================================================================== */

class BetSlip {

    constructor() {
        this.state = {
            selections: [],
            stake: 0,
            bonus: false,
            minStake: 10,
            currency: "KES"
        };

        this.config = {
            placeBetUrl: "/betting/place-bet",
            mobileBreakpoint: 992
        };

        this.dom = {};
        this.toastTimer = null;
        this.initialized = false;
        this.init();
    }

    /* ---------------- INIT ---------------- */
    init() {
        if (this.initialized) return;
        this.cacheDom();
        if (!this.dom.panel) {
            console.error("BetSlip panel not found.");
            return;
        }
        this.bindEvents();
        this.render();
        this.initialized = true;
    }

    /* ---------------- CACHE DOM ---------------- */
    cacheDom() {
        const panel = document.getElementById("betslipPanel");
        if (!panel) return;

        this.dom = {
            panel,
            overlay: document.getElementById("betslipOverlay"),
            floatButton: document.getElementById("betslipFloatBtn"),
            csrf: document.getElementById("betslipCsrf"),
            close: panel.querySelector(".betslip-close"),
            keep: panel.querySelector(".betslip-keep"),
            clearHeader: panel.querySelector(".betslip-clear-all"),
            clearFooter: panel.querySelector(".betslip-clear"),
            place: panel.querySelector(".betslip-place-btn"),
            stake: panel.querySelector(".betslip-stake"),
            bonus: panel.querySelector(".betslip-use-bonus"),
            toast: panel.querySelector(".betslip-toast"),
            hint: panel.querySelector(".betslip-hint"),
            body: panel.querySelector(".betslip-body"),
            footer: panel.querySelector(".betslip-footer"),
            empty: panel.querySelector(".betslip-empty"),
            selections: panel.querySelector(".betslip-selections"),
            totalOdds: panel.querySelector(".betslip-total-odds"),
            potential: panel.querySelector(".betslip-potential"),
            selectionCount: panel.querySelector(".betslip-count-2"),
            badge: panel.querySelector(".betslip-count"),
            template: document.getElementById("betslipCardTemplate")
        };
    }

    /* ---------------- EVENT BINDING (delegation) ---------------- */
    bindEvents() {
        // Delegated: catches ALL odds buttons, even ones added after page load
        document.addEventListener("click", e => {
            const btn = e.target.closest(".team-odds");
            if (btn) this.select(btn);
        });

        if (this.dom.floatButton) {
            this.dom.floatButton.addEventListener("click", () => this.open());
        }
        if (this.dom.close) {
            this.dom.close.addEventListener("click", () => this.close());
        }
        if (this.dom.overlay) {
            this.dom.overlay.addEventListener("click", () => this.close());
        }
        if (this.dom.keep) {
            this.dom.keep.addEventListener("click", () => this.close());
        }
        if (this.dom.clearHeader) {
            this.dom.clearHeader.addEventListener("click", () => this.clear());
        }
        if (this.dom.clearFooter) {
            this.dom.clearFooter.addEventListener("click", () => this.clear());
        }
        if (this.dom.place) {
            this.dom.place.addEventListener("click", () => this.placeBet());
        }

        if (this.dom.bonus) {
            this.dom.bonus.addEventListener("change", e => {
                this.state.bonus = e.target.checked;
                this.render();
            });
        }

        // LIVE potential win while typing the stake
        if (this.dom.stake) {
            this.dom.stake.addEventListener("input", e => {
                this.state.stake = Math.max(0, Number(e.target.value) || 0);
                this.render();
            });
        }

        // Quick-stake buttons
        document.querySelectorAll(".betslip-quick-stakes button").forEach(btn => {
            btn.addEventListener("click", () => {
                const value = Number(btn.dataset.stake) || 0;
                this.state.stake = value;
                this.dom.stake.value = value;
                this.render();
            });
        });

        // Remove card (delegated)
        this.dom.panel.addEventListener("click", e => {
            const remove = e.target.closest(".betslip-card-remove");
            if (remove) this.remove(remove.dataset.id);
        });

        // ESC
        document.addEventListener("keydown", e => {
            if (e.key === "Escape") this.close();
        });
    }

    /* ---------------- OPEN / CLOSE ---------------- */
    open() {
        if (window.innerWidth >= this.config.mobileBreakpoint) return;
        this.dom.panel.classList.add("open");
        this.dom.overlay.classList.add("show");
        this.dom.panel.setAttribute("aria-hidden", "false");
        document.body.classList.add("betslip-locked");
    }

    close() {
        this.dom.panel.classList.remove("open");
        this.dom.overlay.classList.remove("show");
        if (window.innerWidth < this.config.mobileBreakpoint) {
            this.dom.panel.setAttribute("aria-hidden", "true");
        }
        document.body.classList.remove("betslip-locked");
    }

    toggle() {
        if (this.dom.panel.classList.contains("open")) this.close();
        else this.open();
    }

    /* ---------------- SELECT ENGINE ---------------- */
    select(button) {
        const bet = this.extractBet(button);
        if (!bet) return;

        const existing = this.state.selections.findIndex(
            item => item.matchId === bet.matchId
        );

        if (existing !== -1 &&
            this.state.selections[existing].selection === bet.selection) {
            this.state.selections.splice(existing, 1);   // same pick -> remove
        } else if (existing !== -1) {
            this.state.selections[existing] = bet;        // different pick -> replace
        } else {
            this.state.selections.push(bet);              // new match
        }

        this.highlightButtons();
        this.render();
    }

    /* Reads match info from your real markup.
       Uses data-* if present, otherwise falls back to
       the parent match-card text + the button text/position. */
    extractBet(button) {
        const matchCard = button.closest(".match-card") ||
                          button.closest(".match") ||
                          button.parentElement.parentElement;
        const matchName = matchCard
            ? matchCard.querySelector(".match-name, .match-teams, .team")
                  ?.textContent?.trim() || "Match"
            : "Match";

        // Odds from data attribute or from the visible button text
        const oddsRaw = button.dataset.odds ||
                        button.textContent.replace(/[^\d.]/g, "");
        const odds = Number(oddsRaw);

        // Selection key/label
        const selection = button.dataset.selection || this.guessSelection(button);
        const label = button.dataset.selectionLabel || selection;
        const matchId = button.dataset.matchId ||
                        (matchCard ? matchCard.dataset.matchId || matchCard.dataset.id : null) ||
                        matchName;

        if (!odds || odds <= 0) {
            console.warn("[BetSlip] No valid odds on button", button);
            return null;
        }

        return { matchId, match: matchName, selection, label, odds, button };
    }

    guessSelection(button) {
        const idx = Array.from(button.parentElement.children).indexOf(button);
        const text = button.textContent.trim();
        if (/draw|X|xi/i.test(text)) return "X";
        return ["1", "X", "2"][idx] || (idx === 0 ? "1" : "2");
    }

    remove(matchId) {
        this.state.selections =
            this.state.selections.filter(item => item.matchId != matchId);
        this.highlightButtons();
        this.render();
    }

    clear() {
        this.state.selections = [];
        this.state.stake = 0;
        this.state.bonus = false;
        if (this.dom.stake) this.dom.stake.value = "";
        if (this.dom.bonus) this.dom.bonus.checked = false;
        this.highlightButtons();
        this.render();
    }

    highlightButtons() {
        document.querySelectorAll(".team-odds").forEach(button => {
            button.classList.remove("selected", "btn-warning");
            button.classList.add("btn-outline-warning");
        });
        this.state.selections.forEach(bet => {
            if (bet.button && bet.button.classList) {
                bet.button.classList.remove("btn-outline-warning");
                bet.button.classList.add("btn-warning", "selected");
            }
        });
    }

    /* ---------------- CALCULATIONS ---------------- */
    hasSelections() {
        return this.state.selections.length > 0;
    }
    selectionCount() {
        return this.state.selections.length;
    }
    calculateOdds() {
        if (!this.state.selections.length) return 0;
        return this.state.selections.reduce((t, bet) => t * bet.odds, 1);
    }
    calculatePotentialWin() {
        return this.calculateOdds() * this.state.stake;
    }
    isValidStake() {
        return this.state.stake >= this.state.minStake;
    }
    canPlaceBet() {
        return this.hasSelections() && this.isValidStake();
    }
    currency(value) {
        return `${this.state.currency} ${value.toFixed(2)}`;
    }

    /* ---------------- RENDER ---------------- */
    render() {
        this.renderCards();
        this.renderSummary();
        this.renderPotentialWin();
        this.renderBadge();
        this.renderFooter();
        this.renderPlaceButton();
        this.renderHint();
    }

    renderCards() {
        const container = this.dom.selections;
        if (!container) return;
        container.innerHTML = "";

        if (!this.state.selections.length) {
            this.dom.empty.style.display = "flex";
            this.dom.body.style.display = "none";
            return;
        }
        this.dom.empty.style.display = "none";
        this.dom.body.style.display = "block";

        this.state.selections.forEach(bet => {
            let card;
            if (this.dom.template) {
                card = this.dom.template.content.firstElementChild.cloneNode(true);
            } else {
                card = document.createElement("article");
                card.className = "betslip-card";
                card.innerHTML = `
                    <div class="betslip-card-main">
                        <div class="betslip-card-match"></div>
                        <div class="betslip-card-market">
                            <span class="market-key"></span>
                            <span class="market-odds"></span>
                        </div>
                    </div>
                    <button type="button" class="betslip-card-remove">
                        <i class="fas fa-times"></i>
                    </button>`;
            }
            card.querySelector(".betslip-card-match").textContent = bet.match;
            card.querySelector(".market-key").textContent = bet.label;
            card.querySelector(".market-odds").textContent = `@ ${bet.odds.toFixed(2)}`;
            card.querySelector(".betslip-card-remove").dataset.id = bet.matchId;
            container.appendChild(card);
        });
    }

    renderSummary() {
        if (this.dom.totalOdds) {
            this.dom.totalOdds.textContent = this.calculateOdds().toFixed(2);
        }
        if (this.dom.selectionCount) {
            this.dom.selectionCount.textContent = this.selectionCount();
        }
    }

    renderPotentialWin() {
        if (!this.dom.potential) return;
        this.dom.potential.textContent =
            this.currency(this.calculatePotentialWin());
    }

    renderBadge() {
        if (!this.dom.badge) return;
        const count = this.selectionCount();
        this.dom.badge.textContent = count;
        if (this.dom.floatButton) {
            const b = this.dom.floatButton.querySelector(".betslip-count");
            if (b) b.textContent = count;
        }
    }

    renderFooter() {
        if (!this.dom.footer) return;
        this.dom.footer.style.display =
            this.hasSelections() ? "block" : "none";
    }

    renderPlaceButton() {
        if (!this.dom.place) return;
        this.dom.place.disabled = !this.canPlaceBet();
    }

    renderHint() {
        if (!this.dom.hint) return;
        const msg = `Minimum stake is KES ${this.state.minStake}`;
        this.dom.hint.textContent = msg;
        if (this.state.stake > 0 && this.state.stake < this.state.minStake) {
            this.dom.hint.classList.add("error");
        } else {
            this.dom.hint.classList.remove("error");
        }
    }

    /* ---------------- PLACE BET ---------------- */
    async placeBet() {
        if (!this.canPlaceBet()) {
            this.toast("Enter a valid stake and select at least one bet.", "error");
            return;
        }
        this.setLoading(true);
        try {
            const response = await fetch(this.config.placeBetUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": this.dom.csrf ? this.dom.csrf.value : ""
                },
                body: JSON.stringify({
                    stake: this.state.stake,
                    use_bonus: this.state.bonus,
                    selections: this.state.selections.map(bet => ({
                        match_id: bet.matchId,
                        selection_type: bet.selection
                        
                    }))
                })
            });
            const result = await response.json();
            if (!response.ok || result.success === false) {
                throw new Error(result.error || "Bet placement failed.");
            }
            this.toast(result.message || "Bet placed successfully.", "success");
            this.clear();
        } catch (error) {
            console.error(error);
            this.toast(error.message || "Unable to place bet.", "error");
        } finally {
            this.setLoading(false);
        }
    }

    setLoading(state) {
        if (!this.dom.place) return;
        this.dom.place.disabled = state;
        this.dom.place.classList.toggle("loading", state);
    }

    toast(message, type = "info") {
        if (!this.dom.toast) { alert(message); return; }
        this.dom.toast.textContent = message;
        this.dom.toast.className = `betslip-toast ${type}`;
        this.dom.toast.classList.add("show");
        clearTimeout(this.toastTimer);
        this.toastTimer = setTimeout(() => {
            this.dom.toast.classList.remove("show");
        }, 3000);
    }

    debug() {
        console.table(this.state.selections);
        console.log({
            selections: this.selectionCount(),
            totalOdds: this.calculateOdds(),
            stake: this.state.stake,
            potentialWin: this.calculatePotentialWin(),
            useBonus: this.state.bonus
        });
    }

    destroy() {
        this.clear();
        this.initialized = false;
    }
}

/* ---------------- BOOTSTRAP ---------------- */
document.addEventListener("DOMContentLoaded", () => {
    window.betSlip = new BetSlip();
});

/* ---------------- LEGACY API ---------------- */
window.placeBet = () => window.betSlip && window.betSlip.placeBet();
window.clearBetSlip = () => window.betSlip && window.betSlip.clear();
window.calculatePotential = () => window.betSlip && window.betSlip.render();
window.openMobileBetSlip = () => window.betSlip && window.betSlip.open();
window.closeMobileBetSlip = () => window.betSlip && window.betSlip.close();
window.toggleBetSlip = () => window.betSlip && window.betSlip.toggle();