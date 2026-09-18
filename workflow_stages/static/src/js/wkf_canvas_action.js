/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;

export class WorkflowStagesCanvasAction extends Component {
    static template = "workflow_stages.WorkflowStagesCanvasAction";
    static props = ["action", "actionService?", "*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.canvasOuter = useRef("canvasOuter");

        // params is the canonical place for client-action data; context is the fallback.
        // Always coerce to Number — JSON can sometimes deliver strings.
        const rawId =
            this.props.action.params?.workflow_id ??
            this.props.action.context?.workflow_id;
        this.workflowId = rawId ? Number(rawId) : null;

        this.state = useState({
            workflowName: "",
            stages: [],
            transitions: [],
            selectedStageId: null,
            selectedTransitionId: null,
            editingTransition: null,
            loading: true,
            saving: false,
            zoom: 1.0,
            panX: 80,
            panY: 80,
            // Internal interaction flags (not for rendering)
            _dragging: null,
            _panning: null,
            _connecting: null,
        });

        this._onMousemove = this._globalMousemove.bind(this);
        this._onMouseup = this._globalMouseup.bind(this);
        this._alive = false;

        onMounted(async () => {
            this._alive = true;
            await this.loadWorkflow();
        });

        onWillUnmount(() => {
            this._alive = false;
            document.removeEventListener("mousemove", this._onMousemove);
            document.removeEventListener("mouseup", this._onMouseup);
        });
    }

    // ------------------------------------------------------------------ //
    // Data loading                                                         //
    // ------------------------------------------------------------------ //

    async loadWorkflow() {
        this.state.loading = true;
        if (!this.workflowId) {
            this.state.loading = false;
            this.notification.add(
                "No workflow ID found. Please reopen the canvas from a Workflow record.",
                { type: "danger", sticky: true }
            );
            return;
        }
        try {
            const [wf] = await this.orm.read(
                "wkf.workflow",
                [this.workflowId],
                ["name", "canvas_zoom", "canvas_pan_x", "canvas_pan_y"]
            );
            this.state.workflowName = wf.name;
            if (wf.canvas_zoom) {
                this.state.zoom = wf.canvas_zoom;
                this.state.panX = wf.canvas_pan_x || 80;
                this.state.panY = wf.canvas_pan_y || 80;
            }

            const stages = await this.orm.searchRead(
                "wkf.stage",
                [["workflow_id", "=", this.workflowId]],
                ["id", "name", "canvas_x", "canvas_y", "sequence",
                 "is_initial", "is_final", "allowed_user_count"]
            );

            const rawTransitions = await this.orm.searchRead(
                "wkf.transition",
                [["workflow_id", "=", this.workflowId]],
                ["id", "from_stage_id", "to_stage_id", "name", "direction",
                 "allow_manual", "allow_automatic", "record_condition_type", "sequence"]
            );

            // Normalise many2one tuples [id, name] → id
            const transitions = rawTransitions.map((t) => ({
                ...t,
                from_stage_id: Array.isArray(t.from_stage_id) ? t.from_stage_id[0] : t.from_stage_id,
                to_stage_id: Array.isArray(t.to_stage_id) ? t.to_stage_id[0] : t.to_stage_id,
            }));

            // Auto-layout when every stage sits at the default (100, 100)
            if (stages.length > 1 && stages.every((s) => s.canvas_x === 100 && s.canvas_y === 100)) {
                this._autoLayout(stages, transitions);
                this._savePositions(stages);
            }

            this.state.stages = stages;
            this.state.transitions = transitions;
        } finally {
            this.state.loading = false;
        }
    }

    _autoLayout(stages, transitions) {
        const COLS = Math.min(4, stages.length);
        const gapX = NODE_WIDTH + 80;
        const gapY = NODE_HEIGHT + 60;
        stages.sort((a, b) => a.sequence - b.sequence || a.id - b.id);
        stages.forEach((s, i) => {
            s.canvas_x = 80 + (i % COLS) * gapX;
            s.canvas_y = 80 + Math.floor(i / COLS) * gapY;
        });
    }

    async _savePositions(stages) {
        for (const s of stages) {
            await this.orm.write("wkf.stage", [s.id], { canvas_x: s.canvas_x, canvas_y: s.canvas_y });
        }
    }

    async _savePanZoom() {
        await this.orm.write("wkf.workflow", [this.workflowId], {
            canvas_zoom: this.state.zoom,
            canvas_pan_x: this.state.panX,
            canvas_pan_y: this.state.panY,
        });
    }

    // ------------------------------------------------------------------ //
    // Computed helpers                                                     //
    // ------------------------------------------------------------------ //

    get viewportStyle() {
        return `transform: translate(${this.state.panX}px,${this.state.panY}px) scale(${this.state.zoom}); transform-origin: 0 0;`;
    }

    nodeStyle(stage) {
        return `left:${stage.canvas_x}px;top:${stage.canvas_y}px;width:${NODE_WIDTH}px;`;
    }

    getSelectedStage() {
        return this.state.stages.find((s) => s.id === this.state.selectedStageId) || null;
    }

    getSelectedTransition() {
        return (
            this.state.editingTransition ||
            this.state.transitions.find((c) => c.id === this.state.selectedTransitionId) ||
            null
        );
    }

    transitionPath(conn) {
        const from = this.state.stages.find((s) => s.id === conn.from_stage_id);
        const to = this.state.stages.find((s) => s.id === conn.to_stage_id);
        if (!from || !to) return null;
        const x1 = from.canvas_x + NODE_WIDTH;
        const y1 = from.canvas_y + NODE_HEIGHT / 2;
        const x2 = to.canvas_x;
        const y2 = to.canvas_y + NODE_HEIGHT / 2;
        const dx = Math.max(80, Math.abs(x2 - x1) / 2);
        return {
            d: `M ${x1} ${y1} C ${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`,
            labelX: (x1 + x2) / 2,
            labelY: Math.min(y1, y2) - 10,
        };
    }

    ghostPath() {
        const c = this.state._connecting;
        if (!c) return "";
        const from = this.state.stages.find((s) => s.id === c.fromStageId);
        if (!from) return "";
        const x1 = from.canvas_x + NODE_WIDTH;
        const y1 = from.canvas_y + NODE_HEIGHT / 2;
        const dx = Math.max(80, Math.abs(c.cursorX - x1) / 2);
        return `M ${x1} ${y1} C ${x1 + dx} ${y1} ${c.cursorX - dx} ${c.cursorY} ${c.cursorX} ${c.cursorY}`;
    }

    _screenToWorld(clientX, clientY) {
        const el = this.canvasOuter.el;
        if (!el) return { x: 0, y: 0 };
        const r = el.getBoundingClientRect();
        return {
            x: (clientX - r.left - this.state.panX) / this.state.zoom,
            y: (clientY - r.top - this.state.panY) / this.state.zoom,
        };
    }

    // ------------------------------------------------------------------ //
    // Canvas mouse events                                                  //
    // ------------------------------------------------------------------ //

    onCanvasMousedown(ev) {
        if (ev.button !== 0) return;
        const target = ev.target;
        const onEmpty =
            target === this.canvasOuter.el ||
            target.classList.contains("wkf-viewport") ||
            target.classList.contains("wkf-svg");
        if (!onEmpty) return;
        this.state.selectedStageId = null;
        this.state.selectedTransitionId = null;
        this.state.editingTransition = null;
        this.state._panning = {
            sx: ev.clientX,
            sy: ev.clientY,
            px: this.state.panX,
            py: this.state.panY,
        };
        document.addEventListener("mousemove", this._onMousemove);
        document.addEventListener("mouseup", this._onMouseup);
    }

    onNodeMousedown(ev, stage) {
        if (ev.button !== 0) return;
        ev.stopPropagation();
        this.state.selectedStageId = stage.id;
        this.state.selectedTransitionId = null;
        this.state.editingTransition = null;
        this.state._dragging = {
            stageId: stage.id,
            sx: ev.clientX,
            sy: ev.clientY,
            ox: stage.canvas_x,
            oy: stage.canvas_y,
        };
        document.addEventListener("mousemove", this._onMousemove);
        document.addEventListener("mouseup", this._onMouseup);
    }

    onOutputPortMousedown(ev, stageId) {
        if (ev.button !== 0) return;
        ev.stopPropagation();
        const pos = this._screenToWorld(ev.clientX, ev.clientY);
        this.state._connecting = { fromStageId: stageId, cursorX: pos.x, cursorY: pos.y };
        document.addEventListener("mousemove", this._onMousemove);
        document.addEventListener("mouseup", this._onMouseup);
    }

    async onInputPortMouseup(ev, toStageId) {
        ev.stopPropagation();
        if (!this.state._connecting) return;
        const fromStageId = this.state._connecting.fromStageId;
        this.state._connecting = null;
        document.removeEventListener("mousemove", this._onMousemove);
        document.removeEventListener("mouseup", this._onMouseup);

        if (fromStageId === toStageId) return;
        const dup = this.state.transitions.some(
            (c) => c.from_stage_id === fromStageId && c.to_stage_id === toStageId
        );
        if (dup) return;

        // orm.create() in Odoo 19 requires an array of record dicts and returns an array of IDs
        const [newId] = await this.orm.create("wkf.transition", [{
            from_stage_id: fromStageId,
            to_stage_id: toStageId,
            name: "Transition",
            direction: "forward",
        }]);
        this.state.transitions.push({
            id: newId,
            from_stage_id: fromStageId,
            to_stage_id: toStageId,
            name: "Transition",
            direction: "forward",
            allow_manual: true,
            allow_automatic: true,
            record_condition_type: "none",
            sequence: 10,
        });
    }

    _globalMousemove(ev) {
        if (this.state._dragging) {
            const d = this.state._dragging;
            const dx = (ev.clientX - d.sx) / this.state.zoom;
            const dy = (ev.clientY - d.sy) / this.state.zoom;
            const stage = this.state.stages.find((s) => s.id === d.stageId);
            if (stage) {
                stage.canvas_x = Math.max(0, d.ox + dx);
                stage.canvas_y = Math.max(0, d.oy + dy);
            }
        } else if (this.state._panning) {
            const p = this.state._panning;
            this.state.panX = p.px + (ev.clientX - p.sx);
            this.state.panY = p.py + (ev.clientY - p.sy);
        } else if (this.state._connecting) {
            const pos = this._screenToWorld(ev.clientX, ev.clientY);
            this.state._connecting.cursorX = pos.x;
            this.state._connecting.cursorY = pos.y;
        }
    }

    async _globalMouseup(ev) {
        if (this.state._dragging) {
            const stageId = this.state._dragging.stageId;
            const stage = this.state.stages.find((s) => s.id === stageId);
            this.state._dragging = null;
            if (stage) {
                await this.orm.write("wkf.stage", [stage.id], {
                    canvas_x: stage.canvas_x,
                    canvas_y: stage.canvas_y,
                });
            }
        }
        if (this.state._panning) {
            this.state._panning = null;
            this._savePanZoom();
        }
        if (this.state._connecting) {
            this.state._connecting = null;
        }
        document.removeEventListener("mousemove", this._onMousemove);
        document.removeEventListener("mouseup", this._onMouseup);
    }

    onWheel(ev) {
        ev.preventDefault();
        const el = this.canvasOuter.el;
        if (!el) return;
        const r = el.getBoundingClientRect();
        const mx = ev.clientX - r.left;
        const my = ev.clientY - r.top;
        const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
        const newZoom = Math.max(0.15, Math.min(3.0, this.state.zoom * factor));
        this.state.panX = mx - (mx - this.state.panX) * (newZoom / this.state.zoom);
        this.state.panY = my - (my - this.state.panY) * (newZoom / this.state.zoom);
        this.state.zoom = newZoom;
    }

    // ------------------------------------------------------------------ //
    // Toolbar actions                                                      //
    // ------------------------------------------------------------------ //

    zoomIn() {
        const el = this.canvasOuter.el;
        const cx = el ? el.clientWidth / 2 : 400;
        const cy = el ? el.clientHeight / 2 : 300;
        const newZoom = Math.min(3.0, this.state.zoom * 1.2);
        this.state.panX = cx - (cx - this.state.panX) * (newZoom / this.state.zoom);
        this.state.panY = cy - (cy - this.state.panY) * (newZoom / this.state.zoom);
        this.state.zoom = newZoom;
        this._savePanZoom();
    }

    zoomOut() {
        const el = this.canvasOuter.el;
        const cx = el ? el.clientWidth / 2 : 400;
        const cy = el ? el.clientHeight / 2 : 300;
        const newZoom = Math.max(0.15, this.state.zoom / 1.2);
        this.state.panX = cx - (cx - this.state.panX) * (newZoom / this.state.zoom);
        this.state.panY = cy - (cy - this.state.panY) * (newZoom / this.state.zoom);
        this.state.zoom = newZoom;
        this._savePanZoom();
    }

    fitView() {
        const el = this.canvasOuter.el;
        if (!el || !this.state.stages.length) return;
        const w = el.clientWidth;
        const h = el.clientHeight;
        const minX = Math.min(...this.state.stages.map((s) => s.canvas_x));
        const minY = Math.min(...this.state.stages.map((s) => s.canvas_y));
        const maxX = Math.max(...this.state.stages.map((s) => s.canvas_x + NODE_WIDTH));
        const maxY = Math.max(...this.state.stages.map((s) => s.canvas_y + NODE_HEIGHT));
        const pad = 80;
        const scaleX = (w - pad * 2) / (maxX - minX || 1);
        const scaleY = (h - pad * 2) / (maxY - minY || 1);
        const newZoom = Math.min(scaleX, scaleY, 1.5);
        this.state.zoom = newZoom;
        this.state.panX = pad - minX * newZoom;
        this.state.panY = pad - minY * newZoom;
        this._savePanZoom();
    }

    async addStage() {
        const el = this.canvasOuter.el;
        const w = el ? el.clientWidth : 800;
        const h = el ? el.clientHeight : 600;
        let x = Math.max(0, (w / 2 - this.state.panX) / this.state.zoom - NODE_WIDTH / 2);
        let y = Math.max(0, (h / 2 - this.state.panY) / this.state.zoom - NODE_HEIGHT / 2);
        while (this.state.stages.some((s) => Math.abs(s.canvas_x - x) < 20 && Math.abs(s.canvas_y - y) < 20)) {
            x += 25;
            y += 25;
        }
        const seq = this.state.stages.length
            ? Math.max(...this.state.stages.map((s) => s.sequence || 10)) + 10
            : 10;

        // orm.create() in Odoo 19 requires an array of record dicts and returns an array of IDs
        const [newId] = await this.orm.create("wkf.stage", [{
            workflow_id: this.workflowId,
            name: "New Stage",
            canvas_x: x,
            canvas_y: y,
            sequence: seq,
            is_initial: this.state.stages.length === 0,
        }]);

        this.state.stages.push({
            id: newId,
            name: "New Stage",
            canvas_x: x,
            canvas_y: y,
            sequence: seq,
            is_initial: this.state.stages.length === 0,
            is_final: false,
            allowed_user_count: 0,
        });

        this.editStage(newId);
    }

    editStage(stageId) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "wkf.stage",
                res_id: stageId,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => { if (this._alive) this.loadWorkflow(); } }
        );
    }

    async deleteStage(stageId) {
        const connIds = this.state.transitions
            .filter((c) => c.from_stage_id === stageId || c.to_stage_id === stageId)
            .map((c) => c.id);
        if (connIds.length) await this.orm.unlink("wkf.transition", connIds);
        await this.orm.unlink("wkf.stage", [stageId]);
        this.state.stages = this.state.stages.filter((s) => s.id !== stageId);
        this.state.transitions = this.state.transitions.filter(
            (c) => c.from_stage_id !== stageId && c.to_stage_id !== stageId
        );
        if (this.state.selectedStageId === stageId) this.state.selectedStageId = null;
    }

    async duplicateStage(stageId) {
        const stage = this.state.stages.find((s) => s.id === stageId);
        if (!stage) return;

        const newId = await this.orm.call("wkf.stage", "action_duplicate", [stageId], {});

        const [newStage] = await this.orm.read(
            "wkf.stage",
            [newId],
            ["id", "name", "canvas_x", "canvas_y", "sequence",
             "is_initial", "is_final", "allowed_user_count"]
        );

        this.state.stages.push(newStage);
        this.state.selectedStageId = newId;
        this.state.selectedTransitionId = null;
        this.state.editingTransition = null;

        this.notification.add(
            `"${stage.name}" duplicated — all configuration copied, no transitions.`,
            { type: "info" }
        );
    }

    selectTransition(connId) {
        const conn = this.state.transitions.find((c) => c.id === connId);
        this.state.selectedTransitionId = connId;
        this.state.selectedStageId = null;
        this.state.editingTransition = conn ? { ...conn } : null;
    }

    async setDirection(direction) {
        const ec = this.state.editingTransition;
        if (!ec) return;
        ec.direction = direction;
        await this.orm.write("wkf.transition", [ec.id], { direction });
        const idx = this.state.transitions.findIndex((c) => c.id === ec.id);
        if (idx >= 0) this.state.transitions[idx].direction = direction;
    }

    async deleteTransition(connId) {
        await this.orm.unlink("wkf.transition", [connId]);
        this.state.transitions = this.state.transitions.filter((c) => c.id !== connId);
        this.state.selectedTransitionId = null;
        this.state.editingTransition = null;
    }

    // Open the transition's Odoo form dialog so the graphical domain/user
    // filter builders are available. On close, refresh transition data
    // without a full reload.
    editTransition(connId) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "wkf.transition",
                res_id: connId,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: async () => {
                    if (!this._alive) return;
                    await this._refreshTransitions();
                    if (this.state.selectedTransitionId === connId) {
                        const refreshed = this.state.transitions.find((c) => c.id === connId);
                        this.state.editingTransition = refreshed ? { ...refreshed } : null;
                    }
                },
            }
        );
    }

    // Lightweight refresh — reloads only transition records, no spinner.
    async _refreshTransitions() {
        const rawTransitions = await this.orm.searchRead(
            "wkf.transition",
            [["workflow_id", "=", this.workflowId]],
            ["id", "from_stage_id", "to_stage_id", "name", "direction",
             "allow_manual", "allow_automatic", "record_condition_type", "sequence"]
        );
        this.state.transitions = rawTransitions.map((t) => ({
            ...t,
            from_stage_id: Array.isArray(t.from_stage_id) ? t.from_stage_id[0] : t.from_stage_id,
            to_stage_id:   Array.isArray(t.to_stage_id)   ? t.to_stage_id[0]   : t.to_stage_id,
        }));
    }

    async saveLayout() {
        this.state.saving = true;
        try {
            for (const s of this.state.stages) {
                await this.orm.write("wkf.stage", [s.id], { canvas_x: s.canvas_x, canvas_y: s.canvas_y });
            }
            await this._savePanZoom();
            this.notification.add("Layout saved", { type: "success" });
        } finally {
            this.state.saving = false;
        }
    }

    goBack() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "wkf.workflow",
            res_id: this.workflowId,
            views: [[false, "form"]],
        });
    }

    autoLayoutAll() {
        this._autoLayout(this.state.stages, this.state.transitions);
        this._savePositions(this.state.stages);
        this.fitView();
    }
}

registry.category("actions").add("workflow_stages.canvas", WorkflowStagesCanvasAction);
