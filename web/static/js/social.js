// Trang Cộng đồng – Stage 2. Tăng cường tiến dần: mọi nút đều là form POST hoạt động cả khi tắt JS;
// có JS thì Thích / Theo dõi gửi bằng fetch để không tải lại trang. Không dùng innerHTML.
(function () {
  "use strict";

  document.querySelectorAll("form[data-toggle-form]").forEach((form) => {
    form.addEventListener("submit", async (evt) => {
      evt.preventDefault();
      const btn = form.querySelector("button");
      btn.disabled = true;
      try {
        const resp = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),  // gồm csrfmiddlewaretoken
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        });
        if (!resp.ok) { form.submit(); return; }  // lỗi → gửi form thường để server báo lỗi
        const data = await resp.json();
        btn.setAttribute("aria-pressed", String(data.pressed));
        const label = btn.querySelector("[data-label]");
        if (label) label.textContent = data.pressed ? btn.dataset.labelOn : btn.dataset.labelOff;
        const count = btn.querySelector("[data-count]");
        if (count && typeof data.count === "number") count.textContent = String(data.count);
        const followers = document.querySelector("[data-follower-count]");
        if (followers && form.action.endsWith("/follow/") && typeof data.count === "number") {
          followers.textContent = String(data.count);
        }
      } catch (_e) {
        form.submit();
      } finally {
        btn.disabled = false;
      }
    });
  });

  const composer = document.querySelector("[data-composer]");
  if (composer) {
    const area = composer.querySelector("textarea");
    const counter = composer.querySelector("[data-composer-count]");
    const max = area.getAttribute("maxlength");
    area.addEventListener("input", () => { counter.textContent = `${area.value.length}/${max}`; });
  }
})();
