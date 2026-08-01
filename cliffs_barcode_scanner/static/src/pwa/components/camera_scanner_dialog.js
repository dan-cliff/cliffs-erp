import { Component, xml, useRef, useState, onMounted, onWillUnmount } from "../../../lib/owl/owl.js";

// Fallback scan path for devices with no attached hardware scanner, using the
// standard (Chrome/Edge/Android) BarcodeDetector Web API. Deliberately not
// bundling a JS decoding library for browsers without it (Safari/Firefox) -
// on those, this stays unavailable and the hardware scanner / manual entry
// are the supported paths.
export function isCameraScanningSupported() {
    return "BarcodeDetector" in window;
}

export class CameraScannerDialog extends Component {
    static template = xml`
        <div class="o_camera_scanner_backdrop" t-on-click="props.onClose">
            <div class="o_camera_scanner_dialog" t-on-click="(ev) => ev.stopPropagation()">
                <div class="o_camera_scanner_header">
                    <span>Scan with camera</span>
                    <button class="o_camera_scanner_close" t-on-click="props.onClose">✕</button>
                </div>
                <video t-ref="video" class="o_camera_scanner_video" autoplay="autoplay" playsinline="playsinline" muted="muted"/>
                <p t-if="state.error" class="o_camera_scanner_error" t-esc="state.error"/>
            </div>
        </div>
    `;
    static props = {
        onScan: Function,
        onClose: Function,
    };

    setup() {
        this.videoRef = useRef("video");
        this.state = useState({ error: "" });
        this.stream = null;
        this.detecting = false;
        this.rafId = null;

        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
    }

    async start() {
        if (!isCameraScanningSupported()) {
            this.state.error = "Camera scanning isn't supported in this browser.";
            return;
        }
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
            });
        } catch (err) {
            this.state.error = "Camera access was denied or unavailable.";
            return;
        }
        const video = this.videoRef.el;
        video.srcObject = this.stream;
        await video.play();
        this.detector = new window.BarcodeDetector();
        this.detecting = true;
        this.loop();
    }

    async loop() {
        if (!this.detecting) {
            return;
        }
        try {
            const codes = await this.detector.detect(this.videoRef.el);
            if (codes.length) {
                this.props.onScan(codes[0].rawValue);
                return; // the parent closes this dialog from its onScan handler
            }
        } catch (err) {
            // Transient decode errors between frames are expected; ignore.
        }
        this.rafId = requestAnimationFrame(() => this.loop());
    }

    stop() {
        this.detecting = false;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
        }
        if (this.stream) {
            for (const track of this.stream.getTracks()) {
                track.stop();
            }
        }
    }
}
