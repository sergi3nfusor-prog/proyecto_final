/**
 * dashboard.js — Tienda Deportiva
 * Gestiona todos los Chart.js del panel analítico.
 */

"use strict";

// ── Paleta de colores corporativos ───────────────────────────────
const PALETTE = [
  "#c0392b", "#e74c3c", "#922b21", "#f1948a",
  "#7b241c", "#d98880", "#5b202d", "#ff6b6b"
];

const CHART_DEFAULTS = {
  color:       "#888",
  borderColor: "rgba(255,255,255,0.08)",
  plugins: {
    legend:  { labels: { color: "#e8e8e8", font: { family: "Inter", size: 12 } } },
    tooltip: {
      backgroundColor: "#12121a",
      titleColor:      "#e8e8e8",
      bodyColor:       "#888",
      borderColor:     "rgba(255,255,255,0.08)",
      borderWidth:     1,
    }
  }
};

// ── Instancias de Chart (para destruir/recrear) ──────────────────
const charts = {};

// ── Helper: recoger filtros activos ─────────────────────────────
function getFilterParams() {
  const anio     = document.getElementById("filtro-anio")?.value     || "";
  const ciudad   = document.getElementById("filtro-ciudad")?.value   || "";
  const sucursal = document.getElementById("filtro-sucursal")?.value || "";
  return new URLSearchParams({ anio, ciudad, sucursal });
}

// ── Helper: fetch con manejo de errores ─────────────────────────
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Helper: destruir chart si existe ────────────────────────────
function destroyChart(id) {
  if (charts[id]) {
    charts[id].destroy();
    delete charts[id];
  }
}

// ────────────────────────────────────────────────────────────────
// 1. POBLAR SELECTORES DE FILTROS
// ────────────────────────────────────────────────────────────────
async function cargarFiltros() {
  try {
    const data = await fetchJSON("/dashboard/api/filtros");

    const selAnio     = document.getElementById("filtro-anio");
    const selCiudad   = document.getElementById("filtro-ciudad");
    const selSucursal = document.getElementById("filtro-sucursal");

    if (selAnio) {
      selAnio.innerHTML = '<option value="">Todos los años</option>';
      data.anios.forEach(a => {
        selAnio.innerHTML += `<option value="${a}">${a}</option>`;
      });
    }

    if (selCiudad) {
      selCiudad.innerHTML = '<option value="">Todas las ciudades</option>';
      data.ciudades.forEach(c => {
        selCiudad.innerHTML += `<option value="${c}">${c}</option>`;
      });
    }

    if (selSucursal) {
      selSucursal.innerHTML = '<option value="">Todas las sucursales</option>';
      data.sucursales.forEach(s => {
        selSucursal.innerHTML += `<option value="${s.nombre}">${s.nombre} (${s.ciudad})</option>`;
      });
    }
  } catch (e) {
    console.warn("Error cargando filtros:", e);
  }
}

// ────────────────────────────────────────────────────────────────
// 2. VENTAS POR MES — Chart tipo Line
// ────────────────────────────────────────────────────────────────
async function cargarVentasMes(params = "") {
  const canvas = document.getElementById("chart-ventas-mes");
  if (!canvas) return;

  try {
    const data = await fetchJSON(`/dashboard/api/ventas_mes?${params}`);
    destroyChart("ventas-mes");

    charts["ventas-mes"] = new Chart(canvas, {
      type: "line",
      data: {
        labels:   data.labels,
        datasets: [{
          label:           "Ventas (Bs)",
          data:            data.data,
          borderColor:     PALETTE[0],
          backgroundColor: "rgba(192,57,43,0.12)",
          borderWidth:     2.5,
          pointBackgroundColor: PALETTE[0],
          pointRadius:     5,
          pointHoverRadius: 8,
          fill:            true,
          tension:         0.4,
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        responsive:          true,
        maintainAspectRatio: false,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false },
        },
        scales: {
          x: {
            ticks:  { color: "#888", font: { family: "Inter", size: 11 } },
            grid:   { color: "rgba(255,255,255,0.04)" },
          },
          y: {
            ticks:  { color: "#888", font: { family: "Inter", size: 11 },
                      callback: v => "Bs " + v.toLocaleString() },
            grid:   { color: "rgba(255,255,255,0.04)" },
          }
        }
      }
    });

    // Actualizar KPIs si existen en la página
    _setKpi("kpi-total-mes",        `Bs ${(data.total_mes || 0).toLocaleString("es-BO", {minimumFractionDigits:2})}`);
    _setKpi("kpi-transacciones",    data.transacciones || 0);
    _setKpi("kpi-ticket-promedio",  `Bs ${(data.ticket_promedio || 0).toLocaleString("es-BO", {minimumFractionDigits:2})}`);
    _setKpi("kpi-total-descuentos", `Bs ${(data.total_descuentos || 0).toLocaleString("es-BO", {minimumFractionDigits:2})}`);

  } catch (e) {
    console.error("Error cargarVentasMes:", e);
  }
}

function _setKpi(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ────────────────────────────────────────────────────────────────
// 3. SEGMENTACIÓN DE CLIENTES — Chart tipo Doughnut
// ────────────────────────────────────────────────────────────────
async function cargarClientesSegmento(params = "") {
  const canvas = document.getElementById("chart-clientes-segmento");
  if (!canvas) return;

  try {
    const data = await fetchJSON(`/dashboard/api/clientes_segmento?${params}`);
    destroyChart("clientes-segmento");

    charts["clientes-segmento"] = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels:   data.segmentos.labels,
        datasets: [{
          data:             data.segmentos.data,
          backgroundColor: PALETTE.slice(0, data.segmentos.labels.length),
          borderColor:     "rgba(255,255,255,0.06)",
          borderWidth:     2,
          hoverOffset:     8,
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        responsive:          true,
        maintainAspectRatio: false,
        cutout:              "68%",
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: {
            position: "bottom",
            labels:   { color: "#888", font: { family: "Inter", size: 11 }, padding: 16 }
          }
        }
      }
    });

    // Poblar tabla top10
    const tbody = document.getElementById("tabla-top-clientes-body");
    if (tbody && data.top10) {
      tbody.innerHTML = data.top10.map(c => `
        <tr>
          <td>${c.nombre}</td>
          <td><span class="badge-${c.segmento === 'Platino' ? 'saludable' : c.segmento === 'Oro' ? 'riesgo' : 'reposicion'}">${c.segmento}</span></td>
          <td>${c.nivel}</td>
          <td>${c.total_compras}</td>
          <td class="text-accent fw-bold">Bs ${c.valor_total.toLocaleString("es-BO", {minimumFractionDigits:2})}</td>
        </tr>
      `).join("");
    }

    _setKpi("kpi-total-clientes", data.total_clientes || 0);

  } catch (e) {
    console.error("Error cargarClientesSegmento:", e);
  }
}

// ────────────────────────────────────────────────────────────────
// 4. RECAUDACIÓN POR SUCURSAL — Chart tipo Bar horizontal
// ────────────────────────────────────────────────────────────────
async function cargarSucursales(params = "") {
  const canvas = document.getElementById("chart-sucursales");
  if (!canvas) return;

  try {
    const data = await fetchJSON(`/dashboard/api/sucursales?${params}`);
    destroyChart("sucursales");

    charts["sucursales"] = new Chart(canvas, {
      type: "bar",
      data: {
        labels:   data.labels,
        datasets: [
          {
            label:           "Recaudación (Bs)",
            data:            data.recaudacion,
            backgroundColor: PALETTE[0],
            borderColor:     PALETTE[1],
            borderWidth:     1,
            borderRadius:    6,
          },
          {
            label:           "Productividad/Empleado (Bs)",
            data:            data.productividad,
            backgroundColor: PALETTE[2],
            borderColor:     PALETTE[3],
            borderWidth:     1,
            borderRadius:    6,
          }
        ]
      },
      options: {
        ...CHART_DEFAULTS,
        responsive:          true,
        maintainAspectRatio: false,
        indexAxis:           "y",
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: {
            position: "top",
            labels:   { color: "#888", font: { family: "Inter", size: 11 } }
          }
        },
        scales: {
          x: {
            ticks: { color: "#888", callback: v => "Bs " + v.toLocaleString() },
            grid:  { color: "rgba(255,255,255,0.04)" },
          },
          y: {
            ticks: { color: "#e8e8e8", font: { family: "Inter", size: 11 } },
            grid:  { display: false },
          }
        }
      }
    });

  } catch (e) {
    console.error("Error cargarSucursales:", e);
  }
}

// ────────────────────────────────────────────────────────────────
// 5. SALUD DEL STOCK — Chart tipo Pie
// ────────────────────────────────────────────────────────────────
async function cargarStockSalud(params = "") {
  const canvas = document.getElementById("chart-stock-salud");
  if (!canvas) return;

  try {
    const data = await fetchJSON(`/dashboard/api/stock_salud?${params}`);
    destroyChart("stock-salud");

    const colores = {
      "REPOSICIÓN INMEDIATA": "#c0392b",
      "RIESGO BAJO":          "#f39c12",
      "STOCK SALUDABLE":      "#27ae60",
    };

    charts["stock-salud"] = new Chart(canvas, {
      type: "pie",
      data: {
        labels:   data.labels,
        datasets: [{
          data:             data.data,
          backgroundColor: data.labels.map(l => colores[l] || PALETTE[0]),
          borderColor:     "rgba(255,255,255,0.06)",
          borderWidth:     2,
          hoverOffset:     8,
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        responsive:          true,
        maintainAspectRatio: false,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: {
            position: "bottom",
            labels:   { color: "#888", font: { family: "Inter", size: 11 }, padding: 14 }
          }
        }
      }
    });

  } catch (e) {
    console.error("Error cargarStockSalud:", e);
  }
}

// ────────────────────────────────────────────────────────────────
// 6. CHART TOP PRODUCTOS — Bar vertical
// ────────────────────────────────────────────────────────────────
async function cargarTopProductos(params = "") {
  const canvas = document.getElementById("chart-top-productos");
  if (!canvas) return;

  try {
    const data = await fetchJSON(`/dashboard/api/productos_dashboard?${params}`);
    destroyChart("top-productos");

    const top = data.top_productos || [];

    charts["top-productos"] = new Chart(canvas, {
      type: "bar",
      data: {
        labels:   top.map(p => `${p.nombre} (${p.marca})`),
        datasets: [{
          label:           "Unidades Vendidas",
          data:            top.map(p => p.unidades),
          backgroundColor: PALETTE.slice(0, top.length),
          borderRadius:    6,
          borderWidth:     0,
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        responsive:          true,
        maintainAspectRatio: false,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: { color: "#888", maxRotation: 30, font: { size: 10 } },
            grid:  { display: false },
          },
          y: {
            ticks: { color: "#888" },
            grid:  { color: "rgba(255,255,255,0.04)" },
          }
        }
      }
    });

    _setKpi("kpi-valor-inventario",
      `Bs ${(data.valor_total_inventario || 0).toLocaleString("es-BO", {minimumFractionDigits:2})}`);
    _setKpi("kpi-productos-alerta", data.productos_en_alerta || 0);

  } catch (e) {
    console.error("Error cargarTopProductos:", e);
  }
}

// ────────────────────────────────────────────────────────────────
// 7. BOTÓN "APLICAR FILTROS"
// ────────────────────────────────────────────────────────────────
function inicializarFiltros() {
  const btn = document.getElementById("btn-aplicar-filtros");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const params = getFilterParams().toString();
    btn.innerHTML = '<span class="spinner"></span> Cargando…';
    btn.disabled = true;

    Promise.all([
      cargarVentasMes(params),
      cargarClientesSegmento(params),
      cargarSucursales(params),
      cargarStockSalud(params),
      cargarTopProductos(params),
    ]).finally(() => {
      btn.innerHTML = '<i class="fas fa-filter"></i> Aplicar Filtros';
      btn.disabled = false;
    });
  });
}

// ────────────────────────────────────────────────────────────────
// 8. INICIALIZACIÓN AUTOMÁTICA
// ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await cargarFiltros();

  // Cargar todos los charts presentes en la página actual
  const params = getFilterParams().toString();
  cargarVentasMes(params);
  cargarClientesSegmento(params);
  cargarSucursales(params);
  cargarStockSalud(params);
  cargarTopProductos(params);

  inicializarFiltros();
});
