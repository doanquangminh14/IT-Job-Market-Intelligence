// web/js/app.js - Logic ứng dụng Single Page Application cho IT Job Market Intelligence

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initFilterOptions();
  loadJobs(1);
  initRecommender();
  loadAnalytics();
  initModal();
});

// 1. ĐIỀU HƯỚNG TABS
function initNavigation() {
  const tabs = document.querySelectorAll(".nav-tab-btn");
  const views = document.querySelectorAll(".view-section");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetView = tab.getAttribute("data-target");

      tabs.forEach(t => t.classList.remove("active"));
      views.forEach(v => v.classList.remove("active"));

      tab.classList.add("active");
      const activeEl = document.getElementById(targetView);
      if (activeEl) {
        activeEl.classList.add("active");
      }

      if (targetView === "view-analytics") {
        renderAllCharts();
      }
    });
  });
}

// 2. KHÁM PHÁ VIỆC LÀM (JOB EXPLORER)
let currentPage = 1;

async function initFilterOptions() {
  try {
    const res = await fetch("/api/jobs/filter-options");
    const data = await res.json();

    const citySelect = document.getElementById("filter-city");
    const senioritySelect = document.getElementById("filter-seniority");
    const workModeSelect = document.getElementById("filter-work-mode");

    const recCity = document.getElementById("rec-city");
    const recSeniority = document.getElementById("rec-seniority");
    const recWorkMode = document.getElementById("rec-work-mode");

    if (data.cities) {
      populateSelect(citySelect, data.cities);
      populateSelect(recCity, data.cities);
    }
    if (data.seniorities) {
      populateSelect(senioritySelect, data.seniorities);
      populateSelect(recSeniority, data.seniorities);
    }
    if (data.work_modes) {
      populateSelect(workModeSelect, data.work_modes);
      populateSelect(recWorkMode, data.work_modes);
    }
  } catch (err) {
    console.error("Lỗi nạp bộ lọc:", err);
  }
}

function populateSelect(selectEl, items) {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    selectEl.appendChild(opt);
  });
}

document.getElementById("btn-search")?.addEventListener("click", () => {
  currentPage = 1;
  loadJobs(1);
});

document.getElementById("btn-reset")?.addEventListener("click", () => {
  document.getElementById("search-keyword").value = "";
  document.getElementById("filter-city").value = "Tất cả";
  document.getElementById("filter-seniority").value = "Tất cả";
  document.getElementById("filter-work-mode").value = "Tất cả";
  currentPage = 1;
  loadJobs(1);
});

document.getElementById("search-keyword")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    currentPage = 1;
    loadJobs(1);
  }
});

async function loadJobs(page = 1) {
  const container = document.getElementById("jobs-container");
  const countEl = document.getElementById("total-jobs-count");
  const paginationEl = document.getElementById("pagination-container");

  if (!container) return;
  container.innerHTML = `<div style="text-align:center; padding:3rem 0; color:#64748b; font-weight:600;">Đang tải danh sách việc làm từ cơ sở dữ liệu...</div>`;

  const keyword = document.getElementById("search-keyword")?.value || "";
  const city = document.getElementById("filter-city")?.value || "Tất cả";
  const seniority = document.getElementById("filter-seniority")?.value || "Tất cả";
  const workMode = document.getElementById("filter-work-mode")?.value || "Tất cả";

  const params = new URLSearchParams({
    page: page,
    page_size: 12,
    city: city,
    seniority: seniority,
    work_mode: workMode
  });
  if (keyword.trim()) params.append("keyword", keyword.trim());

  try {
    const res = await fetch(`/api/jobs/search?${params.toString()}`);
    const data = await res.json();

    if (countEl) {
      countEl.innerHTML = `Tìm thấy <span>${data.total.toLocaleString()}</span> cơ hội việc làm CNTT phù hợp`;
    }

    if (!data.jobs || data.jobs.length === 0) {
      container.innerHTML = `
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:3rem 2rem; text-align:center;">
          <h4 style="font-size:1.15rem; color:#0f172a; margin-bottom:0.5rem; font-weight:700;">Không tìm thấy việc làm phù hợp</h4>
          <p style="color:#64748b; font-size:0.9rem;">Bạn hãy thử thay đổi từ khóa tìm kiếm hoặc chọn Địa điểm: Tất cả để mở rộng phạm vi.</p>
        </div>
      `;
      if (paginationEl) paginationEl.innerHTML = "";
      return;
    }

    container.innerHTML = data.jobs.map(job => renderJobCard(job)).join("");

    renderPagination(data.page, data.total_pages);
  } catch (err) {
    console.error("Lỗi tải việc làm:", err);
    container.innerHTML = `<div style="text-align:center; color:#dc2626; padding:2rem 0;">Lỗi kết nối tới máy chủ. Vui lòng thử lại sau.</div>`;
  }
}

function renderJobCard(job, rank = null, matchScore = null, semanticScore = null, skillScore = null, matchedSkills = [], missingSkills = []) {
  const companyName = job.company_name || job.company || "Doanh nghiệp IT";
  const initial = companyName ? companyName.charAt(0).toUpperCase() : "IT";
  const logoUrl = job.company_logo_url ? job.company_logo_url.trim() : "";

  const logoHtml = logoUrl
    ? `<img src="${logoUrl}" alt="${companyName}" class="company-logo" onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(companyName)}&background=4f46e5&color=fff&size=128';" />`
    : `<div class="company-avatar-fallback">${initial}</div>`;

  const skillsArr = job.skills || [];
  const skillsHtml = skillsArr.slice(0, 8).map(s => `<span class="skill-chip">${s}</span>`).join("");

  const rankHtml = rank !== null ? `<div class="badge-rank">HẠNG #${String(rank).padStart(2, '0')}</div>` : "";
  const matchHtml = matchScore !== null
    ? `
      <div style="text-align:right;">
        <span class="badge-match">Phù hợp: ${matchScore}%</span>
        <div style="font-size:0.74rem; color:#64748b; margin-top:0.25rem;">Ngữ nghĩa: ${semanticScore}% | Kỹ năng: ${skillScore}%</div>
      </div>
    `
    : "";

  const matchedChips = matchedSkills.length > 0
    ? matchedSkills.map(s => `<span class="skill-chip skill-chip-matched">${s}</span>`).join("")
    : `<span style="color:#94a3b8; font-size:0.78rem;">Chưa có kỹ năng trùng khớp</span>`;

  const missingChips = missingSkills.length > 0
    ? missingSkills.slice(0, 5).map(s => `<span class="skill-chip skill-chip-missing">${s}</span>`).join("")
    : `<span style="color:#059669; font-size:0.78rem; font-weight:600;">Bạn đáp ứng đủ kỹ năng yêu cầu</span>`;

  const skillsMatchBlock = rank !== null
    ? `
      <div style="margin-top:0.65rem; padding-top:0.65rem; border-top:1px dashed #e2e8f0;">
        <div style="margin-bottom:0.35rem;"><strong style="font-size:0.8rem; color:#0f172a;">Kỹ năng bạn đã có:</strong> <div style="display:inline-flex; flex-wrap:wrap; gap:4px; margin-left:4px;">${matchedChips}</div></div>
        <div><strong style="font-size:0.8rem; color:#0f172a;">Kỹ năng khuyên trang bị thêm:</strong> <div style="display:inline-flex; flex-wrap:wrap; gap:4px; margin-left:4px;">${missingChips}</div></div>
      </div>
    `
    : "";

  return `
    <div class="job-card" data-id="${job.job_id}">
      ${logoHtml}
      <div class="job-card-content">
        <div class="job-header">
          <div>
            ${rankHtml}
            <h3 class="job-title" onclick="openJobDetail(${job.job_id})">${job.title}</h3>
            <p class="company-name">${companyName}</p>
          </div>
          ${matchHtml}
        </div>

        <div class="specs-bar">
          <span class="spec-chip spec-salary">Lương: ${job.salary_display || job.salary_str}</span>
          <span class="spec-chip">Địa điểm: ${job.city}</span>
          <span class="spec-chip">Cấp bậc: ${job.seniority_level}</span>
          <span class="spec-chip">Kinh nghiệm: ${job.experience_str || "Không yêu cầu"}</span>
          <span class="spec-chip">Hình thức: ${job.work_mode}</span>
          ${job.deadline_str ? `<span class="spec-chip">Hạn nộp: ${job.deadline_str}</span>` : ""}
        </div>

        ${job.description_snippet ? `<div class="desc-snippet">${job.description_snippet}</div>` : ""}

        ${skillsArr.length > 0 && rank === null ? `<div class="skills-container">${skillsHtml}</div>` : ""}
        ${skillsMatchBlock}

        <div class="card-actions">
          <button class="btn-sm btn-outline" onclick="openJobDetail(${job.job_id})">Xem Chi Tiết Tin</button>
          ${job.url ? `<a href="${job.url}" target="_blank" rel="noopener noreferrer" class="btn-sm btn-primary">Ứng Tuyển Nguồn</a>` : ""}
        </div>
      </div>
    </div>
  `;
}

function renderPagination(current, total) {
  const container = document.getElementById("pagination-container");
  if (!container) return;

  container.innerHTML = `
    <div class="pagination-bar">
      <button class="page-btn" ${current <= 1 ? "disabled" : ""} onclick="changePage(${current - 1})">Trang trước</button>
      <span class="page-indicator">Trang ${current} / ${total}</span>
      <button class="page-btn" ${current >= total ? "disabled" : ""} onclick="changePage(${current + 1})">Trang sau</button>
    </div>
  `;
}

window.changePage = function(page) {
  currentPage = page;
  loadJobs(page);
  window.scrollTo({ top: 400, behavior: "smooth" });
};

// 3. GỢI Ý VIỆC LÀM AI (AI RECOMMENDER)
async function initRecommender() {
  const presetsContainer = document.getElementById("presets-container");
  const textarea = document.getElementById("rec-profile-input");

  try {
    const res = await fetch("/api/recommender/presets");
    const presets = await res.json();

    if (presetsContainer) {
      presetsContainer.innerHTML = presets.map(p => `
        <button class="preset-btn" onclick="applyPreset('${p.id}')">
          ${p.name}
        </button>
      `).join("");
      window._PRESETS_DATA = presets;
    }
  } catch (err) {
    console.error("Lỗi nạp presets:", err);
  }

  document.getElementById("btn-run-match")?.addEventListener("click", runRecommenderMatch);
}

window.applyPreset = function(presetId) {
  const textarea = document.getElementById("rec-profile-input");
  const preset = (window._PRESETS_DATA || []).find(p => p.id === presetId);
  if (preset && textarea) {
    textarea.value = preset.text;
  }
};

async function runRecommenderMatch() {
  const textarea = document.getElementById("rec-profile-input");
  const text = textarea?.value?.trim() || "";
  const btn = document.getElementById("btn-run-match");
  const resultsContainer = document.getElementById("rec-results-container");

  if (!text) {
    alert("Vui lòng nhập nội dung mô tả kỹ năng hoặc chọn một hồ sơ mẫu.");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Hệ thống đang phân tích ngữ nghĩa và tính toán...";
  resultsContainer.innerHTML = `<div style="text-align:center; padding:3rem 0; color:#4f46e5; font-weight:700;">Mô hình NLP đa ngữ đang tính toán độ tương đồng vector 384 chiều...</div>`;

  const city = document.getElementById("rec-city")?.value || "Tất cả";
  const seniority = document.getElementById("rec-seniority")?.value || "Tất cả";
  const workMode = document.getElementById("rec-work-mode")?.value || "Tất cả";
  const topN = parseInt(document.getElementById("rec-top-n")?.value || "12");

  try {
    const res = await fetch("/api/recommender/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile_text: text,
        top_n: topN,
        city: city,
        seniority: seniority,
        work_mode: workMode
      })
    });

    const data = await res.json();
    btn.disabled = false;
    btn.textContent = "Phân Tích AI & Gợi Ý Việc Làm";

    if (!res.ok) {
      resultsContainer.innerHTML = `
        <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:16px; padding:2rem; text-align:center; color:#991b1b;">
          <h4 style="font-size:1.1rem; font-weight:700; margin-bottom:0.4rem;">Đã xảy ra lỗi</h4>
          <p style="font-size:0.9rem;">${data.detail || "Không thể xử lý yêu cầu gợi ý lúc này. Vui lòng thử lại."}</p>
        </div>
      `;
      return;
    }

    if (!data.recommendations || data.recommendations.length === 0) {
      resultsContainer.innerHTML = `
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:3rem 2rem; text-align:center;">
          <h4 style="font-size:1.15rem; color:#0f172a; margin-bottom:0.5rem; font-weight:700;">Không tìm thấy việc làm thỏa mãn bộ lọc</h4>
          <p style="color:#64748b; font-size:0.9rem;">Bạn hãy thử chuyển Thành phố hoặc Cấp bậc về 'Tất cả' để mở rộng phạm vi.</p>
        </div>
      `;
      return;
    }

    const skillsHtml = (data.candidate_skills || []).map(s => `<span class="skill-chip skill-chip-matched" style="font-size:0.82rem; padding:0.3rem 0.75rem;">${s}</span>`).join("");

    const topScore = data.recommendations[0].match_score;
    const topRole = data.recommendations[0].title;

    resultsContainer.innerHTML = `
      <div style="margin-bottom:1.5rem; background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <h4 style="font-size:1.05rem; font-weight:800; color:#0f172a; margin-bottom:0.75rem;">Kỹ năng công nghệ nhận diện từ hồ sơ của bạn:</h4>
        <div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-bottom:1.25rem;">
          ${skillsHtml || `<span style="color:#64748b; font-size:0.86rem;">Chưa phát hiện tên kỹ năng cụ thể. Áp dụng 100% độ tương đồng ngữ nghĩa.</span>`}
        </div>

        <div class="kpi-grid" style="margin-bottom:0;">
          <div class="kpi-card" style="padding:1.2rem;">
            <div class="kpi-label">Độ phù hợp cao nhất</div>
            <div class="kpi-value" style="font-size:1.6rem; color:#059669;">${topScore}%</div>
            <div class="kpi-sub">Xếp hạng 1 danh sách</div>
          </div>
          <div class="kpi-card" style="padding:1.2rem;">
            <div class="kpi-label">Số việc làm đề xuất</div>
            <div class="kpi-value" style="font-size:1.6rem; color:#4f46e5;">${data.recommendations.length} tin</div>
            <div class="kpi-sub">Thỏa mãn tiêu chí lọc</div>
          </div>
          <div class="kpi-card" style="padding:1.2rem;">
            <div class="kpi-label">Kỹ năng nhận diện</div>
            <div class="kpi-value" style="font-size:1.6rem; color:#0284c7;">${data.candidate_skills.length} kỹ năng</div>
            <div class="kpi-sub">Chuẩn hóa theo danh mục</div>
          </div>
        </div>
      </div>

      <div style="margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center;">
        <h3 style="font-size:1.2rem; font-weight:800; color:#0f172a;">Bảng Xếp Hạng Việc Làm Phù Hợp Nhất</h3>
        <span style="font-size:0.84rem; color:#64748b;">Mô hình Hybrid: 65% Ngữ Nghĩa Vector + 35% Kỹ Năng</span>
      </div>

      <div>
        ${data.recommendations.map((job, idx) => renderJobCard(
          job,
          idx + 1,
          job.match_score,
          job.semantic_score,
          job.skill_score,
          job.matched_skills,
          job.missing_skills
        )).join("")}
      </div>
    `;

    resultsContainer.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    console.error("Lỗi gợi ý việc làm:", err);
    btn.disabled = false;
    btn.textContent = "Phân Tích AI & Gợi Ý Việc Làm";
    resultsContainer.innerHTML = `<div style="text-align:center; color:#dc2626; padding:2rem 0;">Đã xảy ra lỗi trong quá trình phân tích. Vui lòng thử lại.</div>`;
  }
}

// 4. PHÂN TÍCH THỊ TRƯỜNG & BIỂU ĐỒ (MARKET ANALYTICS)
let chartSkillsInstance = null;
let chartRolesInstance = null;
let chartGeoInstance = null;

async function loadAnalytics() {
  try {
    const kpiRes = await fetch("/api/analytics/kpis");
    const kpis = await kpiRes.json();

    document.getElementById("stat-total-jobs").textContent = kpis.total_postings ? kpis.total_postings.toLocaleString() : "2,821";
    document.getElementById("stat-active-companies").textContent = kpis.total_companies ? kpis.total_companies.toLocaleString() : "1,436";
    document.getElementById("stat-avg-salary").textContent = `${kpis.avg_min_salary_million} - ${kpis.avg_max_salary_million} Tr`;
    document.getElementById("stat-remote-ratio").textContent = `${kpis.remote_ratio_pct}%`;
  } catch (err) {
    console.error("Lỗi nạp KPI phân tích:", err);
  }
}

async function renderAllCharts() {
  if (typeof Chart === "undefined") return;

  try {
    // 1. Biểu đồ Top kỹ năng
    const skillsRes = await fetch("/api/analytics/top-skills?limit=10");
    const skillsData = await skillsRes.json();

    const ctxSkills = document.getElementById("chart-skills")?.getContext("2d");
    if (ctxSkills) {
      if (chartSkillsInstance) chartSkillsInstance.destroy();
      chartSkillsInstance = new Chart(ctxSkills, {
        type: "bar",
        data: {
          labels: skillsData.map(s => s.skill_name),
          datasets: [{
            label: "Số lượng tin tuyển dụng yêu cầu",
            data: skillsData.map(s => s.job_count),
            backgroundColor: "#4f46e5",
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // 2. Biểu đồ lương theo cấp bậc
    const rolesRes = await fetch("/api/analytics/roles-salary");
    const rolesData = await rolesRes.json();

    const ctxRoles = document.getElementById("chart-roles")?.getContext("2d");
    if (ctxRoles) {
      if (chartRolesInstance) chartRolesInstance.destroy();
      chartRolesInstance = new Chart(ctxRoles, {
        type: "bar",
        data: {
          labels: rolesData.map(r => r.seniority_level),
          datasets: [
            {
              label: "Lương tối thiểu (Triệu VNĐ)",
              data: rolesData.map(r => r.avg_min_million),
              backgroundColor: "#93c5fd",
              borderRadius: 6
            },
            {
              label: "Lương tối đa (Triệu VNĐ)",
              data: rolesData.map(r => r.avg_max_million),
              backgroundColor: "#10b981",
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // 3. Biểu đồ địa lý
    const geoRes = await fetch("/api/analytics/geo-distribution");
    const geoData = await geoRes.json();

    const ctxGeo = document.getElementById("chart-geo")?.getContext("2d");
    if (ctxGeo) {
      if (chartGeoInstance) chartGeoInstance.destroy();
      chartGeoInstance = new Chart(ctxGeo, {
        type: "doughnut",
        data: {
          labels: geoData.map(g => g.city),
          datasets: [{
            data: geoData.map(g => g.total_jobs),
            backgroundColor: ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#64748b"]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right" } }
        }
      });
    }

    // 4. Bảng doanh nghiệp tuyển dụng
    const compRes = await fetch("/api/analytics/top-companies?limit=8");
    const compData = await compRes.json();
    const tableBody = document.getElementById("top-companies-body");
    if (tableBody) {
      tableBody.innerHTML = compData.map((c, i) => `
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:0.75rem 0.5rem; font-weight:700; color:#64748b;">#0${i + 1}</td>
          <td style="padding:0.75rem 0.5rem; font-weight:700; color:#0f172a;">${c.company_name}</td>
          <td style="padding:0.75rem 0.5rem; color:#475569;">${c.city}</td>
          <td style="padding:0.75rem 0.5rem; font-weight:800; color:#4f46e5;">${c.total_postings} tin</td>
          <td style="padding:0.75rem 0.5rem; color:#059669; font-weight:600;">${c.avg_min_mil} - ${c.avg_max_mil} Tr</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Lỗi vẽ biểu đồ:", err);
  }
}

// 5. MODAL CHI TIẾT TIN TUYỂN DỤNG
function initModal() {
  const modal = document.getElementById("job-modal");
  const closeBtn = document.getElementById("modal-close-btn");

  closeBtn?.addEventListener("click", () => {
    modal.classList.remove("active");
  });

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.remove("active");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("active")) {
      modal.classList.remove("active");
    }
  });
}

window.openJobDetail = async function(jobId) {
  const modal = document.getElementById("job-modal");
  const contentEl = document.getElementById("modal-body-content");
  if (!modal || !contentEl) return;

  modal.classList.add("active");
  contentEl.innerHTML = `<div style="text-align:center; padding:3rem 0; color:#64748b;">Đang tải toàn văn tin tuyển dụng...</div>`;

  try {
    const res = await fetch(`/api/jobs/${jobId}`);
    const job = await res.json();

    const logoHtml = job.company_logo_url
      ? `<img src="${job.company_logo_url}" alt="${job.company_name}" style="width:72px; height:72px; object-fit:contain; border-radius:12px; border:1px solid #e2e8f0; background:#ffffff; padding:4px;" onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(job.company_name)}&background=4f46e5&color=fff&size=128';" />`
      : `<div class="company-avatar-fallback">${job.company_name.charAt(0)}</div>`;

    const skillsHtml = (job.skills || []).map(s => `<span class="skill-chip">${s}</span>`).join("");

    contentEl.innerHTML = `
      <div style="display:flex; gap:1.25rem; align-items:flex-start; margin-bottom:1.25rem;">
        ${logoHtml}
        <div>
          <h2 style="font-size:1.35rem; font-weight:800; color:#0f172a; line-height:1.3;">${job.title}</h2>
          <p style="font-size:1rem; font-weight:700; color:#4f46e5; margin-top:0.25rem;">${job.company_name}</p>
          ${job.company_url ? `<a href="${job.company_url}" target="_blank" rel="noopener" style="font-size:0.8rem; color:#64748b; text-decoration:none;">Xem trang doanh nghiệp</a>` : ""}
        </div>
      </div>

      <div class="specs-bar" style="margin-bottom:1.5rem;">
        <span class="spec-chip spec-salary">Lương: ${job.salary_display}</span>
        <span class="spec-chip">Địa điểm: ${job.city}</span>
        <span class="spec-chip">Cấp bậc: ${job.seniority_level}</span>
        <span class="spec-chip">Kinh nghiệm: ${job.experience_str}</span>
        <span class="spec-chip">Hình thức: ${job.work_mode}</span>
        <span class="spec-chip">Hạn nộp: ${job.deadline_str}</span>
      </div>

      ${skillsHtml ? `
        <div style="margin-bottom:1.25rem;">
          <h5 style="font-size:0.85rem; font-weight:700; color:#0f172a; margin-bottom:0.4rem;">Kỹ năng công nghệ yêu cầu:</h5>
          <div style="display:flex; flex-wrap:wrap; gap:0.35rem;">${skillsHtml}</div>
        </div>
      ` : ""}

      <div class="modal-section">
        <h5>Mô tả công việc:</h5>
        <p>${job.description}</p>
      </div>

      <div class="modal-section">
        <h5>Yêu cầu chuyên môn:</h5>
        <p>${job.requirements}</p>
      </div>

      ${job.benefits ? `
        <div class="modal-section">
          <h5>Chế độ đãi ngộ:</h5>
          <p>${job.benefits}</p>
        </div>
      ` : ""}

      <div style="margin-top:2rem; padding-top:1.25rem; border-top:1px solid #e2e8f0; display:flex; justify-content:flex-end; gap:0.75rem;">
        <button class="btn-outline" onclick="document.getElementById('job-modal').classList.remove('active')">Đóng</button>
        ${job.source_job_url ? `<a href="${job.source_job_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="text-decoration:none; display:inline-flex; align-items:center;">Ứng Tuyển Tại Sàn Gốc</a>` : ""}
      </div>
    `;
  } catch (err) {
    console.error("Lỗi xem chi tiết việc làm:", err);
    contentEl.innerHTML = `<div style="text-align:center; color:#dc2626; padding:2rem 0;">Lỗi khi tải thông tin việc làm.</div>`;
  }
};
