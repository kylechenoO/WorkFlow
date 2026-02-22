/**
 * Module Registry — Auto-discovered catalog of all WorkFlow modules.
 *
 * Populated entirely from the ModuleInspector API at /modules/api/registry/.
 * No hardcoded module definitions — just add a .py file under mod/ and it
 * auto-appears in the Visual Editor palette.
 *
 * Depends on: /modules/api/registry/ endpoint
 */

/* global */

var ModuleRegistry = (function () {
    'use strict';

    // =========================================================
    //  Catalog — populated from API via loadFromAPI()
    // =========================================================

    var catalog = {};

    // =========================================================
    //  Public API
    // =========================================================

    /**
     * Get all categories for palette rendering.
     */
    function getCategories() {
        var result = [];
        for (var key in catalog) {
            result.push({
                id: key,
                label: catalog[key].label,
                icon: catalog[key].icon,
                modules: catalog[key].modules
            });
        }
        return result;
    }

    /**
     * Look up module info by mod path (e.g. "mod.common.Http").
     */
    function findByMod(modPath) {
        for (var catKey in catalog) {
            var cat = catalog[catKey];
            for (var modName in cat.modules) {
                if (cat.modules[modName].mod === modPath) {
                    return {
                        category: catKey,
                        categoryLabel: cat.label,
                        moduleName: modName,
                        module: cat.modules[modName]
                    };
                }
            }
        }
        return null;
    }

    /**
     * Get default param values for a specific module/method.
     */
    function getDefaultParams(modPath, methodName) {
        var info = findByMod(modPath);
        if (!info || !info.module.methods[methodName]) return {};

        var schema = info.module.methods[methodName].params;
        var defaults = {};
        for (var key in schema) {
            if (schema[key].default !== undefined && schema[key].default !== null) {
                defaults[key] = schema[key].default;
            }
        }
        return defaults;
    }

    /**
     * Load module registry from API and build the catalog.
     * This is the sole data source — no hardcoded fallback.
     */
    function loadFromAPI(callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/modules/api/registry/', true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) return;
            if (xhr.status === 200) {
                try {
                    var apiData = JSON.parse(xhr.responseText);
                    _buildCatalog(apiData);
                } catch (e) {
                    console.error('ModuleRegistry: failed to parse API response', e);
                }
            } else {
                console.error('ModuleRegistry: API returned status ' + xhr.status);
            }
            if (typeof callback === 'function') {
                callback();
            }
        };
        xhr.send();
    }

    /**
     * Build the catalog entirely from API data.
     */
    function _buildCatalog(apiData) {
        catalog = {};

        for (var catKey in apiData) {
            var apiCat = apiData[catKey];

            catalog[catKey] = {
                label: apiCat.label || catKey,
                icon: apiCat.icon || 'bi-puzzle',
                modules: {}
            };

            for (var modName in apiCat.modules) {
                var apiMod = apiCat.modules[modName];

                catalog[catKey].modules[modName] = {
                    mod: apiMod.mod || ('mod.' + catKey + '.' + modName),
                    icon: apiMod.icon || catalog[catKey].icon,
                    color: apiMod.color || apiCat.color || '#6c757d',
                    methods: {}
                };

                for (var methName in apiMod.methods) {
                    var apiMeth = apiMod.methods[methName];
                    catalog[catKey].modules[modName].methods[methName] = {
                        label: apiMeth.label || methName,
                        params: apiMeth.params || {},
                        returns: apiMeth.returns || null
                    };
                }
            }
        }
    }

    return {
        catalog: catalog,
        getCategories: getCategories,
        findByMod: findByMod,
        getDefaultParams: getDefaultParams,
        loadFromAPI: loadFromAPI
    };

})();
