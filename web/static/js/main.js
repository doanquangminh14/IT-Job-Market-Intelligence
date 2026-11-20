// Tự ẩn thông báo (Django messages) sau vài giây
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-autodismiss]").forEach((el) => {
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 5000);
  });

  // Ảnh logo lỗi ➔ thay bằng biểu tượng mặc định
  document.querySelectorAll("img.company-logo").forEach((img) => {
    img.addEventListener("error", () => {
      const ph = document.createElement("span");
      ph.className = "company-logo company-logo-placeholder";
      ph.innerHTML = '<i class="bi bi-building"></i>';
      img.replaceWith(ph);
    }, { once: true });
  });
});
