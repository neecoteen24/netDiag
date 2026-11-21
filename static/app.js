const form = document.querySelector("#diagnosticForm");
const runButton = document.querySelector("#runButton");
const emptyState = document.querySelector("#emptyState");
const errorState = document.querySelector("#errorState");
const summaryGrid = document.querySelector("#summaryGrid");
const diagnosticsGrid = document.querySelector("#diagnosticsGrid");
const diagnosticsHeading = document.querySelector("#diagnosticsHeading");
const resultTitle = document.querySelector("#resultTitle");
const exportButton = document.querySelector("#exportButton");
const jsonPanel = document.querySelector("#jsonPanel");
const jsonToggle = document.querySelector("#jsonToggle");
const jsonOutput = document.querySelector("#jsonOutput");
let latestReport = null;

const labels = {
  network_info: ["Network", "NW"],
  dns_diagnostics: ["DNS resolution", "DN"],
  connectivity: ["Connectivity", "CN"],
  tcp_diagnostics: ["Port scan", "PT"],
  tls_diagnostics: ["TLS certificate", "TLS"],
  http_diagnostics: ["HTTP request", "HTTP"]
};

document.querySelector("#themeToggle").addEventListener("click", () => {
  document.body.classList.toggle("dark");
});

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function formatMetric(key, value) {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function keyLabel(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());
}

function renderCard(module) {
  const [title, symbol] = labels[module.module] || [module.module, "DX"];
  const excluded = new Set(["interfaces", "traceroute", "tcp_ports", "udp_probe", "records", "headers", "ping"]);
  let metrics = Object.entries(module.data || {}).filter(([key, value]) => !excluded.has(key) && typeof value !== "object");
  if (module.module === "tcp_diagnostics" && module.data?.tcp_ports) {
    metrics = module.data.tcp_ports.map(port => [port.port + " / " + port.protocol, port.state + (port.handshake_ms != null ? " · " + port.handshake_ms + " ms" : "")]);
  } else if (module.module === "dns_diagnostics" && module.data?.ipv4?.length) {
    metrics = [["IPv4", module.data.ipv4.join(", ")], ["IPv6", module.data.ipv6?.join(", ") || "None"]];
  } else if (module.module === "network_info") {
    metrics = [["Gateway", module.data.default_gateway?.gateway || "Unknown"], ["Interface", module.data.default_gateway?.interface || "Unknown"]];
  } else if (module.module === "connectivity" && module.data?.ping) {
    metrics = [["Packet loss", module.data.ping.packet_loss_percent + "%"], ["Latency", module.data.ping.avg_ms != null ? module.data.ping.avg_ms + " ms" : "Unavailable"]];
  } else if (module.module === "http_diagnostics") {
    metrics = [["Status", module.data.status_code || "No response"], ["Latency", module.data.latency_ms != null ? module.data.latency_ms + " ms" : "Unavailable"]];
  }

  return `<article class="diagnostic-card">
    <header class="diagnostic-card-header">
      <div class="diagnostic-card-title"><span class="module-symbol">${symbol}</span><h3>${escapeHtml(title)}</h3></div>
      <span class="status-badge status-${module.status}">${module.status}</span>
    </header>
    <div class="diagnostic-card-body">
      ${metrics.slice(0, 6).map(([key, value]) => `<div class="metric-row"><span>${escapeHtml(keyLabel(String(key)))}</span><b>${escapeHtml(formatMetric(key, value))}</b></div>`).join("")}
      ${module.error ? `<div class="card-error">${escapeHtml(module.error)}</div>` : ""}
    </div>
  </article>`;
}

function renderReport(report) {
  latestReport = report;
  emptyState.hidden = true;
  errorState.hidden = true;
  summaryGrid.hidden = false;
  diagnosticsGrid.hidden = false;
  diagnosticsHeading.hidden = false;
  exportButton.hidden = false;
  jsonPanel.hidden = false;
  jsonOutput.hidden = true;
  jsonOutput.textContent = JSON.stringify(report, null, 2);
  jsonToggle.setAttribute("aria-expanded", "false");
  jsonToggle.querySelector("span").textContent = "View raw JSON";
  jsonToggle.querySelector("b").textContent = "+";
  resultTitle.textContent = report.resolved_hostname || report.target;

  const counts = report.diagnostics.reduce((acc, module) => {
    acc[module.status] = (acc[module.status] || 0) + 1;
    return acc;
  }, {});
  const dns = report.diagnostics.find(module => module.module === "dns_diagnostics");
  const tcp = report.diagnostics.find(module => module.module === "tcp_diagnostics");
  const http = report.diagnostics.find(module => module.module === "http_diagnostics");
  const openPorts = tcp?.data?.tcp_ports?.filter(port => port.state === "OPEN").length || 0;

  summaryGrid.innerHTML = `
    <article class="summary-card"><span>Resolved host</span><strong>${escapeHtml(report.resolved_hostname)}</strong><small>DNS target</small></article>
    <article class="summary-card"><span>Checks passed</span><strong>${counts.PASS || 0}</strong><small>${counts.WARN || 0} warnings</small></article>
    <article class="summary-card"><span>Open ports</span><strong>${openPorts}</strong><small>${tcp?.data?.tcp_ports?.length || 0} tested</small></article>
    <article class="summary-card"><span>HTTP status</span><strong>${http?.data?.status_code || "—"}</strong><small>${http?.data?.latency_ms != null ? http.data.latency_ms + " ms" : "No response"}</small></article>`;
  diagnosticsGrid.innerHTML = report.diagnostics.map(renderCard).join("");
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  runButton.classList.add("loading");
  runButton.querySelector("span").textContent = "Scanning...";
  errorState.hidden = true;

  try {
    const response = await fetch("/api/diagnose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: document.querySelector("#target").value,
        ports: document.querySelector("#ports").value,
        scheme: document.querySelector("#scheme").value,
        udp_probe: document.querySelector("#udpProbe").checked,
        no_trace: document.querySelector("#noTrace").checked
      })
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error || "Diagnostic request failed.");
    renderReport(report);
  } catch (error) {
    emptyState.hidden = true;
    summaryGrid.hidden = true;
    diagnosticsGrid.hidden = true;
    diagnosticsHeading.hidden = true;
    jsonPanel.hidden = true;
    errorState.hidden = false;
    errorState.textContent = error.message;
  } finally {
    runButton.classList.remove("loading");
    runButton.querySelector("span").textContent = "Run diagnostics";
  }
});

exportButton.addEventListener("click", () => {
  if (!latestReport) return;
  const blob = new Blob([JSON.stringify(latestReport, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "netdiag-report.json";
  link.click();
  URL.revokeObjectURL(url);
});

jsonToggle.addEventListener("click", () => {
  const isOpen = jsonToggle.getAttribute("aria-expanded") === "true";
  jsonToggle.setAttribute("aria-expanded", String(!isOpen));
  jsonOutput.hidden = isOpen;
  jsonToggle.querySelector("span").textContent = isOpen ? "View raw JSON" : "Hide raw JSON";
  jsonToggle.querySelector("b").textContent = isOpen ? "+" : "−";
});
