/**
 * Sortable Table — Client-side column sorting for HTML tables.
 *
 * Usage: Add class "sortable" to <table>, and data-sort="type" to each
 * sortable <th>. Supported types: "number", "string", "date".
 * The Actions column should NOT have data-sort to remain unsortable.
 *
 * Example:
 *   <table class="sortable">
 *     <thead><tr>
 *       <th data-sort="number">#</th>
 *       <th data-sort="string">Name</th>
 *       <th>Actions</th>  <!-- not sortable -->
 *     </tr></thead>
 *     ...
 *   </table>
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var tables = document.querySelectorAll('table.sortable');
        tables.forEach(function (table) {
            initSortable(table);
        });
    });

    function initSortable(table) {
        var headers = table.querySelectorAll('thead th[data-sort]');

        headers.forEach(function (th, colIdx) {
            // find real column index (account for th without data-sort)
            var allThs = table.querySelectorAll('thead th');
            var realIdx = Array.prototype.indexOf.call(allThs, th);

            th.style.cursor = 'pointer';
            th.style.userSelect = 'none';
            th.style.whiteSpace = 'nowrap';

            // add sort icon
            var icon = document.createElement('i');
            icon.className = 'bi bi-arrow-down-up';
            icon.style.fontSize = '10px';
            icon.style.marginLeft = '4px';
            icon.style.opacity = '0.4';
            th.appendChild(icon);

            th.addEventListener('click', function () {
                sortTable(table, th, realIdx);
            });
        });
    }

    function sortTable(table, clickedTh, colIdx) {
        var tbody = table.querySelector('tbody');
        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
        var sortType = clickedTh.getAttribute('data-sort');

        // determine sort direction
        var currentDir = clickedTh.getAttribute('data-sort-dir') || 'none';
        var newDir = (currentDir === 'asc') ? 'desc' : 'asc';

        // reset all headers
        var allHeaders = table.querySelectorAll('thead th[data-sort]');
        allHeaders.forEach(function (th) {
            th.setAttribute('data-sort-dir', 'none');
            var icon = th.querySelector('i.bi');
            if (icon) {
                icon.className = 'bi bi-arrow-down-up';
                icon.style.opacity = '0.4';
            }
        });

        // set active header
        clickedTh.setAttribute('data-sort-dir', newDir);
        var activeIcon = clickedTh.querySelector('i.bi');
        if (activeIcon) {
            activeIcon.className = newDir === 'asc' ? 'bi bi-sort-up' : 'bi bi-sort-down';
            activeIcon.style.opacity = '1';
        }

        // sort rows
        rows.sort(function (a, b) {
            var aCell = a.cells[colIdx];
            var bCell = b.cells[colIdx];
            if (!aCell || !bCell) return 0;

            var aVal = getCellValue(aCell, sortType);
            var bVal = getCellValue(bCell, sortType);

            var result = 0;
            if (sortType === 'number') {
                result = aVal - bVal;
            } else if (sortType === 'date') {
                result = aVal - bVal;
            } else {
                result = aVal.localeCompare(bVal);
            }

            return newDir === 'asc' ? result : -result;
        });

        // re-append rows in sorted order
        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    function getCellValue(cell, sortType) {
        var text = cell.textContent.trim();

        if (sortType === 'number') {
            // extract numeric value (strip ms, s, m, etc.)
            var num = parseFloat(text.replace(/[^0-9.\-]/g, ''));
            return isNaN(num) ? -1 : num;
        }

        if (sortType === 'date') {
            var d = new Date(text);
            return isNaN(d.getTime()) ? 0 : d.getTime();
        }

        // string: use lowercase for case-insensitive sorting
        return text.toLowerCase();
    }
})();
