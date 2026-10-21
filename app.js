(() => {
  const $ = (s) => document.querySelector(s);
  const esc = (s = "") => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ICONS = {
    blog: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/></svg>',
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
    insta: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    youtube: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 5 3-5 3z" fill="currentColor"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
  };
  const BADGE = { 쿠팡: "coupang", 여기어때: "stay", 마이리얼트립: "stay" };
  // 필터 칩 묶음: 여행 제휴처는 '여행'으로 모아 보여줌
  const GROUP = { 마이리얼트립: "여행", 여기어때: "여행" };
  const groupOf = (i) => GROUP[i.partner] || i.partner;

  // 클릭 통계(GoatCounter 설정 시)
  const track = (name) => { try { window.goatcounter?.count({ path: "click/" + name, title: name, event: true }); } catch (_) {} };
  document.addEventListener("click", (e) => { const a = e.target.closest("a[data-track]"); if (a) track(a.dataset.track); });

  const load = (u) => fetch(u + "?v=" + Date.now()).then((r) => (r.ok ? r.json() : null)).catch(() => null);

  Promise.all([load("config.json"), load("data/feed.json")]).then(([cfg, feed]) => {
    if (!cfg) return;
    feed = feed || { posts: {}, affiliates: [] };
    const P = cfg.profile;

    // 프로필
    $("#avatar").src = P.image;
    $("#name").textContent = P.name;
    $("#bio").textContent = P.bio || "";
    if (cfg.notice?.show && cfg.notice.text) {
      const n = $("#notice"); n.hidden = false; n.textContent = cfg.notice.text;
      if (cfg.notice.url) { n.href = cfg.notice.url; n.target = "_blank"; n.rel = "noopener"; n.dataset.track = "notice"; }
    }

    // 바로가기
    const linkHtml = (l) => `
      <a class="link${l.highlight ? " hl" : ""}${l.color ? " " + esc(l.color) : ""}" href="${esc(l.url)}" ${l.url.startsWith("mailto:") ? "" : 'target="_blank" rel="noopener"'} data-track="${esc(l.id)}">
        <span class="ic">${ICONS[l.icon] || ICONS.link}</span>
        <span class="tx"><span class="t">${esc(l.title)}</span>${l.sub ? `<span class="s">${esc(l.sub)}</span>` : ""}</span>
        <span class="go" aria-hidden="true">→</span>
      </a>`;
    // type "pair": 다른 채널 묶음 — 제목·설명 아래 버튼 2개를 가로로
    const pairHtml = (g) => `
      <div class="pair${g.color ? " " + esc(g.color) : ""}">
        <p class="pair-head">${g.title ? `<span class="t">${esc(g.title)}</span>` : ""}${g.sub ? `<span class="s">${esc(g.sub)}</span>` : ""}</p>
        <div class="pair-row">${g.items.map((l) => `
          <a class="pair-btn" href="${esc(l.url)}" target="_blank" rel="noopener" data-track="${esc(l.id)}">
            <span class="ic">${ICONS[l.icon] || ICONS.link}</span>
            <span class="tx"><span class="t">${esc(l.title)}</span>${l.sub ? `<span class="s">${esc(l.sub)}</span>` : ""}</span>
          </a>`).join("")}
        </div>
      </div>`;
    $("#links").innerHTML = cfg.links.filter((l) => !l.hidden).map((l) => (l.type === "pair" ? pairHtml(l) : linkHtml(l))).join("");

    // 추천템 = 직접 등록 상품(위) + 블로그 자동 수집
    const items = [
      ...(cfg.products || []).filter((p) => !p.hidden).map((p) => ({ ...p, thumb: p.image, manual: true })),
      ...(feed.affiliates || []),
    ];
    const partners = [...new Set(items.map(groupOf))];
    const counts = items.reduce((m, i) => ((m[groupOf(i)] = (m[groupOf(i)] || 0) + 1), m), { 전체: items.length });
    let pf = "전체";
    const renderItems = () => {
      const list = pf === "전체" ? items : items.filter((i) => groupOf(i) === pf);
      $("#items").innerHTML = list.length ? list.map((i, k) => `
        <article class="item">
          <a class="ph" href="${esc(i.url)}" target="_blank" rel="noopener sponsored" data-track="item-${k}">
            ${i.thumb ? `<img src="${esc(i.thumb)}" alt="" loading="lazy">` : `<span class="noimg" aria-hidden="true">${i.kind === "숙소" ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18V7M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5"/><circle cx="7" cy="11" r="1.6"/></svg><b>STAY</b>' : ""}</span>`}
            <span class="badge ${BADGE[i.partner] || ""}">${esc(i.kind || i.partner)}</span>
          </a>
          <div class="bd">
            <p class="t">${esc(i.title)}</p>
            ${i.price ? `<p class="price">${esc(i.price)}<span>~</span></p>` : ""}
            ${i.note ? `<p class="note">${esc(i.note)}</p>` : ""}
            <a class="buy" href="${esc(i.url)}" target="_blank" rel="noopener sponsored" data-track="buy-${k}">${esc(i.cta || (i.kind === "숙소" ? "숙소 보기" : GROUP[i.partner] ? "예약하러 가기" : "보러 가기"))}</a>
            ${i.postUrl ? `<a class="rv" href="${esc(i.postUrl)}" target="_blank" rel="noopener" data-track="review-${k}">${GROUP[i.partner] ? "여행 코스 글 보기" : "소현 후기 읽기"}</a>` : ""}
          </div>
        </article>`).join("") : `<p class="empty">곧 추천템이 올라와요</p>`;
    };
    const renderChips = (el, names, counts, cur, on) => {
      el.innerHTML = names.map((n) => `<button class="chip" aria-pressed="${n === cur}" data-v="${esc(n)}">${esc(n)}${counts ? `<span class="n">${counts[n] ?? ""}</span>` : ""}</button>`).join("");
      el.onclick = (e) => { const b = e.target.closest(".chip"); if (b) on(b.dataset.v); };
    };
    const itemChips = () => renderChips($("#item-filters"), ["전체", ...partners], counts, pf, (v) => { pf = v; itemChips(); renderItems(); });
    if (partners.length > 1) itemChips(); else $("#item-filters").hidden = true;
    renderItems();

    // 블로그 새 글 (카테고리별)
    const cats = cfg.blog.categories.filter((c) => (feed.posts[c.name] || []).length);
    const all = cats.flatMap((c) => feed.posts[c.name].map((p) => ({ ...p, chip: c.chip, label: c.label }))).sort((a, b) => (a.date < b.date ? 1 : -1));
    let bf = "전체";
    const renderPosts = () => {
      const c = cats.find((x) => x.label === bf);
      const list = c ? all.filter((p) => p.category === c.name) : all.slice(0, cfg.blog.perCategory * 2);
      $("#posts").innerHTML = list.length ? list.map((p, k) => `
        <li class="post"><a href="${esc(p.url)}" target="_blank" rel="noopener" data-track="post-${k}">
          <span class="th">${p.thumb ? `<img src="${esc(p.thumb)}" alt="" loading="lazy">` : ""}</span>
          <span class="tx"><span class="cat ${p.chip}">${esc(p.label)}</span><span class="t">${esc(p.title)}</span><span class="d">${esc(p.date)}</span></span>
        </a></li>`).join("") : `<li class="empty">아직 글이 없어요</li>`;
      $("#blog-more").href = `https://blog.naver.com/${cfg.blog.id}`;
    };
    const blogChips = () => renderChips($("#blog-filters"), ["전체", ...cats.map((c) => c.label)], null, bf, (v) => { bf = v; blogChips(); renderPosts(); });
    blogChips(); renderPosts();

    // 탭
    const tabs = [["#tab-items", "#panel-items"], ["#tab-blog", "#panel-blog"]];
    const show = (i) => tabs.forEach(([t, p], k) => { $(t).setAttribute("aria-selected", k === i); $(p).hidden = k !== i; });
    tabs.forEach(([t], i) => $(t).addEventListener("click", () => show(i)));
    if (!items.length) show(1);

    $("#disclosure").textContent = cfg.affiliate.disclosure;
    if (feed.updated) $("#updated").textContent = "업데이트 " + feed.updated;

    if (cfg.goatcounter) {
      const s = document.createElement("script");
      s.async = true; s.src = "https://gc.zgo.at/count.js"; s.dataset.goatcounter = `https://${cfg.goatcounter}.goatcounter.com/count`;
      document.body.appendChild(s);
    }
  });
})();
