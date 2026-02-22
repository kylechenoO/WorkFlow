/**
 * Run Viewer — Read-only Drawflow viewer for workflow run results.
 *
 * Displays a workflow in read-only mode with per-step status coloring:
 *   - pending  → gray border (dimmed)
 *   - running  → blue border + pulse animation
 *   - success  → green border + checkmark badge
 *   - failed   → red border + X badge
 *   - skipped  → dashed gray border (dimmed)
 *
 * Depends on: Drawflow.js, ModuleRegistry
 */

/* global Drawflow, ModuleRegistry */

var RunViewer = (function () {
    'use strict';

    var editor = null;
    var nodeCounter = 0;
    var stepResults = [];
    var nameToNodeId = {};

    // =========================================================
    //  Initialization
    // =========================================================

    function init(containerId, procedures, results) {
        stepResults = results || [];

        var container = document.getElementById(containerId);
        if (!container) return;

        // create drawflow instance in view-only mode
        editor = new Drawflow(container);
        editor.reroute = true;
        editor.editor_mode = 'fixed';  // read-only mode
        editor.start();

        // import the flow
        if (procedures && procedures.procedures) {
            importFlow(procedures);
        }

        // apply step status coloring
        applyStatusColors();

        // bind node click to highlight step detail
        editor.on('nodeSelected', function (nodeId) {
            highlightStepDetail(nodeId);
        });

        // bind zoom buttons
        bindZoomButtons();
    }

    // =========================================================
    //  Import Flow (read-only)
    // =========================================================

    function importFlow(data) {
        if (!editor) return;
        if (!data || !data.procedures) return;

        // compute auto-layout positions
        var positions = _computeLayout(data.procedures);

        // create nodes
        data.procedures.forEach(function (proc) {
            var pos = positions[proc.name] || { x: 80, y: 60 };

            var info = ModuleRegistry.findByMod(proc.mod);
            var color = info ? info.module.color : '#6c757d';
            var icon = info ? info.module.icon : 'bi-gear';
            var moduleName = info ? info.moduleName : proc.mod.split('.').pop();

            var nodeId = addNode(proc.mod, moduleName, proc.method, color, icon, pos.x, pos.y, proc.name);
            nameToNodeId[proc.name] = nodeId;
        });

        // draw sequential connections
        var connectedPairs = {};
        data.procedures.forEach(function (proc, idx) {
            var targetId = nameToNodeId[proc.name];
            if (!targetId) return;

            if (idx > 0) {
                var prevProc = data.procedures[idx - 1];
                var prevId = nameToNodeId[prevProc.name];
                if (prevId) {
                    var seqKey = prevId + '->' + targetId;
                    if (!connectedPairs[seqKey]) {
                        try { editor.addConnection(prevId, targetId, 'output_1', 'input_1'); } catch (e) {}
                        connectedPairs[seqKey] = true;
                    }
                }
            }
        });
    }

    // =========================================================
    //  Auto-Layout — BFS-based left-to-right graph layout
    // =========================================================

    function _computeLayout(procedures) {
        var xStart = 80;
        var yStart = 80;
        var xSpacing = 240;

        // sequential layout: each procedure gets its own column
        var positions = {};
        procedures.forEach(function (p, idx) {
            positions[p.name] = {
                x: xStart + idx * xSpacing,
                y: yStart
            };
        });

        return positions;
    }

    // =========================================================
    //  Node Creation
    // =========================================================

    function addNode(mod, moduleName, method, color, icon, x, y, stepName) {
        nodeCounter++;
        var name = stepName || (moduleName.toLowerCase() + '_' + nodeCounter);
        color = color || '#6c757d';
        icon = icon || 'bi-gear';

        // build node html
        var nodeHtml = '';
        nodeHtml += '<div class="node-order">' + nodeCounter + '</div>';
        nodeHtml += '<div class="node-header" style="background:' + color + ';">';
        nodeHtml += '<i class="bi ' + icon + '" style="font-size:10px;"></i>';
        nodeHtml += '<span>' + escHtml(moduleName) + '</span>';
        nodeHtml += '</div>';
        nodeHtml += '<div class="node-body">';
        nodeHtml += '<div class="node-title">' + escHtml(name) + '</div>';
        nodeHtml += '<div class="node-method">' + escHtml(method) + '</div>';
        nodeHtml += '</div>';

        // status badge placeholder (filled by applyStatusColors)
        nodeHtml += '<div class="node-status-badge"></div>';

        var nodeId = editor.addNode(
            name,
            1,
            1,
            x,
            y,
            'run-node',
            {},
            nodeHtml
        );

        return nodeId;
    }

    // =========================================================
    //  Status Coloring
    // =========================================================

    function applyStatusColors() {
        stepResults.forEach(function (step) {
            var nodeId = nameToNodeId[step.name];
            if (!nodeId) return;

            var nodeEl = document.getElementById('node-' + nodeId);
            if (!nodeEl) return;

            // remove any existing status class
            nodeEl.classList.remove('run-pending', 'run-running', 'run-success', 'run-failed', 'run-skipped');

            // add status class
            var statusClass = 'run-' + (step.status || 'pending');
            nodeEl.classList.add(statusClass);

            // update status badge
            var badge = nodeEl.querySelector('.node-status-badge');
            if (badge) {
                badge.className = 'node-status-badge';
                if (step.status === 'success') {
                    badge.innerHTML = '<i class="bi bi-check-lg"></i>';
                    badge.classList.add('badge-success');
                } else if (step.status === 'failed') {
                    badge.innerHTML = '<i class="bi bi-x-lg"></i>';
                    badge.classList.add('badge-failed');
                } else if (step.status === 'running') {
                    badge.innerHTML = '<i class="bi bi-arrow-repeat"></i>';
                    badge.classList.add('badge-running');
                } else if (step.status === 'skipped') {
                    badge.innerHTML = '<i class="bi bi-dash-lg"></i>';
                    badge.classList.add('badge-skipped');
                }
            }

            // add duration label
            if (step.duration_ms !== null && step.duration_ms !== undefined) {
                var dur = formatDuration(step.duration_ms);
                var durEl = document.createElement('div');
                durEl.className = 'node-duration';
                durEl.textContent = dur;
                var bodyEl = nodeEl.querySelector('.node-body');
                if (bodyEl) bodyEl.appendChild(durEl);
            }
        });
    }

    // =========================================================
    //  Step Detail Highlight
    // =========================================================

    function highlightStepDetail(nodeId) {
        // find step name from nodeId
        var stepName = null;
        for (var name in nameToNodeId) {
            if (nameToNodeId[name] === nodeId) {
                stepName = name;
                break;
            }
        }
        if (!stepName) return;

        // highlight matching step in the right panel
        var items = document.querySelectorAll('.step-result-item');
        items.forEach(function (item) {
            item.classList.remove('active');
            if (item.getAttribute('data-step') === stepName) {
                item.classList.add('active');
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    }

    // =========================================================
    //  Zoom Controls
    // =========================================================

    function bindZoomButtons() {
        var btnIn = document.getElementById('btn-rv-zoom-in');
        var btnOut = document.getElementById('btn-rv-zoom-out');
        var btnReset = document.getElementById('btn-rv-zoom-reset');

        if (btnIn) btnIn.addEventListener('click', function () { if (editor) editor.zoom_in(); });
        if (btnOut) btnOut.addEventListener('click', function () { if (editor) editor.zoom_out(); });
        if (btnReset) btnReset.addEventListener('click', function () { if (editor) editor.zoom_reset(); });
    }

    // =========================================================
    //  Utility
    // =========================================================

    function escHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str || ''));
        return div.innerHTML;
    }

    function formatDuration(ms) {
        if (ms < 1000) return ms + 'ms';
        if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
        return (ms / 60000).toFixed(1) + 'm';
    }

    // =========================================================
    //  Public API
    // =========================================================

    return {
        init: init
    };
})();
