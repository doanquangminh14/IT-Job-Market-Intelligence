// Trang Cộng đồng – Stage 1 (bản demo). Mọi thao tác chỉ diễn ra trên trình duyệt, không gửi lên server.
// An toàn: nội dung người dùng gõ chỉ được gán bằng textContent (không innerHTML) và KHÔNG được lưu lại;
// localStorage chỉ lưu id bài viết / username.
(function () {
  "use strict";

  const knownEl = document.getElementById("community-known");
  const known = knownEl ? JSON.parse(knownEl.textContent) : { following_seed: [], me: "" };
  const KEYS = { likes: "community.likes", follows: "community.follows", banner: "community.bannerDismissed" };
  const USERNAME_RE = /^[\w.\-]{1,50}$/;

  // ---------- Lưu trữ (bỏ qua dữ liệu hỏng / sai kiểu) ----------
  function loadList(key, valid, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return fallback;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(valid) : fallback;
    } catch (_e) {
      return fallback;
    }
  }
  function saveList(key, list) {
    try { localStorage.setItem(key, JSON.stringify(Array.from(new Set(list)))); } catch (_e) { /* bộ nhớ đầy / bị chặn */ }
  }
  let likes = loadList(KEYS.likes, (v) => Number.isInteger(v) && v > 0, []);
  let follows = loadList(KEYS.follows, (v) => typeof v === "string" && USERNAME_RE.test(v), known.following_seed || []);

  // ---------- Thông báo ngắn; nhắc "chưa lưu" một lần mỗi phiên ----------
  const toastEl = document.querySelector("[data-toast]");
  let toastTimer = null;
  function toast(message) {
    if (!toastEl) return;
    let text = message;
    if (!sessionStorage.getItem("community.demoNoticeShown")) {
      text += " (Bản demo – chưa lưu)";
      sessionStorage.setItem("community.demoNoticeShown", "1");
    }
    toastEl.textContent = text;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 3000);
  }

  // ---------- Banner demo ----------
  const banner = document.querySelector("[data-demo-banner]");
  if (banner) {
    if (localStorage.getItem(KEYS.banner) === "1") banner.hidden = true;
    const close = banner.querySelector("[data-demo-banner-close]");
    if (close) close.addEventListener("click", () => {
      banner.hidden = true;
      try { localStorage.setItem(KEYS.banner, "1"); } catch (_e) { /* ignore */ }
    });
  }

  // ---------- Thích / Theo dõi ----------
  function setPressed(btn, pressed) {
    btn.setAttribute("aria-pressed", String(pressed));
    const action = btn.dataset.action;
    const label = btn.querySelector("[data-label]");
    if (label) label.textContent = action === "like" ? (pressed ? "Đã thích" : "Thích") : (pressed ? "Đang theo dõi" : "Theo dõi");
    const count = btn.querySelector("[data-count]");
    if (count) {
      if (!("base" in count.dataset)) count.dataset.base = count.textContent.trim();
      count.textContent = String(Number(count.dataset.base) + (pressed ? 1 : 0));
    }
  }
  function syncButtons() {
    document.querySelectorAll('[data-action="like"]').forEach((b) => setPressed(b, likes.includes(Number(b.dataset.target))));
    document.querySelectorAll('[data-action="follow"]').forEach((b) => setPressed(b, follows.includes(b.dataset.target)));
  }

  document.addEventListener("click", (evt) => {
    const btn = evt.target.closest("button[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    if (action === "like") {
      const id = Number(btn.dataset.target);
      const on = !likes.includes(id);
      likes = on ? likes.concat(id) : likes.filter((x) => x !== id);
      saveList(KEYS.likes, likes);
      syncButtons();
      toast(on ? "Đã thích bài viết" : "Đã bỏ thích");
    } else if (action === "follow") {
      const name = btn.dataset.target;
      if (!USERNAME_RE.test(name)) return;
      const on = !follows.includes(name);
      follows = on ? follows.concat(name) : follows.filter((x) => x !== name);
      saveList(KEYS.follows, follows);
      syncButtons();
      applyTab();
      toast(on ? `Đang theo dõi ${name}` : `Đã bỏ theo dõi ${name}`);
    } else if (action === "report") {
      toast("Cảm ơn bạn, báo cáo đã được ghi nhận");
    }
  });

  // ---------- Tab Mới nhất / Đang theo dõi ----------
  let currentTab = "latest";
  function applyTab() {
    const feed = document.querySelector("[data-feed]");
    if (!feed) return;
    let visible = 0;
    feed.querySelectorAll("[data-post]").forEach((post) => {
      const show = currentTab === "latest" || follows.includes(post.dataset.author) || post.classList.contains("cm-preview");
      post.hidden = !show;
      if (show) visible += 1;
    });
    const empty = document.querySelector("[data-following-empty]");
    if (empty) empty.hidden = !(currentTab === "following" && visible === 0);
  }
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      currentTab = tab.dataset.tab;
      document.querySelectorAll("[data-tab]").forEach((t) => t.setAttribute("aria-pressed", String(t === tab)));
      applyTab();
    });
  });

  // ---------- Xem trước bài viết / bình luận (không lưu) ----------
  function initials(name) {
    const parts = name.replace(/_/g, ".").split(".").filter(Boolean);
    return parts.slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
  }
  function fromTemplate(id, body) {
    const tpl = document.getElementById(id);
    if (!tpl) return null;
    const node = tpl.content.firstElementChild.cloneNode(true);
    const me = known.me || "bạn";
    node.querySelector('[data-slot="initials"]').textContent = initials(me);
    node.querySelector('[data-slot="username"]').textContent = me;
    node.querySelector('[data-slot="body"]').textContent = body;
    return node;
  }

  const composer = document.querySelector("[data-composer]");
  if (composer) {
    const area = composer.querySelector("textarea");
    const counter = composer.querySelector("[data-composer-count]");
    const max = Number(area.getAttribute("maxlength"));
    area.addEventListener("input", () => { counter.textContent = `${area.value.length}/${max}`; });
    composer.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const body = area.value.trim().slice(0, max);
      if (!body) { area.focus(); toast("Hãy viết nội dung trước khi đăng"); return; }
      const tags = composer.querySelector('[name="tags"]').value.split(",")
        .map((t) => t.trim().slice(0, 30)).filter(Boolean).slice(0, 5);
      const node = fromTemplate("tpl-post", body);
      if (!node) return;
      node.dataset.author = known.me || "";
      const tagBox = node.querySelector('[data-slot="tags"]');
      tags.forEach((t) => {
        const chip = document.createElement("span");
        chip.className = "cm-tag";
        chip.textContent = `#${t}`;
        tagBox.appendChild(chip);
      });
      const feed = document.querySelector("[data-feed]");
      feed.querySelectorAll(".cm-empty").forEach((e) => e.remove());
      node.tabIndex = -1;
      feed.prepend(node);
      composer.reset();
      counter.textContent = `0/${max}`;
      node.focus();
      toast("Đã thêm bài viết xem trước");
    });
  }

  const commentForm = document.querySelector("[data-comment-form]");
  if (commentForm) {
    commentForm.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const area = commentForm.querySelector("textarea");
      const body = area.value.trim().slice(0, Number(area.getAttribute("maxlength")));
      if (!body) { area.focus(); return; }
      const node = fromTemplate("tpl-comment", body);
      const list = document.querySelector("[data-comments]");
      const emptyMsg = list.querySelector("[data-comments-empty]");
      if (emptyMsg) emptyMsg.remove();
      list.appendChild(node);
      commentForm.reset();
      area.focus();
      toast("Đã thêm bình luận xem trước");
    });
  }

  syncButtons();
  applyTab();
})();
