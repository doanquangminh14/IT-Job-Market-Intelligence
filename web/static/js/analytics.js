// Vẽ biểu đồ trang Phân tích thị trường từ dữ liệu JSON do Django nhúng (json_script id="chart-data")
(function () {
  const el = document.getElementById("chart-data");
  if (!el || typeof Chart === "undefined") return;
  const data = JSON.parse(el.textContent);

  const BRAND = "#2563eb";
  const ACCENT = "#06b6d4";
  const PALETTE = [
    "#2563eb", "#06b6d4", "#10b981", "#8b5cf6",
    "#f59e0b", "#ec4899", "#3b82f6", "#64748b"
  ];

  Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif";
  Chart.defaults.color = "#475569";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.font = { weight: 600, size: 12 };
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15, 23, 42, 0.92)";
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: "bold" };

  // Bấm vào cột/lát của biểu đồ để mở danh sách việc làm tương ứng (mỗi dòng dữ liệu có sẵn "url" do server tạo)
  function linkTo(rows) {
    return {
      onClick: (_evt, elements) => {
        const row = elements.length ? rows[elements[0].index] : null;
        if (row && row.url) window.location.href = row.url;
      },
      onHover: (evt, elements) => {
        const clickable = elements.length && rows[elements[0].index] && rows[elements[0].index].url;
        evt.native.target.style.cursor = clickable ? "pointer" : "default";
      },
    };
  }

  function draw(id, config) {
    const canvas = document.getElementById(id);
    if (canvas) new Chart(canvas, config);
  }

  function hbar(id, rows, labelKey, valueKey, color) {
    draw(id, {
      type: "bar",
      data: {
        labels: rows.map((r) => r[labelKey]),
        datasets: [{
          label: "Số tin",
          data: rows.map((r) => r[valueKey]),
          backgroundColor: color,
          borderRadius: 6,
          maxBarThickness: 24,
        }],
      },
      options: {
        ...linkTo(rows),
        indexAxis: "y",
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: "#f1f5f9" } },
          y: { grid: { display: false }, ticks: { font: { weight: 600 } } },
        },
      },
    });
  }

  function doughnut(id, rows) {
    draw(id, {
      type: "doughnut",
      data: {
        labels: rows.map((r) => r.label),
        datasets: [{
          data: rows.map((r) => r.n),
          backgroundColor: PALETTE,
          borderWidth: 2,
          borderColor: "#ffffff",
        }],
      },
      options: {
        ...linkTo(rows),
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { padding: 16, boxWidth: 10, usePointStyle: true },
          },
        },
      },
    });
  }

  hbar("chart-skills", data.skills, "label", "n", BRAND);
  hbar("chart-cities", data.cities, "label", "n", ACCENT);

  draw("chart-salary", {
    type: "bar",
    data: {
      labels: data.salary_by_city.map((r) => `${r.label} (${r.n})`),
      datasets: [
        {
          label: "Mức sàn trung vị",
          data: data.salary_by_city.map((r) => r.lo),
          backgroundColor: ACCENT,
          borderRadius: 6,
          maxBarThickness: 32,
        },
        {
          label: "Mức trần trung vị",
          data: data.salary_by_city.map((r) => r.hi),
          backgroundColor: BRAND,
          borderRadius: 6,
          maxBarThickness: 32,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { padding: 14 } },
        tooltip: {
          callbacks: {
            label: (c) => `${c.dataset.label}: ${c.parsed.y} triệu VNĐ`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: "Triệu VNĐ / tháng", font: { weight: 600 } },
          grid: { color: "#f1f5f9" },
        },
        x: { grid: { display: false }, ticks: { font: { weight: 600 } } },
      },
    },
  });

  doughnut("chart-workmode", data.work_modes);
  doughnut("chart-employment", data.employment_types);
  doughnut("chart-sources", data.sources);
})();
