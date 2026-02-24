/**
 * WorkFlow Editor - Triple Mode (Form + Visual + JSON)
 *
 * Provides bidirectional sync between a form-based procedure editor,
 * a visual drag-and-drop canvas (Drawflow), and a CodeMirror JSON editor.
 *
 * Data flow:
 *   Visual editor is the canonical source of truth.
 *   Form tab shows all procedures.
 *   JSON tab shows the full data.
 */

/* global CodeMirror, VisualEditor */

var FlowEditor = (function () {
    'use strict';

    var cmEditor = null;
    var stepCounter = 0;
    var lastActiveTab = 'visual'; // 'form', 'visual', 'json'
    var visualInitialized = false;

    // cached snapshot of the last data (from Visual or JSON)
    var _lastCompleteData = null;

    /**
     * Lazily create the CodeMirror instance.
     * Called only when the JSON tab is first shown so that CodeMirror
     * can measure line heights correctly (it must be visible in the DOM).
     */
    function _ensureCmEditor() {
        if (cmEditor) return;
        var textarea = document.getElementById('json-editor');
        if (!textarea) return;
        cmEditor = CodeMirror.fromTextArea(textarea, {
            mode: {name: 'javascript', json: true},
            lineNumbers: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            theme: 'default',
            lineWrapping: true
        });
        cmEditor.setSize(null, '100%');
    }

    // =========================================================
    //  Initialization
    // =========================================================

    function init(initialData) {
        // Do NOT init CodeMirror here — it will be created lazily
        // when the JSON tab is first shown, to avoid the hidden-at-init bug
        // where CodeMirror calculates all line heights as 0.

        // cache initial data as the first complete snapshot
        if (initialData && initialData.procedures) {
            _lastCompleteData = JSON.parse(JSON.stringify(initialData));
            loadProcedures(initialData.procedures);
        }

        // bind tab switch events
        var formTab = document.getElementById('tab-form');
        var jsonTab = document.getElementById('tab-json');
        var visualTab = document.getElementById('tab-visual');

        if (formTab) {
            formTab.addEventListener('shown.bs.tab', function () {
                syncToForm();
                lastActiveTab = 'form';
            });
        }

        if (jsonTab) {
            jsonTab.addEventListener('shown.bs.tab', function () {
                _ensureCmEditor();
                syncToJson();
                lastActiveTab = 'json';
                // Force CodeMirror to recalculate after the tab is fully visible.
                // Use setTimeout to let the browser complete painting and settle
                // element dimensions before CodeMirror measures line heights.
                if (cmEditor) {
                    setTimeout(function () {
                        var val = cmEditor.getValue();
                        cmEditor.setValue(val);
                        cmEditor.refresh();
                    }, 300);
                }
            });
        }

        if (visualTab) {
            visualTab.addEventListener('shown.bs.tab', function () {
                // lazy init visual editor
                if (!visualInitialized && typeof VisualEditor !== 'undefined') {
                    VisualEditor.init('drawflow');
                    visualInitialized = true;
                }
                syncToVisual();
                lastActiveTab = 'visual';
            });
        }

        // init visual editor immediately if it is the default active tab
        var visualPane = document.getElementById('pane-visual');
        if (visualPane && visualPane.classList.contains('active') && typeof VisualEditor !== 'undefined') {
            VisualEditor.init('drawflow');
            visualInitialized = true;
            if (initialData && initialData.procedures && initialData.procedures.length > 0) {
                VisualEditor.importFromJSON(initialData);
                // Refresh connection paths after the browser fully paints the initial layout.
                // On initial load the pane is already "visible" but layout isn't complete yet,
                // so we must always use the delayed path here.
                // Also auto fit-to-view so all nodes are visible regardless of saved positions.
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        setTimeout(function () {
                            VisualEditor.refreshConnections();
                            VisualEditor.fitToView();
                        }, 100);
                    });
                });
            }
        }

        // bind add step button
        var addBtn = document.getElementById('btn-add-step');
        if (addBtn) {
            addBtn.addEventListener('click', function () {
                addStep();
            });
        }
    }

    // =========================================================
    //  Sync helpers — route from lastActiveTab to target
    // =========================================================

    /**
     * Get the current data from whichever tab was last active.
     */
    function getCurrentData() {
        var data;

        if (lastActiveTab === 'json' && cmEditor) {
            try {
                data = JSON.parse(cmEditor.getValue());
            } catch (e) {
                data = { procedures: _readFormProcedures() };
            }
        } else if (lastActiveTab === 'visual' && visualInitialized && typeof VisualEditor !== 'undefined') {
            data = VisualEditor.exportToJSON();
        } else {
            data = { procedures: _readFormProcedures() };
        }

        return data;
    }


    /**
     * Read procedures from the form DOM.
     */
    function _readFormProcedures() {
        var procedures = [];
        var steps = document.querySelectorAll('.procedure-step');

        steps.forEach(function (step) {
            var name = step.querySelector('.step-name').value.trim();
            var mod = step.querySelector('.step-mod').value.trim();
            var method = step.querySelector('.step-method').value.trim();

            // collect params
            var params = {};
            var paramRows = step.querySelectorAll('.param-row');
            paramRows.forEach(function (row) {
                var key = row.querySelector('.param-key').value.trim();
                var val = row.querySelector('.param-val').value.trim();
                if (key) {
                    try {
                        params[key] = JSON.parse(val);
                    } catch (e) {
                        params[key] = val;
                    }
                }
            });

            if (name && mod && method) {
                var proc = {name: name, mod: mod, method: method};
                if (Object.keys(params).length > 0) {
                    proc.params = params;
                }
                procedures.push(proc);
            }
        });

        return procedures;
    }

    function syncToForm() {
        var data = getCurrentData();
        if (data && data.procedures) {
            var container = document.getElementById('steps-container');
            container.innerHTML = '';
            stepCounter = 0;
            loadProcedures(data.procedures);
        }
    }

    function syncToJson() {
        var data = getCurrentData();
        if (cmEditor) {
            // strip _visual metadata — JSON editor always shows clean procedures only
            var clean = { procedures: (data && data.procedures) ? data.procedures : [] };
            cmEditor.setValue(JSON.stringify(clean, null, 4));
        }
    }

    /**
     * Stable djb2 hash of a procedures array.
     * Object keys are sorted before serialization so insertion-order differences
     * don't produce false mismatches (e.g. JSON.parse re-orders keys vs visual export).
     */
    function _hashProcedures(procs) {
        var s = JSON.stringify(procs || [], function (key, val) {
            if (val && typeof val === 'object' && !Array.isArray(val)) {
                return Object.keys(val).sort().reduce(function (acc, k) {
                    acc[k] = val[k];
                    return acc;
                }, {});
            }
            return val;
        });
        var h = 5381;
        for (var i = 0; i < s.length; i++) {
            h = (h * 33) ^ s.charCodeAt(i);
        }
        return h >>> 0;
    }

    function syncToVisual() {
        if (!visualInitialized || typeof VisualEditor === 'undefined') return;

        // if Visual was the last active tab, the canvas already has the correct state
        if (lastActiveTab === 'visual') {
            // still refresh connections in case the pane was hidden and paths are stale
            _scheduleConnectionRefresh();
            return;
        }

        // get current data from Form or JSON tab
        var data = getCurrentData();
        if (!data) return;

        // get current visual state to preserve _connections and _positions
        // (form/json tabs only carry procedures, not visual metadata)
        var visualState = VisualEditor.exportToJSON();

        // hash full procedure content (names + params + method) for accurate change detection.
        // name-only comparison misses param edits made in Form/JSON tab.
        var incomingHash = _hashProcedures(data.procedures);
        var currentHash  = _hashProcedures(visualState.procedures);
        if (incomingHash === currentHash && (data.procedures || []).length > 0) {
            // identical content — skip re-import, just refresh SVG paths
            _scheduleConnectionRefresh();
            return;
        }

        // procedures changed — full re-import needed
        // build name mapping (oldName → newName) to handle renames
        var oldProcs = visualState.procedures || [];
        var newProcs = data.procedures || [];
        var nameMap = {};
        var usedOld = {};
        var usedNew = {};

        // pass 1: exact name matches (unchanged steps)
        for (var i = 0; i < newProcs.length; i++) {
            for (var j = 0; j < oldProcs.length; j++) {
                if (!usedOld[j] && !usedNew[i] && newProcs[i].name === oldProcs[j].name) {
                    nameMap[oldProcs[j].name] = newProcs[i].name;
                    usedOld[j] = true;
                    usedNew[i] = true;
                }
            }
        }

        // pass 2: match remaining by same index + same mod+method (likely renames)
        for (var i = 0; i < newProcs.length; i++) {
            if (usedNew[i]) continue;
            if (i < oldProcs.length && !usedOld[i] &&
                newProcs[i].mod === oldProcs[i].mod &&
                newProcs[i].method === oldProcs[i].method) {
                nameMap[oldProcs[i].name] = newProcs[i].name;
                usedOld[i] = true;
                usedNew[i] = true;
            }
        }

        // detect if the order changed (same step names, different sequence)
        var orderChanged = false;
        if (oldProcs.length === newProcs.length && oldProcs.length > 1) {
            var sameNames = oldProcs.every(function (p) {
                return newProcs.some(function (np) { return np.name === p.name; });
            });
            if (sameNames) {
                for (var k = 0; k < oldProcs.length; k++) {
                    if (oldProcs[k].name !== newProcs[k].name) {
                        orderChanged = true;
                        break;
                    }
                }
            }
        }

        // if order changed, build new sequential connections from new array order
        if (orderChanged && !data._connections) {
            var seqConns = [];
            for (var k = 1; k < newProcs.length; k++) {
                seqConns.push({ from: newProcs[k - 1].name, to: newProcs[k].name });
            }
            data._connections = seqConns;
        }

        // translate _connections using nameMap (only when order didn't change)
        if (!orderChanged && !data._connections && visualState._connections && visualState._connections.length > 0) {
            var mapped = [];
            visualState._connections.forEach(function (conn) {
                var from = nameMap[conn.from] || conn.from;
                var to   = nameMap[conn.to]   || conn.to;
                // only keep connection if both endpoints exist in new procedures
                var fromExists = newProcs.some(function (p) { return p.name === from; });
                var toExists   = newProcs.some(function (p) { return p.name === to; });
                if (fromExists && toExists) {
                    mapped.push({ from: from, to: to });
                }
            });
            if (mapped.length > 0) {
                data._connections = mapped;
            }
        }

        // translate _positions using nameMap (skip when order changed — auto-layout instead)
        if (!orderChanged && !data._positions && visualState._positions && Object.keys(visualState._positions).length > 0) {
            var mappedPos = {};
            for (var oldName in visualState._positions) {
                var newName = nameMap[oldName] || oldName;
                // only keep position if step exists in new procedures
                var exists = newProcs.some(function (p) { return p.name === newName; });
                if (exists) {
                    mappedPos[newName] = visualState._positions[oldName];
                }
            }
            if (Object.keys(mappedPos).length > 0) {
                data._positions = mappedPos;
            }
        }

        VisualEditor.importFromJSON(data);
        _scheduleConnectionRefresh();
    }

    /**
     * Schedule a connection path refresh after the visual pane is fully visible.
     * Bootstrap's fade transition keeps the pane display:none (opacity:0) even
     * after shown.bs.tab fires — we must wait for the opacity transition to finish
     * before getBoundingClientRect() returns real coordinates.
     */
    function _scheduleConnectionRefresh() {
        if (typeof VisualEditor === 'undefined' || !VisualEditor.refreshConnections) return;

        var pane = document.getElementById('pane-visual');
        if (!pane) return;

        // If pane is already fully visible (display != none, opacity settled), refresh now
        var style = window.getComputedStyle(pane);
        if (style.display !== 'none' && parseFloat(style.opacity) > 0.9) {
            VisualEditor.refreshConnections();
            return;
        }

        // Otherwise wait for the transitionend on the pane (Bootstrap fade)
        var done = false;
        function onTransitionEnd() {
            if (done) return;
            done = true;
            pane.removeEventListener('transitionend', onTransitionEnd);
            VisualEditor.refreshConnections();
        }

        pane.addEventListener('transitionend', onTransitionEnd);

        // Safety fallback — if transitionend never fires (e.g. no CSS transition),
        // poll until the pane is visible, then refresh
        var attempts = 0;
        function poll() {
            if (done) return;
            attempts++;
            var s = window.getComputedStyle(pane);
            if (s.display !== 'none' && parseFloat(s.opacity) > 0.9) {
                done = true;
                pane.removeEventListener('transitionend', onTransitionEnd);
                VisualEditor.refreshConnections();
            } else if (attempts < 20) {
                setTimeout(poll, 50);
            }
        }
        setTimeout(poll, 50);
    }

    // =========================================================
    //  Form -> JSON (legacy, kept for form-only builds)
    // =========================================================

    function syncFormToJson() {
        var data = { procedures: _readFormProcedures() };
        if (cmEditor) {
            cmEditor.setValue(JSON.stringify(data, null, 4));
        }
    }

    // =========================================================
    //  JSON -> Form Sync
    // =========================================================

    function syncJsonToForm() {
        if (!cmEditor) return;

        try {
            var data = JSON.parse(cmEditor.getValue());
            if (data && data.procedures) {
                // clear existing steps
                var container = document.getElementById('steps-container');
                container.innerHTML = '';
                stepCounter = 0;

                loadProcedures(data.procedures);
            }
        } catch (e) {
            // JSON parse error - keep form as is
            console.warn('JSON parse error:', e.message);
        }
    }

    function loadProcedures(procedures) {
        procedures.forEach(function (proc) {
            addStep(proc);
        });
    }

    // =========================================================
    //  Step Management
    // =========================================================

    function addStep(data) {
        stepCounter++;
        var idx = stepCounter;

        var container = document.getElementById('steps-container');
        var div = document.createElement('div');
        div.className = 'procedure-step';
        div.setAttribute('data-step', idx);

        var name = (data && data.name) || '';
        var mod = (data && data.mod) || '';
        var method = (data && data.method) || '';
        var params = (data && data.params) || {};

        var html = '';
        html += '<div class="step-header">';
        html += '  <span class="step-number">Step ' + idx + '</span>';
        html += '  <button type="button" class="btn btn-sm btn-outline-danger btn-remove-step" title="Remove step">';
        html += '    <i class="bi bi-trash"></i>';
        html += '  </button>';
        html += '</div>';
        html += '<div class="row g-2 mb-2">';
        html += '  <div class="col-md-4">';
        html += '    <input type="text" class="form-control form-control-sm step-name" placeholder="Step name" value="' + escHtml(name) + '">';
        html += '  </div>';
        html += '  <div class="col-md-4">';
        html += '    <input type="text" class="form-control form-control-sm step-mod" placeholder="Module (e.g. common.Http)" value="' + escHtml(mod) + '">';
        html += '  </div>';
        html += '  <div class="col-md-4">';
        html += '    <input type="text" class="form-control form-control-sm step-method" placeholder="Method (e.g. get)" value="' + escHtml(method) + '">';
        html += '  </div>';
        html += '</div>';
        html += '<div class="params-container">';
        html += '  <label class="form-label mb-1" style="font-size:0.8rem;color:#6c757d;">Parameters</label>';

        // render existing params
        var paramKeys = Object.keys(params);
        if (paramKeys.length > 0) {
            paramKeys.forEach(function (key) {
                var val = params[key];
                var valStr = (typeof val === 'string') ? val : JSON.stringify(val);
                html += paramRowHtml(key, valStr);
            });
        } else {
            html += paramRowHtml('', '');
        }

        html += '</div>';
        html += '<button type="button" class="btn btn-sm btn-outline-secondary mt-1 btn-add-param">';
        html += '  <i class="bi bi-plus"></i> Add param';
        html += '</button>';

        div.innerHTML = html;
        container.appendChild(div);

        // bind remove step
        div.querySelector('.btn-remove-step').addEventListener('click', function () {
            div.remove();
            renumberSteps();
        });

        // bind add param
        div.querySelector('.btn-add-param').addEventListener('click', function () {
            var paramsDiv = div.querySelector('.params-container');
            var tmp = document.createElement('div');
            tmp.innerHTML = paramRowHtml('', '');
            var newRow = tmp.firstElementChild;
            paramsDiv.appendChild(newRow);
            bindParamRemove(newRow);
        });

        // bind existing param remove buttons
        div.querySelectorAll('.btn-remove-param').forEach(function (btn) {
            bindParamRemove(btn.closest('.param-row'));
        });
    }

    function paramRowHtml(key, val) {
        var html = '<div class="param-row">';
        html += '  <input type="text" class="form-control form-control-sm param-key" placeholder="Key" value="' + escHtml(key) + '">';
        html += '  <input type="text" class="form-control form-control-sm param-val" placeholder="Value" value="' + escHtml(val) + '">';
        html += '  <button type="button" class="btn btn-sm btn-outline-danger btn-remove-param" title="Remove">';
        html += '    <i class="bi bi-x"></i>';
        html += '  </button>';
        html += '</div>';
        return html;
    }

    function bindParamRemove(row) {
        var btn = row.querySelector('.btn-remove-param');
        if (btn) {
            btn.addEventListener('click', function () {
                row.remove();
            });
        }
    }

    function renumberSteps() {
        var steps = document.querySelectorAll('.procedure-step');
        steps.forEach(function (step, i) {
            step.querySelector('.step-number').textContent = 'Step ' + (i + 1);
        });
        stepCounter = steps.length;
    }

    // =========================================================
    //  Utilities
    // =========================================================

    function escHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML.replace(/"/g, '&quot;');
    }

    function getData() {
        // return current data from whichever tab is active
        var data;
        var jsonPane = document.getElementById('pane-json');
        if (jsonPane && jsonPane.classList.contains('show')) {
            try {
                data = JSON.parse(cmEditor.getValue());
            } catch (e) {
                return null;
            }
            // JSON tab stores a bare array; normalise to { procedures: [...] }
            if (Array.isArray(data)) {
                data = { procedures: data };
            }
            return data;
        }

        var visualPane = document.getElementById('pane-visual');
        if (visualPane && visualPane.classList.contains('show') && visualInitialized && typeof VisualEditor !== 'undefined') {
            data = VisualEditor.exportToJSON();
        } else {
            data = { procedures: _readFormProcedures() };
        }

        return data;
    }

    function validate() {
        var data = getData();
        if (!data || !data.procedures || data.procedures.length === 0) {
            return 'At least one procedure step is required.';
        }

        for (var i = 0; i < data.procedures.length; i++) {
            var p = data.procedures[i];
            if (!p.name || !p.mod || !p.method) {
                return 'Step ' + (i + 1) + ': name, mod, and method are required.';
            }
        }

        // visual editor connection validation
        var visualPane = document.getElementById('pane-visual');
        if (visualPane && visualPane.classList.contains('show') &&
            visualInitialized && typeof VisualEditor !== 'undefined' &&
            typeof VisualEditor.validate === 'function') {
            var visualErr = VisualEditor.validate();
            if (visualErr) return visualErr;
        }

        return null;
    }

    // =========================================================
    //  Public API
    // =========================================================

    return {
        init: init,
        getData: getData,
        validate: validate,
        syncFormToJson: syncFormToJson,
        syncJsonToForm: syncJsonToForm
    };

})();
