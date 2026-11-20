// Vẽ biểu đồ trang Phân tích thị trường từ dữ liệu JSON do Django nhúng (json_script id="chart-data")
(function () {
  const el = document.getElementById("chart-data");
  if (!el || typeof Chart === "undefined") return;
  const data = JSON.parse(el.textContent);

  const BRAND = "#1f4e79";
  const ACCENT = "#5b9bd5";
  const PALETTE = ["#1f4e79", "#2e75b6", "#5b9bd5", "#9dc3e6", "#c55a11", "#70ad47", "#ffc000", "#7f7f7f"];

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = "#555";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;

  function draw(id, config) {
    const canvas = document.getElementById(id);
    if (canvas) new Chart(canvas, config);
  }

  function hbar(id, rows, labelKey, valueKey, color) {
    draw(id, {
      type: "bar",
      data: {
        labels: rows.map((r) => r[labelKey]),
        datasets: [{ label: "Số tin", data: rows.map((r) => r[valueKey]), backgroundColor: color, borderRadius: 4 }],
      },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, grid: { color: "#eee" } }, y: { grid: { display: false } } },
      },
    });
  }

  function doughnut(id, rows) {
    draw(id, {
      type: "doughnut",
      data: {
        labels: rows.map((r) => r.label),
        datasets: [{ data: rows.map((r) => r.n), backgroundColor: PALETTE, borderWidth: 1 }],
      },
      options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
    });
  }

  hbar("chart-skills", data.skills, "name", "n", BRAND);
  hbar("chart-cities", data.cities, "label", "n", ACCENT);

  draw("chart-salary", {
    type: "bar",
    data: {
      labels: data.salary_by_city.map((r) => `${r.label} (${r.n})`),
      datasets: [
        { label: "Mức sàn TB", data: data.salary_by_city.map((r) => r.lo), backgroundColor: ACCENT, borderRadius: 4 },
        { label: "Mức trần TB", data: data.salary_by_city.map((r) => r.hi), backgroundColor: BRAND, borderRadius: 4 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" },
                 tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y} triệu` } } },
      scales: { y: { beginAtZero: true, title: { display: true, text: "triệu VNĐ" } }, x: { grid: { display: false } } },
    },
  });

  doughnut("chart-workmode", data.work_modes);
  doughnut("chart-employment", data.employment_types);
  doughnut("chart-sources", data.sources);
})();
