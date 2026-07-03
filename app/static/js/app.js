document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll("table.sortable").forEach((table) => {
  table.querySelectorAll("th").forEach((header, index) => {
    header.addEventListener("click", () => {
      const body = table.tBodies[0];
      const rows = Array.from(body.rows);
      const asc = header.dataset.order !== "asc";
      rows.sort((a, b) => a.cells[index].innerText.localeCompare(b.cells[index].innerText, undefined, { numeric: true }) * (asc ? 1 : -1));
      rows.forEach((row) => body.appendChild(row));
      header.dataset.order = asc ? "asc" : "desc";
    });
  });
});

function drawBarChart(id, label) {
  const el = document.getElementById(id);
  if (!el || !window.Chart) return;
  const labels = JSON.parse(el.dataset.labels || "[]");
  const values = JSON.parse(el.dataset.values || "[]");
  new Chart(el, {
    type: "bar",
    data: { labels, datasets: [{ label, data: values, backgroundColor: "#3f83a8", borderRadius: 4 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: id === "utilChart" ? 100 : undefined } } }
  });
}

drawBarChart("utilChart", "Allocation");
drawBarChart("skillChart", "Available Capacity");
