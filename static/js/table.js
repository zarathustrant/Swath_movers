// Global variables
let tableData = null;
let deploymentColors = {};
let canEdit = false;
let currentSwath = '';
let deploymentTypes = [];
let lineNumbers = [];
let dragging = false;
let startSelect = null;
let zoomLevel = 100;

$(document).ready(function() {
    console.log('JavaScript loaded and ready');
    loadTableData();
});

function loadTableData() {
    console.log('loadTableData() called');
    // Show loading
    $('#loading').show();
    updateProgress(0, 'Initializing...');

    // Get current swath from URL
    const pathParts = window.location.pathname.split('/');
    const swath = pathParts[pathParts.length - 1];
    console.log('Swath from URL:', swath);

    // Use XMLHttpRequest for progress tracking
    const xhr = new XMLHttpRequest();

    xhr.addEventListener('progress', function(e) {
        console.log('Progress event:', e);
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            console.log('Progress:', percentComplete + '%');
            updateProgress(percentComplete, `Loading data... ${percentComplete}%`);
        } else {
            // Fallback: simulate progress
            simulateProgress();
        }
    });

    xhr.addEventListener('loadstart', function() {
        console.log('Load started');
        updateProgress(5, 'Starting download...');
    });

    xhr.addEventListener('load', function() {
        updateProgress(90, 'Processing data...');

        if (xhr.status === 200) {
            try {
                const data = JSON.parse(xhr.responseText);
                console.log('JSON data received:', data);

                if (data.error) {
                    console.error('Error in data:', data.error);
                    showToast('❌ ' + data.error);
                    $('#loading').hide();
                    return;
                }

                // Store global data
                tableData = data.table_data;
                deploymentColors = data.colors;
                canEdit = data.can_edit;
                currentSwath = data.swath;
                deploymentTypes = data.deployment_types;
                lineNumbers = data.line_numbers;

                console.log('Global data stored:', {
                    tableDataLength: tableData.length,
                    deploymentColors,
                    canEdit,
                    currentSwath,
                    deploymentTypesLength: deploymentTypes.length,
                    lineNumbersLength: lineNumbers.length
                });

                updateProgress(95, 'Building table...');

                // Update UI
                updateUI(data);
                buildTable();
                buildStats(data);

                updateProgress(100, 'Complete!');
                setTimeout(() => {
                    $('#loading').hide();
                    console.log('Table built successfully');
                }, 500);

            } catch (e) {
                console.error('Error parsing JSON:', e);
                showToast('❌ Error processing data');
                $('#loading').hide();
            }
        } else {
            console.error('HTTP error:', xhr.status);
            showToast('❌ Failed to load data');
            $('#loading').hide();
        }
    });

    xhr.addEventListener('error', function() {
        console.error('Network error');
        showToast('❌ Network error');
        $('#loading').hide();
    });

    xhr.open('GET', `/api/swath/${swath}`);
    xhr.send();
}

function simulateProgress() {
    let progress = 10;
    const progressInterval = setInterval(() => {
        if (progress < 85) {
            progress += Math.random() * 15;
            updateProgress(Math.min(progress, 85), `Loading data... ${Math.round(progress)}%`);
        } else {
            clearInterval(progressInterval);
        }
    }, 200);
}

function updateProgress(percent, text) {
    $('#progressBar').css('width', percent + '%');
    $('#progressText').text(text);
}

function updateUI(data) {
    // Update swath selector
    const swathSelect = $('#swathSelect');
    swathSelect.empty();
    data.swath_list.forEach(function(s) {
        const selected = s === data.swath ? 'selected' : '';
        swathSelect.append(`<option value="${s}" ${selected}>${s}</option>`);
    });

    // Update login/logout buttons
    if (canEdit) {
        $('#loginBtn').hide();
        $('#logoutBtn').show();
    } else {
        $('#loginBtn').show();
        $('#logoutBtn').hide();
    }
}

function buildTable() {
    const headerRow = $('#tableHeader');
    const body = $('#tableBody');

    // Clear existing content
    headerRow.empty();
    body.empty();

    // Build header
    lineNumbers.forEach(function(line) {
        headerRow.append(`<th>${line}</th><th>Deployment/Retrieval</th>`);
    });

    // Build table rows
    tableData.forEach(function(entry) {
        const row = $('<tr></tr>');

        lineNumbers.forEach(function(line) {
            const cellData = entry.row[line];

            if (cellData && cellData.value) {
                // Data cell
                const cell = $(`<td id="cell-${line}-${entry.shot}" class="shot-cell">${cellData.value}</td>`);
                row.append(cell);

                // Select cell
                const selectCell = $('<td></td>');
                const selectWrapper = $('<div class="select-wrapper"></div>');
                const select = $(`
                    <select data-line="${line}" data-shot="${entry.shot}">
                        <option value="">--</option>
                    </select>
                `);

                // Add options
                deploymentTypes.forEach(function(type) {
                    const selected = cellData.deploy === type ? 'selected' : '';
                    select.append(`<option value="${type}" ${selected}>${type}</option>`);
                });

                // Set initial color
                const color = cellData.color || '#ffffff';
                cell.css('background-color', color);

                // Add fill handle
                const fillHandle = $('<div class="fill-handle"></div>');

                selectWrapper.append(select);
                selectWrapper.append(fillHandle);
                selectCell.append(selectWrapper);
                row.append(selectCell);
            } else {
                // Empty cells
                row.append('<td></td><td></td>');
            }
        });

        body.append(row);
    });

    // Reinitialize event handlers
    initializeEventHandlers();
}

function initializeEventHandlers() {
    $(document).off('change', 'select[data-line]');
    $(document).off('mousedown', '.fill-handle');

    $(document).on('change', 'select[data-line]', function() {
        const line = $(this).data('line');
        const shot = $(this).data('shot');
        updateDeployment($(this), line, shot);
    });

    $(document).on('mousedown', '.fill-handle', function(e) {
        e.preventDefault();
        startFill($(this)[0]);
    });

    $('#zoomIn').off('click').on('click', zoomIn);
    $('#zoomOut').off('click').on('click', zoomOut);
    $('#toggleStats').off('click').on('click', toggleStats);
    $('#clearCache').off('click').on('click', clearLineCache);
    $('#swathSelect').off('change').on('change', function() {
        window.location.href = '/swath/' + $(this).val();
    });

    makeStatsDraggable();
}

function updateDeployment(select, line, shot) {
    const value = select.val();
    const color = deploymentColors[value] || '#ffffff';

    $(`#cell-${line}-${shot}`).css('background-color', color);

    if (!canEdit) {
        showToast("🔒 Not saved — viewer mode only.");
        return;
    }

    $.ajax({
        url: `/save/${currentSwath}`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            line: line,
            shotpoint: shot,
            deployment: value
        }),
        success: function(response) {
            if (response.status === 'saved') {
                showToast(`✅ Saved by ${response.user}`);
            }
        }
    });
}

function startFill(handle) {
    dragging = true;
    startSelect = $(handle).siblings('select')[0];
    $('body').addClass('dragging');

    $(document).on('mouseup', stopFill);
    $(document).on('mousemove', performFill);
}

function stopFill() {
    dragging = false;
    startSelect = null;
    $('body').removeClass('dragging');

    $(document).off('mouseup', stopFill);
    $(document).off('mousemove', performFill);
}

function performFill(e) {
    if (!dragging || !startSelect) return;

    const allSelects = $(`select[data-line="${$(startSelect).data('line')}"]`);
    const startIndex = allSelects.index(startSelect);

    allSelects.slice(startIndex + 1).each(function() {
        const select = $(this);
        const rect = select[0].getBoundingClientRect();

        if (e.clientY >= rect.top && e.clientY <= rect.bottom) {
            const line = select.data('line');
            const shot = select.data('shot');

            select.val($(startSelect).val());
            updateDeployment(select, line, shot);
        }
    });
}

function applyZoom() {
    $('body').css('zoom', zoomLevel + '%');
    $('#zoomDisplay').text(zoomLevel + '%');
}

function zoomIn() {
    if (zoomLevel < 200) {
        zoomLevel += 10;
        applyZoom();
    }
}

function zoomOut() {
    if (zoomLevel > 50) {
        zoomLevel -= 10;
        applyZoom();
    }
}

function toggleStats() {
    $('#statsPopup').toggle();
}

function makeStatsDraggable() {
    const popup = $('#statsPopup');
    const header = $('#statsHeader');
    let isDragging = false;
    let offset = { x: 0, y: 0 };

    header.off('mousedown').on('mousedown', function(e) {
        isDragging = true;
        offset.x = e.clientX - popup.offset().left;
        offset.y = e.clientY - popup.offset().top;
        popup.css('cursor', 'grabbing');
    });

    $(document).off('mousemove').on('mousemove', function(e) {
        if (!isDragging) return;

        popup.css({
            top: (e.clientY - offset.y) + 'px',
            left: (e.clientX - offset.x) + 'px',
            right: 'auto'
        });
    });

    $(document).off('mouseup').on('mouseup', function() {
        isDragging = false;
        popup.css('cursor', '');
    });
}

function clearLineCache() {
    if (confirm('Clear line cache and regenerate all map lines from scratch?')) {
        $.ajax({
            url: '/clear_line_cache',
            method: 'POST',
            contentType: 'application/json',
            success: function(response) {
                showToast('✅ ' + response.message);
            },
            error: function() {
                showToast('❌ Error clearing cache');
            }
        });
    }
}

function showToast(message) {
    const toast = $('#toast');
    toast.text(message).fadeIn(300);
    setTimeout(() => toast.fadeOut(300), 3000);
}

function buildStats(data) {
    const statsContent = $('#statsContent');
    statsContent.empty();

    const statsTable = $('<table></table>');
    const thead = $('<thead></thead>');
    const tbody = $('<tbody></tbody>');
    const tfoot = $('<tfoot></tfoot>');

    // Header
    const headerRow = $('<tr></tr>');
    headerRow.append('<th>Deployment/Retrieval Type</th>');
    lineNumbers.forEach(function(line) {
        headerRow.append(`<th>${line}</th>`);
    });
    headerRow.append('<th style="background:#333;">Total</th>');
    thead.append(headerRow);

    // Body
    deploymentTypes.forEach(function(dtype) {
        const row = $('<tr></tr>');
        row.append(`<td><strong>${dtype}</strong></td>`);

        let rowTotal = 0;
        lineNumbers.forEach(function(line) {
            const count = data.stats[dtype][line];
            rowTotal += count;

            const maxCount = data.max_count[dtype];
            const intensity = maxCount > 0 ? 255 - (count / maxCount * 180) : 255;

            const base = deploymentColors[dtype] || "#ffffff";
            const r = parseInt(base.slice(1, 3), 16);
            const g = parseInt(base.slice(3, 5), 16);
            const b = parseInt(base.slice(5, 7), 16);

            const rr = Math.floor(r * (intensity / 255));
            const gg = Math.floor(g * (intensity / 255));
            const bb = Math.floor(b * (intensity / 255));
            const brightness = (rr * 0.299 + gg * 0.587 + bb * 0.114);
            const textColor = brightness < 128 ? 'white' : 'black';

            row.append(`<td style="background-color: rgb(${rr}, ${gg}, ${bb}); color: ${textColor};">${count}</td>`);
        });

        row.append(`<td style="background:#eee; font-weight:bold;">${rowTotal}</td>`);
        tbody.append(row);
    });

    // Footer
    const footerRow = $('<tr></tr>');
    footerRow.append('<th>Total</th>');

    let grandTotal = 0;
    lineNumbers.forEach(function(line) {
        let colTotal = 0;
        deploymentTypes.forEach(function(dt) {
            if (data.stats[dt][line] !== undefined) {
                colTotal += data.stats[dt][line];
            }
        });
        grandTotal += colTotal;
        footerRow.append(`<th style="background:#eee; color:black; font-weight:bold;">${colTotal}</th>`);
    });

    footerRow.append(`<th style="background:#333; color:white; font-weight:bold;">${grandTotal}</th>`);
    tfoot.append(footerRow);

    statsTable.append(thead);
    statsTable.append(tbody);
    statsTable.append(tfoot);
    statsContent.append(statsTable);
}
