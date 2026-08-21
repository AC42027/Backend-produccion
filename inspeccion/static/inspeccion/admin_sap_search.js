/*
 * Buscador de equipos SAP para el formulario de Equipo en el admin.
 * Consulta /api/sap/buscar/ (debounce) y al seleccionar un resultado
 * completa los campos sap_equnr / sap_equnr_desc / sap_tplnr / sap_tplnr_desc
 * usando /api/sap/resolver/ para los equipos (EQ).
 */
(function () {
    'use strict';

    function init() {
        var equnrInput = document.getElementById('id_sap_equnr');
        if (!equnrInput) return;

        // Evitar doble inicialización
        if (document.getElementById('sap-buscar-box')) return;

        var fieldRow = equnrInput.closest('.form-row, .field-sap_equnr, .flex-container') || equnrInput.parentElement;

        // Contenedor del buscador
        var box = document.createElement('div');
        box.id = 'sap-buscar-box';
        box.style.cssText = 'margin:4px 0 12px 0;';

        var searchWrap = document.createElement('div');
        searchWrap.style.cssText = 'display:flex;gap:6px;align-items:center;max-width:640px;';

        var searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.id = 'sap-buscar-input';
        searchInput.placeholder = 'Buscar en SAP (nombre o código, ej: CV170, GABINETE...)';
        searchInput.autocomplete = 'off';
        searchInput.style.cssText = 'flex:1;padding:6px 10px;border:1px solid #ccc;border-radius:4px;';

        var clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.textContent = 'Limpiar SAP';
        clearBtn.title = 'Vaciar los campos SAP';
        clearBtn.style.cssText = 'padding:6px 12px;border:1px solid #ccc;border-radius:4px;background:#f8f8f8;cursor:pointer;';
        clearBtn.addEventListener('click', function () {
            ['id_sap_equnr', 'id_sap_equnr_desc', 'id_sap_tplnr', 'id_sap_tplnr_desc'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.value = '';
            });
            results.innerHTML = '';
            status.textContent = '';
            searchInput.value = '';
            searchInput.focus();
        });

        searchWrap.appendChild(searchInput);
        searchWrap.appendChild(clearBtn);

        var results = document.createElement('div');
        results.id = 'sap-buscar-results';
        results.style.cssText = 'border:1px solid #ddd;border-radius:4px;max-width:640px;max-height:260px;overflow-y:auto;background:#fff;display:none;box-shadow:0 2px 6px rgba(0,0,0,.12);';

        var status = document.createElement('div');
        status.id = 'sap-buscar-status';
        status.style.cssText = 'max-width:640px;font-size:12px;margin-top:4px;color:#666;min-height:16px;';

        box.appendChild(searchWrap);
        box.appendChild(results);
        box.appendChild(status);

        // Insertar antes de la fila del campo EQUNR
        fieldRow.parentElement.insertBefore(box, fieldRow);

        var currentRequest = null;
        var debounceTimer = null;

        function setStatus(text, isError) {
            status.textContent = text || '';
            status.style.color = isError ? '#c0392b' : '#666';
        }

        function hideResults() {
            results.style.display = 'none';
            results.innerHTML = '';
        }

        function fillField(id, value) {
            var el = document.getElementById(id);
            if (el) {
                el.value = value || '';
                try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
            }
        }

        function selectResult(item) {
            hideResults();
            searchInput.value = item.descript + ' [' + item.id + ']';

            if (item.type === 'FL') {
                fillField('id_sap_tplnr', item.id);
                fillField('id_sap_tplnr_desc', item.descript);
                setStatus('Ubicación técnica asignada: ' + item.id, false);
                return;
            }

            setStatus('Resolviendo ubicación técnica de ' + item.id + '...', false);
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/sap/resolver/?equnr=' + encodeURIComponent(item.id), true);
            xhr.onload = function () {
                if (xhr.status !== 200) {
                    setStatus('Error resolviendo equipo (HTTP ' + xhr.status + '). Complete manualmente.', true);
                    return;
                }
                try {
                    var data = JSON.parse(xhr.responseText);
                    fillField('id_sap_equnr', data.equnr);
                    fillField('id_sap_equnr_desc', data.equnr_desc);
                    fillField('id_sap_tplnr', data.tplnr);
                    fillField('id_sap_tplnr_desc', data.tplnr_desc);
                    setStatus(
                        'Asignado: EQUNR ' + data.equnr +
                        (data.tplnr ? ' | TPLNR ' + data.tplnr + (data.tplnr_desc ? ' (' + data.tplnr_desc + ')' : '') : ''),
                        false
                    );
                } catch (e) {
                    setStatus('Respuesta inválida del servidor.', true);
                }
            };
            xhr.onerror = function () { setStatus('Error de red consultando el resolver.', true); };
            xhr.send();
        }

        function renderResults(items) {
            results.innerHTML = '';
            if (!items.length) {
                var empty = document.createElement('div');
                empty.textContent = 'Sin resultados.';
                empty.style.cssText = 'padding:8px 10px;color:#888;';
                results.appendChild(empty);
                results.style.display = 'block';
                return;
            }
            items.forEach(function (item) {
                var row = document.createElement('div');
                row.style.cssText = 'padding:8px 10px;cursor:pointer;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;gap:8px;';
                row.addEventListener('mouseover', function () { row.style.background = '#f2f7ff'; });
                row.addEventListener('mouseout', function () { row.style.background = ''; });

                var label = document.createElement('span');
                label.textContent = item.descript;
                label.style.fontWeight = '600';

                var code = document.createElement('span');
                code.textContent = item.id;
                code.style.cssText = 'font-family:monospace;color:#555;white-space:nowrap;';

                var badge = document.createElement('span');
                badge.textContent = item.type === 'FL' ? 'Ubicación' : 'Equipo';
                badge.style.cssText = 'font-size:11px;padding:1px 6px;border-radius:8px;' +
                    (item.type === 'FL'
                        ? 'background:#eef3ff;color:#3556a8;'
                        : 'background:#e8f6ec;color:#2c7a44;');

                var right = document.createElement('span');
                right.style.cssText = 'display:flex;align-items:center;gap:6px;';
                right.appendChild(code);
                right.appendChild(badge);

                row.appendChild(label);
                row.appendChild(right);
                row.addEventListener('click', function () { selectResult(item); });
                results.appendChild(row);
            });
            results.style.display = 'block';
        }

        function doSearch(q) {
            if (currentRequest) { try { currentRequest.abort(); } catch (e) {} }
            setStatus('Buscando...', false);
            currentRequest = new XMLHttpRequest();
            currentRequest.open('GET', '/api/sap/buscar/?q=' + encodeURIComponent(q), true);
            currentRequest.onload = function () {
                currentRequest = null;
                if (searchInput.value.trim() !== q) return; // respuesta obsoleta
                if (this.status !== 200) {
                    setStatus('Error del servidor (HTTP ' + this.status + ').', true);
                    hideResults();
                    return;
                }
                try {
                    var data = JSON.parse(this.responseText);
                    renderResults(data.resultados || []);
                    setStatus('');
                } catch (e) {
                    setStatus('Respuesta inválida.', true);
                }
            };
            currentRequest.onerror = function () {
                currentRequest = null;
                setStatus('No se pudo contactar la API de activos SAP.', true);
            };
            currentRequest.send();
        }

        searchInput.addEventListener('input', function () {
            var q = searchInput.value.trim();
            clearTimeout(debounceTimer);
            if (q.length < 2) {
                hideResults();
                setStatus('');
                return;
            }
            debounceTimer = setTimeout(function () { doSearch(q); }, 400);
        });

        // Cerrar dropdown al hacer clic fuera
        document.addEventListener('click', function (ev) {
            if (!box.contains(ev.target)) hideResults();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
