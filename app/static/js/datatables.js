/**
 * datatables.js — Tienda Deportiva
 * Inicializa todas las tablas DataTables del sistema.
 */

"use strict";

// ── Configuración base de idioma español ────────────────────────
const DT_LANG_ES = {
  sProcessing:   "Procesando…",
  sLengthMenu:   "Mostrar _MENU_ registros",
  sZeroRecords:  "No se encontraron resultados",
  sEmptyTable:   "Ningún dato disponible en esta tabla",
  sInfo:         "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
  sInfoEmpty:    "Mostrando registros del 0 al 0 de un total de 0 registros",
  sInfoFiltered: "(filtrado de un total de _MAX_ registros)",
  sInfoPostFix:  "",
  sSearch:       "",
  sSearchPlaceholder: "Buscar…",
  sUrl:          "",
  sLoadingRecords: "Cargando…",
  oPaginate: {
    sFirst:    "Primero",
    sLast:     "Último",
    sNext:     "Siguiente",
    sPrevious: "Anterior"
  },
  oAria: {
    sSortAscending:  ": order ascending",
    sSortDescending: ": order descending"
  },
  buttons: {
    copyTitle:  "Copiado al portapapeles",
    copySuccess: { _: "%d filas copiadas", 1: "1 fila copiada" }
  }
};

// ── Helper: badge de alerta de stock ────────────────────────────
function badgeAlerta(alerta) {
  const map = {
    "REPOSICIÓN INMEDIATA": "badge-reposicion",
    "RIESGO BAJO":          "badge-riesgo",
    "STOCK SALUDABLE":      "badge-saludable",
  };
  return `<span class="${map[alerta] || 'badge-riesgo'}">${alerta}</span>`;
}

// ────────────────────────────────────────────────────────────────
// 1. TABLA OLAP — Dashboard Ejecutivo (#tabla-olap)
// ────────────────────────────────────────────────────────────────
function initTablaOlap() {
  const wrapper = document.getElementById("tabla-olap-wrapper");
  if (!wrapper) return;

  const filtros = new URLSearchParams({
    anio:     document.getElementById("filtro-anio")?.value     || "",
    ciudad:   document.getElementById("filtro-ciudad")?.value   || "",
    sucursal: document.getElementById("filtro-sucursal")?.value || "",
  });

  fetch(`/dashboard/api/tabla_olap?${filtros}`)
    .then(r => r.json())
    .then(({ columns, data }) => {
      // Construir tabla dinámicamente
      const thead = columns.map(c => `<th>${c}</th>`).join("");
      const tbody = data.map(row =>
        "<tr>" + row.map((cell, i) => {
          if (i === 6 || i === 7 || i === 8) {
            const v = typeof cell === "number"
              ? cell.toLocaleString("es-BO", { minimumFractionDigits: 2 })
              : cell;
            return `<td class="text-accent fw-bold">Bs ${v}</td>`;
          }
          return `<td>${cell || "—"}</td>`;
        }).join("") + "</tr>"
      ).join("");

      wrapper.innerHTML = `
        <table id="tabla-olap" class="display w-100" style="width:100%">
          <thead><tr>${thead}</tr></thead>
          <tbody>${tbody}</tbody>
        </table>
      `;

      if (jQuery && jQuery.fn.DataTable) {
        jQuery("#tabla-olap").DataTable({
          language:    DT_LANG_ES,
          pageLength:  15,
          lengthMenu:  [10, 15, 25, 50, 100],
          scrollX:     true,
          dom:         "Bfrtip",
          buttons: [
            { extend: "csv",   text: '<i class="fas fa-file-csv"></i> CSV',   className: "btn btn-sm btn-secondary" },
            { extend: "excel", text: '<i class="fas fa-file-excel"></i> Excel', className: "btn btn-sm btn-secondary" },
            { extend: "print", text: '<i class="fas fa-print"></i> Imprimir', className: "btn btn-sm btn-secondary" },
          ],
          order:       [[0, "desc"], [1, "desc"]],
        });
      }
    })
    .catch(err => {
      wrapper.innerHTML = `<p class="text-danger">Error cargando datos OLAP: ${err.message}</p>`;
    });
}

// ────────────────────────────────────────────────────────────────
// 2. TABLA HISTORIAL DE VENTAS (#tabla-historial)
// ────────────────────────────────────────────────────────────────
function initTablaHistorial() {
  const wrapper = document.getElementById("tabla-historial-wrapper");
  if (!wrapper) return;

  function cargarHistorial() {
    const params = new URLSearchParams({
      fecha_inicio: document.getElementById("filtro-fecha-inicio")?.value || "",
      fecha_fin:    document.getElementById("filtro-fecha-fin")?.value    || "",
    });

    // KPI del día
    fetch(`/ventas/api/del_dia`)
      .then(r => r.json())
      .then(d => {
        const el = document.getElementById("kpi-total-dia");
        if (el) el.textContent = `Bs ${(d.total || 0).toLocaleString("es-BO", {minimumFractionDigits:2})}`;
      })
      .catch(() => {});

    fetch(`/ventas/api/historial?${params}`)
      .then(r => r.json())
      .then(({ data }) => {
        if (jQuery && jQuery.fn.DataTable) {
          // Destruir si ya existe
          if (jQuery.fn.DataTable.isDataTable("#tabla-historial")) {
            jQuery("#tabla-historial").DataTable().destroy();
            jQuery("#tabla-historial tbody").empty();
          }

          const tbody = document.querySelector("#tabla-historial tbody");
          if (tbody) {
            tbody.innerHTML = data.map(r => `
              <tr>
                <td>#${r.id_venta}</td>
                <td>${r.fecha}</td>
                <td>${r.cliente}</td>
                <td class="text-accent fw-bold">Bs ${r.monto.toLocaleString("es-BO",{minimumFractionDigits:2})}</td>
                <td class="text-warning">Bs ${r.descuento.toLocaleString("es-BO",{minimumFractionDigits:2})}</td>
                <td>Bs ${r.impuesto.toLocaleString("es-BO",{minimumFractionDigits:2})}</td>
              </tr>
            `).join("");
          }

          jQuery("#tabla-historial").DataTable({
            language:   DT_LANG_ES,
            pageLength: 25,
            lengthMenu: [10, 25, 50, 100],
            dom:        "Bfrtip",
            buttons: [
              { extend: "csv",   text: '<i class="fas fa-file-csv"></i> CSV', className: "btn btn-sm btn-secondary" },
              { extend: "excel", text: '<i class="fas fa-file-excel"></i> Excel', className: "btn btn-sm btn-secondary" },
            ],
            order: [[0, "desc"]],
          });
        }
      })
      .catch(err => console.error("Error historial:", err));
  }

  cargarHistorial();

  const btnFiltrar = document.getElementById("btn-filtrar-historial");
  if (btnFiltrar) {
    btnFiltrar.addEventListener("click", cargarHistorial);
  }
}

// ────────────────────────────────────────────────────────────────
// 3. TABLA DE PRODUCTOS/INVENTARIO (#tabla-productos)
// ────────────────────────────────────────────────────────────────
function initTablaProductos() {
  const wrapper = document.getElementById("tabla-productos-wrapper");
  if (!wrapper) return;

  function cargarProductos() {
    const params = new URLSearchParams({
      marca: document.getElementById("filtro-marca")?.value || "",
    });

    fetch(`/inventario/api/productos?${params}`)
      .then(r => r.json())
      .then(({ data }) => {
        if (jQuery && jQuery.fn.DataTable) {
          if (jQuery.fn.DataTable.isDataTable("#tabla-productos")) {
            jQuery("#tabla-productos").DataTable().destroy();
            jQuery("#tabla-productos tbody").empty();
          }

          const tbody = document.querySelector("#tabla-productos tbody");
          if (tbody) {
            tbody.innerHTML = data.map(p => `
              <tr>
                <td>#${p.id}</td>
                <td><strong>${p.nombre}</strong></td>
                <td>${p.marca}</td>
                <td class="text-accent fw-bold">Bs ${p.precio.toLocaleString("es-BO",{minimumFractionDigits:2})}</td>
                <td>${p.talla || "—"}</td>
                <td>${p.temporada || "—"}</td>
                <td>
                  <div class="d-flex align-center gap-8">
                    <span>${p.stock}</span>
                    <div class="progress-bar" style="width:80px">
                      <div class="progress-fill ${p.alerta === 'STOCK SALUDABLE' ? 'saludable' : p.alerta === 'RIESGO BAJO' ? 'riesgo' : 'critico'}"
                           style="width:${Math.min(100, Math.round((p.stock / (p.max || 1)) * 100))}%"></div>
                    </div>
                  </div>
                </td>
                <td>${badgeAlerta(p.alerta)}</td>
              </tr>
            `).join("");
          }

          jQuery("#tabla-productos").DataTable({
            language:   DT_LANG_ES,
            pageLength: 20,
            lengthMenu: [10, 20, 50, 100],
            dom:        "Bfrtip",
            buttons: [
              { extend: "csv",   text: '<i class="fas fa-file-csv"></i> CSV', className: "btn btn-sm btn-secondary" },
              { extend: "excel", text: '<i class="fas fa-file-excel"></i> Excel', className: "btn btn-sm btn-secondary" },
            ],
            order: [[6, "asc"]],
          });
        }
      })
      .catch(err => console.error("Error productos:", err));
  }

  cargarProductos();

  const btnFiltrar = document.getElementById("btn-filtrar-productos");
  if (btnFiltrar) {
    btnFiltrar.addEventListener("click", cargarProductos);
  }
}

// ────────────────────────────────────────────────────────────────
// 4. TABLA DE ALERTAS STOCK (cards) — usa /inventario/api/stock_bajo
// ────────────────────────────────────────────────────────────────
function initTablaAlertas() {
  const container = document.getElementById("alertas-container");
  if (!container) return;

  fetch("/inventario/api/stock_bajo")
    .then(r => r.json())
    .then(({ data, total }) => {
      const kpiEl = document.getElementById("kpi-alertas-total");
      if (kpiEl) kpiEl.textContent = total || 0;

      if (!data || data.length === 0) {
        container.innerHTML = `
          <div class="card text-center" style="padding:48px">
            <p style="font-size:3rem">✅</p>
            <p class="text-secondary mt-16">No hay productos con stock bajo en este momento.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = data.map(p => {
        const pct = Math.min(100, Math.round((p.stock / (p.minimo * 2 || 1)) * 100));
        return `
          <div class="card" style="min-width:260px">
            <div class="card-header" style="margin-bottom:12px;padding-bottom:12px">
              <div>
                <div class="fw-bold">${p.nombre}</div>
                <div class="text-muted fs-sm">${p.marca}</div>
              </div>
              <span class="badge-reposicion">ALERTA</span>
            </div>
            <div class="d-flex justify-between mb-8">
              <span class="text-muted fs-sm">Stock actual</span>
              <span class="text-danger fw-bold">${p.stock} uds</span>
            </div>
            <div class="d-flex justify-between mb-8">
              <span class="text-muted fs-sm">Stock mínimo</span>
              <span class="text-secondary">${p.minimo} uds</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill critico" style="width:${pct}%"></div>
            </div>
            <button class="btn btn-secondary btn-sm w-100 mt-16" style="margin-top:16px">
              <i class="fas fa-envelope"></i> Contactar Proveedor
            </button>
          </div>
        `;
      }).join("");
    })
    .catch(err => {
      console.error("Error alertas:", err);
      if (container) container.innerHTML = `<p class="text-danger">Error cargando alertas.</p>`;
    });
}

// ────────────────────────────────────────────────────────────────
// INICIALIZACIÓN
// ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTablaOlap();
  initTablaHistorial();
  initTablaProductos();
  initTablaAlertas();
});
