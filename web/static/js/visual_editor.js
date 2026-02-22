/**
 * Visual Flow Editor — Drag-and-drop workflow builder using Drawflow.
 *
 * Provides a three-panel visual editor:
 *   Left:   Module palette (draggable blocks)
 *   Center: Drawflow canvas (nodes + connections)
 *   Right:  Properties panel (edit selected node)
 *
 * Depends on: Drawflow.js, ModuleRegistry
 */

/* global Drawflow, ModuleRegistry */

var VisualEditor = (function () {
    'use strict';

    var editor = null;
    var selectedNodeId = null;
    var nodeCounter = 0;
    var initialized = false;

    // map: drawflow node id -> step data
    var nodeDataMap = {};

    // in-memory visual state: positions and connections, keyed by step name
    // never serialized to JSON — survives tab switches within a page session
    var _visualCache = {
        positions: {},    // stepName -> { x, y }
        connections: []   // [{ from: stepName, to: stepName }, ...]
    };

    // =========================================================
    //  Initialization
    // =========================================================

    function init(containerId) {
        if (initialized) return;

        var container = document.getElementById(containerId);
        if (!container) return;

        // create drawflow instance
        editor = new Drawflow(container);
        editor.reroute = true;
        editor.start();

        // build palette
        buildPalette('visual-palette');

        // bind canvas events
        editor.on('nodeSelected', function (nodeId) {
            selectedNodeId = nodeId;
            showProperties(nodeId);
        });

        editor.on('nodeUnselected', function () {
            selectedNodeId = null;
            hideProperties();
        });

        editor.on('nodeRemoved', function (nodeId) {
            delete nodeDataMap[nodeId];
            if (selectedNodeId === nodeId) {
                selectedNodeId = null;
                hideProperties();
            }
            recalculateOrder();
        });

        editor.on('connectionCreated', function (info) {
            onConnectionCreated(info);
        });

        editor.on('connectionRemoved', function () {
            recalculateOrder();
        });

        // bind canvas drag-drop
        var canvasEl = container;
        canvasEl.addEventListener('dragover', function (e) {
            e.preventDefault();
        });
        canvasEl.addEventListener('drop', function (e) {
            e.preventDefault();
            onCanvasDrop(e, canvasEl);
        });

        // bind zoom buttons
        bindZoomButtons();

        // bind delete key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                // only if visual tab is active and no input focused
                var visualPane = document.getElementById('pane-visual');
                if (!visualPane || !visualPane.classList.contains('show')) return;
                var active = document.activeElement;
                if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT')) return;
                if (selectedNodeId) {
                    editor.removeNodeId('node-' + selectedNodeId);
                }
            }
        });

        initialized = true;
    }

    // =========================================================
    //  Palette
    // =========================================================

    function buildPalette(panelId) {
        var panel = document.getElementById(panelId);
        if (!panel) return;

        var categories = ModuleRegistry.getCategories();

        // search input
        var html = '<div class="palette-search">';
        html += '<input type="text" id="palette-search-input" class="form-control form-control-sm" placeholder="Search...">';
        html += '</div>';

        categories.forEach(function (cat) {
            html += '<div class="palette-category" data-cat-group="' + cat.id + '">';
            html += '<div class="palette-category-header" data-cat="' + cat.id + '">';
            html += '<i class="bi ' + cat.icon + '"></i>';
            html += '<span>' + cat.label + '</span>';
            html += '<i class="bi bi-chevron-down chevron"></i>';
            html += '</div>';
            html += '<div class="palette-items" data-cat-items="' + cat.id + '">';

            for (var modName in cat.modules) {
                var mod = cat.modules[modName];
                for (var methodName in mod.methods) {
                    var m = mod.methods[methodName];
                    var searchText = (modName + '.' + methodName).toLowerCase();
                    html += '<div class="palette-item" draggable="true"';
                    html += ' style="--module-color:' + mod.color + '"';
                    html += ' data-mod="' + mod.mod + '"';
                    html += ' data-module-name="' + modName + '"';
                    html += ' data-method="' + methodName + '"';
                    html += ' data-color="' + mod.color + '"';
                    html += ' data-icon="' + mod.icon + '"';
                    html += ' data-search="' + searchText + '"';
                    html += ' title="' + escHtml(m.label || methodName) + '">';
                    html += '<i class="bi ' + mod.icon + '"></i>';
                    html += '<span>' + modName + '.' + methodName + '</span>';
                    html += '</div>';
                }
            }

            html += '</div></div>';
        });

        panel.innerHTML = html;

        // bind drag events on palette items
        panel.querySelectorAll('.palette-item').forEach(function (item) {
            item.addEventListener('dragstart', function (e) {
                e.dataTransfer.setData('application/json', JSON.stringify({
                    mod: item.getAttribute('data-mod'),
                    moduleName: item.getAttribute('data-module-name'),
                    method: item.getAttribute('data-method'),
                    color: item.getAttribute('data-color'),
                    icon: item.getAttribute('data-icon')
                }));
            });
        });

        // bind category collapse/expand
        panel.querySelectorAll('.palette-category-header').forEach(function (header) {
            header.addEventListener('click', function () {
                var catId = header.getAttribute('data-cat');
                var items = panel.querySelector('[data-cat-items="' + catId + '"]');
                if (items.style.display === 'none') {
                    items.style.display = '';
                    header.classList.remove('collapsed');
                } else {
                    items.style.display = 'none';
                    header.classList.add('collapsed');
                }
            });
        });

        // bind search filter
        var searchInput = document.getElementById('palette-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                var q = searchInput.value.toLowerCase().trim();
                var allItems = panel.querySelectorAll('.palette-item');
                var allCats = panel.querySelectorAll('.palette-category');

                allItems.forEach(function (item) {
                    var text = item.getAttribute('data-search') || '';
                    item.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
                });

                // show/hide category if it has visible items
                allCats.forEach(function (cat) {
                    var items = cat.querySelectorAll('.palette-item');
                    var hasVisible = false;
                    items.forEach(function (item) {
                        if (item.style.display !== 'none') hasVisible = true;
                    });
                    cat.style.display = hasVisible ? '' : 'none';

                    // expand categories when searching, restore when cleared
                    var catItems = cat.querySelector('.palette-items');
                    if (q && catItems) {
                        catItems.style.display = '';
                        var header = cat.querySelector('.palette-category-header');
                        if (header) header.classList.remove('collapsed');
                    }
                });
            });
        }
    }

    // =========================================================
    //  Canvas Drop
    // =========================================================

    function onCanvasDrop(e, canvasEl) {
        var raw = e.dataTransfer.getData('application/json');
        if (!raw) return;

        try {
            var dropData = JSON.parse(raw);
        } catch (err) {
            return;
        }

        // convert page coords to canvas coords
        var rect = canvasEl.getBoundingClientRect();
        var x = (e.clientX - rect.left) / (editor.zoom || 1);
        var y = (e.clientY - rect.top) / (editor.zoom || 1);

        // account for canvas translation
        var preX = editor.precanvas.style.transform;
        if (preX) {
            var m = preX.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/);
            if (m) {
                x -= parseFloat(m[1]) / (editor.zoom || 1);
                y -= parseFloat(m[2]) / (editor.zoom || 1);
            }
        }

        addNode(dropData.mod, dropData.moduleName, dropData.method, dropData.color, dropData.icon, x, y);
    }

    // =========================================================
    //  Node Management
    // =========================================================

    function addNode(mod, moduleName, method, color, icon, x, y, stepName, params) {
        nodeCounter++;
        var name = stepName || (moduleName.toLowerCase() + '_' + method + '_' + nodeCounter);
        var nodeParams = params || ModuleRegistry.getDefaultParams(mod, method);
        color = color || '#6c757d';
        icon = icon || 'bi-gear';

        // build node html
        var nodeHtml = '';
        nodeHtml += '<div class="node-order">' + nodeCounter + '</div>';
        nodeHtml += '<div class="node-delete" onclick="VisualEditor.deleteNode(this)" title="Delete">&times;</div>';
        nodeHtml += '<div class="node-header" style="background:' + color + ';">';
        nodeHtml += '<i class="bi ' + icon + '" style="font-size:10px;"></i>';
        nodeHtml += '<span>' + moduleName + '</span>';
        nodeHtml += '</div>';
        nodeHtml += '<div class="node-body">';
        nodeHtml += '<div class="node-title">' + escHtml(name) + '</div>';
        nodeHtml += '<div class="node-method">' + method + '</div>';
        nodeHtml += '</div>';

        // add node: name, inputs, outputs, x, y, className, data, html
        var nodeId = editor.addNode(
            name,              // name
            1,                 // inputs
            1,                 // outputs
            x,                 // pos_x
            y,                 // pos_y
            '',                // class
            {},                // data (drawflow internal)
            nodeHtml           // html
        );

        // store our custom data
        nodeDataMap[nodeId] = {
            stepName: name,
            mod: mod,
            moduleName: moduleName,
            method: method,
            color: color,
            icon: icon,
            params: nodeParams
        };

        recalculateOrder();
        return nodeId;
    }

    function deleteNode(btnEl) {
        // find the drawflow-node parent
        var nodeEl = btnEl.closest('.drawflow-node');
        if (!nodeEl) return;
        var nodeId = nodeEl.id.replace('node-', '');
        editor.removeNodeId('node-' + nodeId);
    }

    // =========================================================
    //  JSON Parsing Helper
    // =========================================================

    /**
     * Parse a JSON string loosely — handles single-quoted Python-style dicts.
     * Falls back to raw string if all parsing fails.
     */
    function _parseJsonLoose(raw) {
        if (!raw) return raw;
        // try strict JSON first
        try { return JSON.parse(raw); } catch (e) {}
        // try replacing single quotes with double quotes (Python dict syntax)
        try {
            var fixed = raw.replace(/'/g, '"');
            return JSON.parse(fixed);
        } catch (e) {}
        // return raw string as fallback
        return raw;
    }

    // =========================================================
    //  Return Key Parsing
    // =========================================================

    /**
     * Extract variable names from a returns.desc string.
     * e.g. "Request result with status_code, data, headers" → ['status_code', 'data', 'headers']
     * e.g. "Filtered data with count"                       → ['count']
     * e.g. "Result with list of dicts in data key"          → ['data']
     */
    function parseReturnKeys(returnsObj) {
        if (!returnsObj || !returnsObj.desc) return [];
        var desc = returnsObj.desc;

        // try to extract words after "with" keyword — match identifiers (word chars + underscore)
        var withMatch = desc.match(/\bwith\b(.+)/i);
        if (withMatch) {
            var afterWith = withMatch[1];
            // pull out all snake_case/camelCase identifiers (skip short filler words)
            var tokens = afterWith.match(/\b([a-z_][a-z0-9_]{1,})\b/gi) || [];
            // filter out common English filler words
            var fillers = {
                'of': 1, 'in': 1, 'the': 1, 'and': 1, 'or': 1, 'a': 1, 'an': 1,
                'list': 1, 'key': 1, 'keys': 1, 'value': 1, 'values': 1,
                'result': 1, 'results': 1, 'dict': 1, 'dicts': 1, 'item': 1,
                'items': 1, 'number': 1, 'string': 1, 'boolean': 1, 'object': 1
            };
            var keys = tokens.filter(function (t) {
                return !fillers[t.toLowerCase()];
            });
            if (keys.length > 0) return keys;
        }

        // fallback: all snake_case identifiers in desc
        var allTokens = desc.match(/\b([a-z_][a-z0-9_]{2,})\b/g) || [];
        return allTokens.filter(function (t) {
            return t !== 'dict' && t !== 'list' && t !== 'result';
        });
    }

    /**
     * Get the return keys for a module/method from the registry.
     */
    function getMethodReturnKeys(mod, method) {
        var info = ModuleRegistry.findByMod(mod);
        if (!info || !info.module.methods[method]) return [];
        var meth = info.module.methods[method];
        return parseReturnKeys(meth.returns);
    }

    /**
     * Get connected source node IDs (nodes feeding into nodeId via connections).
     */
    function getSourceNodeIds(nodeId) {
        if (!editor) return [];
        var exportData = editor.export();
        var nodes = exportData.drawflow.Home.data;
        var node = nodes[nodeId];
        if (!node) return [];
        var sourceIds = [];
        for (var inputKey in node.inputs) {
            var inp = node.inputs[inputKey];
            if (inp && inp.connections) {
                inp.connections.forEach(function (conn) {
                    var sid = parseInt(conn.node);
                    if (sourceIds.indexOf(sid) === -1) sourceIds.push(sid);
                });
            }
        }
        return sourceIds;
    }

    // =========================================================
    //  Properties Panel
    // =========================================================

    function showProperties(nodeId) {
        var placeholder = document.getElementById('properties-placeholder');
        var formDiv = document.getElementById('properties-form');
        if (!placeholder || !formDiv) return;

        var data = nodeDataMap[nodeId];
        if (!data) return;

        placeholder.style.display = 'none';
        formDiv.style.display = '';

        // get param schema
        var info = ModuleRegistry.findByMod(data.mod);
        var schema = {};
        if (info && info.module.methods[data.method]) {
            schema = info.module.methods[data.method].params || {};
        }

        // get existing step names for @reference suggestions
        var stepNames = [];
        for (var nid in nodeDataMap) {
            if (nid != nodeId) {
                stepNames.push(nodeDataMap[nid].stepName);
            }
        }

        var html = '';
        html += '<div class="prop-header">' + escHtml(data.moduleName + '.' + data.method) + '</div>';

        // step name
        html += '<div class="prop-section">';
        html += '<label>Step Name</label>';
        html += '<input type="text" id="prop-name" value="' + escHtml(data.stepName) + '">';
        html += '</div>';

        // module (readonly)
        html += '<div class="prop-section">';
        html += '<label>Module</label>';
        html += '<input type="text" value="' + escHtml(data.mod) + '" readonly style="background:#f0f0f0;">';
        html += '</div>';

        // method (readonly — fixed at drag time)
        html += '<div class="prop-section">';
        html += '<label>Method</label>';
        html += '<input type="text" value="' + escHtml(data.method) + '" readonly style="background:#f0f0f0;">';
        html += '</div>';

        html += '<div class="prop-divider"></div>';
        html += '<div style="font-size:11px;font-weight:600;color:#6c757d;margin-bottom:8px;">PARAMETERS</div>';

        // params — render from schema if available, else fall back to stored params
        var schemaKeys = Object.keys(schema);
        if (schemaKeys.length > 0) {
            // schema-driven rendering
            for (var paramName in schema) {
                var ps = schema[paramName];
                var curVal = data.params.hasOwnProperty(paramName) ? data.params[paramName] : (ps.default !== undefined ? ps.default : '');
                var valStr = (typeof curVal === 'object' && curVal !== null) ? JSON.stringify(curVal) : String(curVal === null ? '' : curVal);

                html += '<div class="prop-section">';
                html += '<label>' + paramName;
                if (ps.required) html += ' <span style="color:#dc3545;">*</span>';
                html += '</label>';

                if (ps.type === 'boolean') {
                    var checked = (curVal === true || curVal === 'true') ? ' checked' : '';
                    html += '<input type="checkbox" class="prop-param" data-param="' + paramName + '" data-type="boolean"' + checked + ' style="width:auto;">';
                } else if (ps.type === 'json' || ps.type === 'ref') {
                    html += '<textarea class="prop-param" data-param="' + paramName + '" data-type="' + ps.type + '">' + escHtml(valStr) + '</textarea>';
                    // ref suggestion
                    if (ps.type === 'ref' && stepNames.length > 0) {
                        html += '<div class="prop-desc">Refs: ' + stepNames.map(function (s) { return '@' + s; }).join(', ') + '</div>';
                    }
                } else {
                    html += '<input type="text" class="prop-param" data-param="' + paramName + '" data-type="' + ps.type + '" value="' + escHtml(valStr) + '">';
                }

                if (ps.desc) {
                    html += '<div class="prop-desc">' + escHtml(ps.desc) + '</div>';
                }
                html += '</div>';
            }
        } else {
            // no schema — render stored params as generic text/checkbox inputs
            var storedParams = data.params || {};
            if (Object.keys(storedParams).length === 0) {
                html += '<div style="font-size:11px;color:#adb5bd;">No parameters</div>';
            } else {
                for (var pName in storedParams) {
                    var pVal = storedParams[pName];
                    var pType = typeof pVal;
                    var pValStr = (pType === 'object' && pVal !== null) ? JSON.stringify(pVal) : String(pVal === null ? '' : pVal);
                    html += '<div class="prop-section">';
                    html += '<label>' + escHtml(pName) + '</label>';
                    if (pType === 'boolean') {
                        var pChecked = pVal ? ' checked' : '';
                        html += '<input type="checkbox" class="prop-param" data-param="' + escHtml(pName) + '" data-type="boolean"' + pChecked + ' style="width:auto;">';
                    } else if (pType === 'object') {
                        html += '<textarea class="prop-param" data-param="' + escHtml(pName) + '" data-type="json">' + escHtml(pValStr) + '</textarea>';
                    } else {
                        html += '<input type="text" class="prop-param" data-param="' + escHtml(pName) + '" data-type="' + pType + '" value="' + escHtml(pValStr) + '">';
                    }
                    html += '</div>';
                }
            }
        }

        // --- current step returns ---
        var currentReturnKeys = getMethodReturnKeys(data.mod, data.method);
        if (currentReturnKeys.length > 0) {
            html += '<div class="prop-divider"></div>';
            html += '<div style="font-size:11px;font-weight:600;color:#6c757d;margin-bottom:6px;">RETURNS</div>';
            html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px;">';
            currentReturnKeys.forEach(function (k) {
                html += '<code style="font-size:11px;background:#e9ecef;padding:1px 5px;border-radius:3px;">' + escHtml(k) + '</code>';
            });
            html += '</div>';
        }

        // --- previous step refs ---
        var sourceIds = getSourceNodeIds(nodeId);
        if (sourceIds.length > 0) {
            html += '<div class="prop-divider"></div>';
            html += '<div style="font-size:11px;font-weight:600;color:#6c757d;margin-bottom:6px;">PREV STEP REFS</div>';
            sourceIds.forEach(function (sid) {
                var srcData = nodeDataMap[sid];
                if (!srcData) return;
                var srcKeys = getMethodReturnKeys(srcData.mod, srcData.method);
                html += '<div style="font-size:11px;color:#495057;margin-bottom:3px;">';
                html += '<span style="color:#6c757d;">@' + escHtml(srcData.stepName) + '</span>';
                if (srcKeys.length > 0) {
                    html += ' → ';
                    html += srcKeys.map(function (k) {
                        return '<code style="font-size:11px;background:#e9ecef;padding:1px 5px;border-radius:3px;">.' + escHtml(k) + '</code>';
                    }).join(' ');
                }
                html += '</div>';
            });
        }

        formDiv.innerHTML = html;

        // bind name change
        var nameInput = document.getElementById('prop-name');
        if (nameInput) {
            nameInput.addEventListener('change', function () {
                data.stepName = nameInput.value.trim() || data.stepName;
                updateNodeDisplay(nodeId, data);
            });
        }

        // bind param changes
        formDiv.querySelectorAll('.prop-param').forEach(function (input) {
            var paramName = input.getAttribute('data-param');
            var paramType = input.getAttribute('data-type');

            var evtType = paramType === 'boolean' ? 'change' : 'blur';
            input.addEventListener(evtType, function () {
                if (paramType === 'boolean') {
                    data.params[paramName] = input.checked;
                } else if (paramType === 'json' || paramType === 'ref') {
                    var rawVal = input.value.trim();
                    var parsed = _parseJsonLoose(rawVal);
                    data.params[paramName] = parsed;
                } else if (paramType === 'number') {
                    var num = parseFloat(input.value);
                    data.params[paramName] = isNaN(num) ? input.value : num;
                } else {
                    data.params[paramName] = input.value;
                }
            });
        });
    }

    function hideProperties() {
        var placeholder = document.getElementById('properties-placeholder');
        var formDiv = document.getElementById('properties-form');
        if (placeholder) placeholder.style.display = '';
        if (formDiv) formDiv.style.display = 'none';
    }

    function updateNodeDisplay(nodeId, data) {
        var nodeEl = document.getElementById('node-' + nodeId);
        if (!nodeEl) return;
        var titleEl = nodeEl.querySelector('.node-title');
        var methodEl = nodeEl.querySelector('.node-method');
        if (titleEl) titleEl.textContent = data.stepName;
        if (methodEl) methodEl.textContent = data.method;
    }

    // =========================================================
    //  Connections
    // =========================================================

    function onConnectionCreated(info) {
        recalculateOrder();

        // auto-suggest @reference in target node
        var sourceId = parseInt(info.output_id);
        var targetId = parseInt(info.input_id);
        var sourceData = nodeDataMap[sourceId];
        var targetData = nodeDataMap[targetId];

        if (!sourceData || !targetData) return;

        // find first 'ref' type param in target that is empty or '@'
        var paramInfo = ModuleRegistry.findByMod(targetData.mod);
        if (!paramInfo) return;
        var methodSchema = paramInfo.module.methods[targetData.method];
        if (!methodSchema) return;

        for (var pName in methodSchema.params) {
            if (methodSchema.params[pName].type === 'ref') {
                var curVal = targetData.params[pName];
                if (!curVal || curVal === '@' || curVal === '') {
                    targetData.params[pName] = '@' + sourceData.stepName;
                    // refresh properties if this node is selected
                    if (selectedNodeId === targetId) {
                        showProperties(targetId);
                    }
                    break;
                }
            }
        }
    }

    // =========================================================
    //  Execution Order
    // =========================================================

    function recalculateOrder() {
        if (!editor) return;

        var exportData = editor.export();
        var nodes = exportData.drawflow.Home.data;
        var nodeIds = Object.keys(nodes).map(Number);

        // build adjacency: who depends on whom
        var inDegree = {};
        var adjList = {};
        nodeIds.forEach(function (id) { inDegree[id] = 0; adjList[id] = []; });

        nodeIds.forEach(function (id) {
            var node = nodes[id];
            // check all input ports (input_1, input_2, ...)
            for (var inputKey in node.inputs) {
                if (node.inputs[inputKey] && node.inputs[inputKey].connections) {
                    node.inputs[inputKey].connections.forEach(function (conn) {
                        var fromId = parseInt(conn.node);
                        // avoid duplicate edges
                        if (adjList[fromId].indexOf(id) === -1) {
                            adjList[fromId].push(id);
                            inDegree[id]++;
                        }
                    });
                }
            }
        });

        // topological sort (Kahn's algorithm)
        // prioritize Start nodes at the beginning
        var queue = [];
        nodeIds.forEach(function (id) {
            if (inDegree[id] === 0) queue.push(id);
        });

        var order = [];
        while (queue.length > 0) {
            // sort by x position for stable ordering
            queue.sort(function (a, b) {
                return (nodes[a].pos_x || 0) - (nodes[b].pos_x || 0);
            });
            var curr = queue.shift();
            order.push(curr);
            (adjList[curr] || []).forEach(function (next) {
                inDegree[next]--;
                if (inDegree[next] === 0) queue.push(next);
            });
        }

        // any remaining (cycles) - add by x position
        nodeIds.forEach(function (id) {
            if (order.indexOf(id) === -1) order.push(id);
        });

        // update order badges
        order.forEach(function (id, idx) {
            var nodeEl = document.getElementById('node-' + id);
            if (nodeEl) {
                var badge = nodeEl.querySelector('.node-order');
                if (badge) badge.textContent = idx + 1;
            }
            if (nodeDataMap[id]) {
                nodeDataMap[id]._order = idx;
            }
        });
    }

    // =========================================================
    //  Import / Export
    // =========================================================

    function exportToJSON() {
        if (!editor) return { procedures: [] };

        var exportData = editor.export();
        var nodes = exportData.drawflow.Home.data;
        var nodeIds = Object.keys(nodes).map(Number);

        // sort by execution order
        nodeIds.sort(function (a, b) {
            var oa = nodeDataMap[a] ? (nodeDataMap[a]._order || 0) : 0;
            var ob = nodeDataMap[b] ? (nodeDataMap[b]._order || 0) : 0;
            return oa - ob;
        });

        var procedures = [];

        // save positions into in-memory cache (not exported to JSON)
        _visualCache.positions = {};
        _visualCache.connections = [];
        var seenPairs = {};

        nodeIds.forEach(function (id) {
            var data = nodeDataMap[id];
            if (!data) return;

            var node = nodes[id];
            var proc = {
                name: data.stepName,
                mod: data.mod,
                method: data.method
            };

            // include non-empty params
            var cleanParams = {};
            for (var k in data.params) {
                var v = data.params[k];
                if (v !== '' && v !== null && v !== undefined) {
                    cleanParams[k] = v;
                }
            }
            if (Object.keys(cleanParams).length > 0) {
                proc.params = cleanParams;
            }

            procedures.push(proc);

            // cache node position
            _visualCache.positions[data.stepName] = { x: node.pos_x, y: node.pos_y };

            // cache outgoing connections
            for (var outKey in node.outputs) {
                var out = node.outputs[outKey];
                if (out && out.connections) {
                    out.connections.forEach(function (conn) {
                        var tgtData = nodeDataMap[parseInt(conn.node)];
                        if (!tgtData) return;
                        var pairKey = data.stepName + '->' + tgtData.stepName;
                        if (!seenPairs[pairKey]) {
                            _visualCache.connections.push({ from: data.stepName, to: tgtData.stepName });
                            seenPairs[pairKey] = true;
                        }
                    });
                }
            }
        });

        // return procedures + connections + positions (persist across page loads)
        var result = { procedures: procedures };
        if (_visualCache.connections.length > 0) {
            result._connections = _visualCache.connections.slice();
        }
        if (Object.keys(_visualCache.positions).length > 0) {
            result._positions = JSON.parse(JSON.stringify(_visualCache.positions));
        }
        return result;
    }

    function importFromJSON(data) {
        if (!editor) return;
        if (!data || !data.procedures) return;

        // clear canvas
        editor.clear();
        nodeDataMap = {};
        nodeCounter = 0;
        selectedNodeId = null;
        hideProperties();

        if (data.procedures.length === 0) return;

        // seed connections from top-level _connections (persisted in workflow JSON)
        if (data._connections && data._connections.length > 0) {
            _visualCache.connections = data._connections.slice();
        }

        // seed positions from top-level _positions (persisted in workflow JSON) — always override cache
        if (data._positions) {
            for (var pKey in data._positions) {
                _visualCache.positions[pKey] = data._positions[pKey];
            }
        }

        // seed cache from legacy _visual data if present (backward-compat for old saves)
        // also seed connections from _visual._connections if cache is empty
        if (data._visual) {
            var legacyConns = data._visual._connections || [];
            for (var stepKey in data._visual) {
                if (stepKey === '_connections') continue;
                if (!_visualCache.positions[stepKey]) {
                    _visualCache.positions[stepKey] = data._visual[stepKey];
                }
            }
            if (_visualCache.connections.length === 0 && legacyConns.length > 0) {
                _visualCache.connections = legacyConns.slice();
            }
        }

        var startX = 80;
        var startY = 60;
        var xSpacing = 280;
        var ySpacing = 140;
        var nodesPerRow = 3;

        // create nodes — use in-memory cached positions if available, else auto-layout
        var nameToId = {};
        data.procedures.forEach(function (proc, idx) {
            var pos = _visualCache.positions[proc.name];
            var x = pos ? pos.x : startX + (idx % nodesPerRow) * xSpacing;
            var y = pos ? pos.y : startY + Math.floor(idx / nodesPerRow) * ySpacing;

            var info = ModuleRegistry.findByMod(proc.mod);
            var color = info ? info.module.color : '#6c757d';
            var icon = info ? info.module.icon : 'bi-gear';
            var moduleName = info ? info.moduleName : proc.mod.split('.').pop();

            var nodeId = addNode(proc.mod, moduleName, proc.method, color, icon, x, y, proc.name, proc.params || {});
            nameToId[proc.name] = nodeId;
        });

        // draw connections — prefer cached wires, then infer from @reference params
        var connectedPairs = {};

        // restore cached connections (drawn in visual editor this session)
        _visualCache.connections.forEach(function (conn) {
            var sourceId = nameToId[conn.from];
            var targetId = nameToId[conn.to];
            if (sourceId && targetId) {
                var pairKey = sourceId + '->' + targetId;
                if (!connectedPairs[pairKey]) {
                    try { editor.addConnection(sourceId, targetId, 'output_1', 'input_1'); } catch (e) {}
                    connectedPairs[pairKey] = true;
                }
            }
        });

        // also draw connections inferred from @reference params (handles loaded/saved workflows)
        data.procedures.forEach(function (proc) {
            var targetId = nameToId[proc.name];
            if (!targetId || !proc.params) return;

            for (var key in proc.params) {
                var val = proc.params[key];
                if (typeof val === 'string' && val.indexOf('@') === 0 && val.indexOf('@@') !== 0) {
                    var ref = val.substring(1);
                    var dotIdx = ref.indexOf('.');
                    var refStep = dotIdx >= 0 ? ref.substring(0, dotIdx) : ref;

                    var sourceId = nameToId[refStep];
                    if (sourceId) {
                        var pairKey = sourceId + '->' + targetId;
                        if (!connectedPairs[pairKey]) {
                            try { editor.addConnection(sourceId, targetId, 'output_1', 'input_1'); } catch (e) {}
                            connectedPairs[pairKey] = true;
                        }
                    }
                }
            }
        });

        recalculateOrder();
    }

    /**
     * Force Drawflow to recalculate all SVG connection paths.
     * Must be called AFTER the canvas pane is visible in the DOM,
     * otherwise getBoundingClientRect() returns zeros.
     */
    function refreshConnections() {
        if (!editor) return;
        if (!editor.updateConnectionNodes) return;
        var dfNodes = document.querySelectorAll('.drawflow-node');
        dfNodes.forEach(function (n) {
            try { editor.updateConnectionNodes(n.id); } catch (e) {}
        });
    }

    // =========================================================
    //  Zoom Controls
    // =========================================================

    function bindZoomButtons() {
        var btnIn = document.getElementById('btn-zoom-in');
        var btnOut = document.getElementById('btn-zoom-out');
        var btnReset = document.getElementById('btn-zoom-reset');

        if (btnIn) {
            btnIn.addEventListener('click', function (e) {
                e.preventDefault();
                if (editor) editor.zoom_in();
            });
        }
        if (btnOut) {
            btnOut.addEventListener('click', function (e) {
                e.preventDefault();
                if (editor) editor.zoom_out();
            });
        }
        if (btnReset) {
            btnReset.addEventListener('click', function (e) {
                e.preventDefault();
                if (editor) fitToView();
            });
        }
    }

    // =========================================================
    //  Fit to View — auto-zoom and center all nodes
    // =========================================================

    function fitToView() {
        if (!editor) return;

        var nodes = editor.drawflow.drawflow.Home.data;
        var keys = Object.keys(nodes);
        if (keys.length === 0) {
            editor.zoom_reset();
            return;
        }

        // find bounding box of all nodes
        var minX = Infinity, minY = Infinity;
        var maxX = -Infinity, maxY = -Infinity;

        keys.forEach(function (id) {
            var n = nodes[id];
            var el = document.querySelector('#node-' + id);
            var w = el ? el.offsetWidth : 180;
            var h = el ? el.offsetHeight : 80;
            if (n.pos_x < minX) minX = n.pos_x;
            if (n.pos_y < minY) minY = n.pos_y;
            if (n.pos_x + w > maxX) maxX = n.pos_x + w;
            if (n.pos_y + h > maxY) maxY = n.pos_y + h;
        });

        // add padding
        var pad = 40;
        minX -= pad;
        minY -= pad;
        maxX += pad;
        maxY += pad;

        var bw = maxX - minX;
        var bh = maxY - minY;

        // get canvas size
        var canvas = editor.precanvas.parentElement;
        var cw = canvas.clientWidth;
        var ch = canvas.clientHeight;

        // calculate zoom to fit
        var zoomX = cw / bw;
        var zoomY = ch / bh;
        var newZoom = Math.min(zoomX, zoomY, 1.0);  // never zoom in beyond 100%
        newZoom = Math.max(newZoom, editor.zoom_min || 0.1);

        // set zoom
        editor.zoom = newZoom;
        editor.zoom_refresh();

        // center: translate so bounding box center aligns with canvas center
        var centerX = (minX + maxX) / 2;
        var centerY = (minY + maxY) / 2;
        var tx = (cw / 2) / newZoom - centerX;
        var ty = (ch / 2) / newZoom - centerY;

        editor.precanvas.style.transform =
            'translate(' + (tx * newZoom) + 'px, ' + (ty * newZoom) + 'px) scale(' + newZoom + ')';

        // update editor internal state
        editor.canvas_x = tx * newZoom;
        editor.canvas_y = ty * newZoom;
    }

    // =========================================================
    //  Utilities
    // =========================================================

    function escHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function isInitialized() {
        return initialized;
    }

    // =========================================================
    //  Public API
    // =========================================================

    return {
        init: init,
        isInitialized: isInitialized,
        exportToJSON: exportToJSON,
        importFromJSON: importFromJSON,
        deleteNode: deleteNode,
        fitToView: fitToView,
        refreshConnections: refreshConnections,
        getSelectedNode: function () { return selectedNodeId; }
    };

})();
