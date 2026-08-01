import { Component, xml, useRef, useState, onMounted, onWillUnmount } from "../../../lib/owl/owl.js";

// Handheld/laptop-attached barcode scanners act as "keyboard wedges": they
// type the barcode's characters very fast and (almost always) finish with an
// Enter/Tab keystroke. This input stays invisible-but-focused so an operator
// can just point-and-scan without touching the screen, and submits either on
// Enter or after a short pause in typing (for the rare scanner that doesn't
// send a terminator).
const SUBMIT_ON_PAUSE_MS = 300;

export class ScanInput extends Component {
    static template = xml`
        <input t-ref="input"
               class="o_scan_input"
               type="text"
               inputmode="none"
               autocomplete="off"
               autocorrect="off"
               autocapitalize="off"
               spellcheck="false"
               t-att-placeholder="props.placeholder ?? 'Scan a barcode…'"
               t-att-value="state.value"
               t-on-keydown="onKeydown"
               t-on-input="onInput"/>
    `;
    static props = {
        onScan: Function,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.inputRef = useRef("input");
        this.state = useState({ value: "" });
        this.pauseTimer = null;

        onMounted(() => {
            this.focusInput();
            this.refocusInterval = setInterval(() => this.maybeRefocus(), 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.refocusInterval);
            clearTimeout(this.pauseTimer);
        });
    }

    focusInput() {
        this.inputRef.el?.focus();
    }

    // Keep the scan input focused so scans work without tapping the screen
    // first, but don't steal focus from something the user is actively using
    // (a manual quantity field, a dialog, ...).
    maybeRefocus() {
        const active = document.activeElement;
        if (!active || active === document.body || active === this.inputRef.el) {
            this.focusInput();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" || ev.key === "Tab") {
            ev.preventDefault();
            this.submit();
        }
    }

    onInput(ev) {
        this.state.value = ev.target.value;
        clearTimeout(this.pauseTimer);
        if (this.state.value) {
            this.pauseTimer = setTimeout(() => this.submit(), SUBMIT_ON_PAUSE_MS);
        }
    }

    submit() {
        clearTimeout(this.pauseTimer);
        const code = this.state.value.trim();
        this.state.value = "";
        if (code) {
            this.props.onScan(code);
        }
    }
}
