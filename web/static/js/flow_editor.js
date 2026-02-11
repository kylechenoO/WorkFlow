/**
 * WorkFlow Editor - Dual Mode (Form + JSON)
 *
 * Provides bidirectional sync between a form-based procedure editor
 * and a CodeMirror JSON editor.
 */

/* global CodeMirror */

var FlowEditor = (function () {
    'use strict';

    var cmEditor = null;
    var stepCounter = 0;

    /* =========================================================
       Initialization
       ========================================================= */

    function init(initialData) {
        // init CodeMirror
        var textarea = document.getElementById('json-editor');
        if (textarea) {
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
            cmEditor.setSize(null, 450);
        }

        // load initial data
        if (initialData && initialData.procedures) {
            loadProcedures(initialData.procedures);
            if (cmEditor) {
                cmEditor.setValue(JSON.stringify(initialData, null, 4));
            }
        }

        // bind tab switch events
        var formTab = document.getElementById('tab-form');
        var jsonTab = document.getElementById('tab-json');

        if (formTab) {
            formTab.addEventListener('shown.bs.tab', function () {
                syncJsonToForm();
            });
        }

        if (jsonTab) {
            jsonTab.addEventListener('shown.bs.tab', function () {
                syncFormToJson();
                if (cmEditor) {
                    cmEditor.refresh();
                }
            });
        }

        // bind add step button
        var addBtn = document.getElementById('btn-add-step');
        if (addBtn) {
            addBtn.addEventListener('click', function () {
                addStep();
            });
        }
    }

    /* =========================================================
       Form -> JSON Sync
       ========================================================= */

    function syncFormToJson() {
        var data = buildDataFromForm();
        if (cmEditor) {
            cmEditor.setValue(JSON.stringify(data, null, 4));
        }
    }

    function buildDataFromForm() {
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
                    // try to parse JSON values (numbers, booleans, arrays, objects)
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

        return {procedures: procedures};
    }

    /* =========================================================
       JSON -> Form Sync
       ========================================================= */

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

    /* =========================================================
       Step Management
       ========================================================= */

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

    /* =========================================================
       Utilities
       ========================================================= */

    function escHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function getData() {
        // return current data from whichever tab is active
        var jsonPane = document.getElementById('pane-json');
        if (jsonPane && jsonPane.classList.contains('show')) {
            try {
                return JSON.parse(cmEditor.getValue());
            } catch (e) {
                return null;
            }
        }
        return buildDataFromForm();
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
        return null;
    }

    /* =========================================================
       Public API
       ========================================================= */

    return {
        init: init,
        getData: getData,
        validate: validate,
        syncFormToJson: syncFormToJson,
        syncJsonToForm: syncJsonToForm
    };

})();
