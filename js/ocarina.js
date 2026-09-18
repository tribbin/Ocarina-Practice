function installOcarinaTemplate(svgText) {
  let tpl = document.getElementById("oca-tpl");
  if (!tpl) {
    tpl = document.createElement("template");
    tpl.id = "oca-tpl";
    document.body.appendChild(tpl);
  }
  tpl.innerHTML = svgText;
}

function ocarinaSVG(covered, chamber) {
  try {
    const src = document.getElementById("oca-tpl");
    if (!src) return "<div>missing ocarina template</div>";
    const svg = src.content.querySelector("svg");
    if (!svg) return "<div>template has no svg</div>";
    const clone = svg.cloneNode(true);
    clone.setAttribute("class", "ocarina");
    clone.removeAttribute("width");
    clone.removeAttribute("height");
    clone.setAttribute("preserveAspectRatio", "xMidYMid meet");
    tagOcarinaParts(clone);
    const set = new Set(covered || []);
    const holes = (window.FING && FING.holes) || {};
    clone.querySelectorAll("[data-hole]").forEach(el => {
      const hid = el.getAttribute("data-hole") || "";
      const meta = holes[hid];
      // A hole is not drawn if it's absent from this instrument's fingering data
      // (e.g. a chamber this ocarina doesn't have), flagged ignored (tuning /
      // dead holes), or only active on chambers other than the current one.
      const activeOn = meta && meta.active_on_chambers;
      const inactive = Array.isArray(activeOn) && !activeOn.includes(chamber);
      if (!meta || meta.ignored || inactive) {
        el.style.fill = "none";
        el.style.strokeDasharray = "1.2 1";
        // Even though it is not playable in this view, the hole still belongs
        // to a chamber — fade it like the other non-current-chamber holes so
        // diagrams stay consistent between instruments.
        const holeCh = (meta && meta.chamber) || 0;
        if (!holeCh || holeCh !== chamber) el.style.opacity = "0.25";
        return;
      }
      el.style.fill = set.has(hid) ? "#1a120c" : "#ffffff";
      // Chamber comes from the fingering data, not the id.
      const holeCh = meta.chamber || 1;
      el.style.opacity = (holeCh === chamber) ? "1" : "0.25";
    });
    const chambers = (window.FING && FING.chambers) || {};
    const cfg = chambers[String(chamber)] || {};
    const blowName = cfg.blow || ("blow-ch" + chamber);
    const blowColor = cfg.color || "#8b3d2f";
    clone.querySelectorAll("[data-blow]").forEach(el => {
      const n = el.getAttribute("data-blow");
      el.style.fill = (n === blowName) ? blowColor : "#ffffff";
    });
    const bigBtn = document.getElementById("bigSmall");
    if (bigBtn && bigBtn.getAttribute("aria-pressed") === "true") {
      enlargeSmallHoles(clone);
    }
    return clone.outerHTML;
  } catch (e) {
    return "<div>" + String(e) + "</div>";
  }
}

function tagOcarinaParts(svg) {
  svg.querySelectorAll("*").forEach(el => {
    const lab = el.getAttribute("inkscape:label") || "";
    if (lab === "ocarina outline") el.classList.add("oca-body");
    else if (lab === "rim") el.classList.add("oca-rim");
    else if (lab === "triforce") el.classList.add("oca-deco");
    else if (lab.indexOf("relief") === 0) el.classList.add("oca-relief");
  });
}

function enlargeSmallHoles(svg) {
  const holeMeta = (window.FING && FING.holes) || {};
  const isSmall = hid => !!(holeMeta[hid] && holeMeta[hid].small);
  const geom = el => {
    const tag = el.tagName.toLowerCase();
    if (tag === "circle") {
      return { x:+el.getAttribute("cx"), y:+el.getAttribute("cy"), r:+el.getAttribute("r") || 0 };
    }
    const rx = +el.getAttribute("rx") || 0, ry = +el.getAttribute("ry") || 0;
    return { x:+el.getAttribute("cx"), y:+el.getAttribute("cy"), r:Math.max(rx, ry), rx, ry };
  };
  const holes = [...svg.querySelectorAll("[data-hole]")].filter(el => {
    const hid = el.getAttribute("data-hole") || "";
    return hid && el.style.visibility !== "hidden";
  }).map(el => ({ el, hid: el.getAttribute("data-hole"), ...geom(el) }));
  const GAP = 0.55;
  for (const h of holes) {
    if (!isSmall(h.hid)) continue;
    let maxR = Math.max(h.r * 1.7, 2.2);
    for (const o of holes) {
      if (o.el === h.el) continue;
      const dist = Math.hypot(h.x - o.x, h.y - o.y);
      const allowed = dist - o.r - GAP;
      if (allowed < maxR) maxR = allowed;
    }
    if (maxR <= h.r) continue;
    const s = maxR / h.r;
    if (h.el.tagName.toLowerCase() === "circle") {
      h.el.setAttribute("r", (h.r * s).toFixed(4));
    } else {
      h.el.setAttribute("rx", ((h.rx || h.r) * s).toFixed(4));
      h.el.setAttribute("ry", ((h.ry || h.r) * s).toFixed(4));
    }
    h.r *= s;
  }
}
