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
    const set = new Set(covered || []);
    clone.querySelectorAll("[data-hole]").forEach(el => {
      const hid = el.getAttribute("data-hole") || "";
      if (hid === "R3-middle-high") {
        el.style.visibility = "hidden";
        return;
      }
      const ignore = hid.endsWith("tune") || (hid === "thumb" && chamber !== 1);
      if (ignore) {
        el.style.fill = "none";
        el.style.strokeDasharray = "1.2 1";
        return;
      }
      el.style.fill = set.has(hid) ? "#1a120c" : "#ffffff";
      const holeCh = hid.startsWith("R3") ? 3 : hid.startsWith("R2") ? 2 : 1;
      el.style.opacity = (holeCh === chamber) ? "1" : "0.25";
    });
    const blowFill = {1:"#8b3d2f", 2:"#2f5f73", 3:"#6b4a8b"};
    clone.querySelectorAll("[data-blow]").forEach(el => {
      const n = el.getAttribute("data-blow");
      el.style.fill = (n === ("blow-ch" + chamber)) ? (blowFill[chamber] || "#8b3d2f") : "#ffffff";
    });
    if (document.getElementById("bigSmall") && document.getElementById("bigSmall").checked) {
      enlargeSmallHoles(clone);
    }
    return clone.outerHTML;
  } catch (e) {
    return "<div>" + String(e) + "</div>";
  }
}

function enlargeSmallHoles(svg) {
  const SMALL = new Set([
    "L-middle-small","R1-middle-small","R2-middle-small","R2-pinky",
    "R3-middle-low","R3-pinky"
  ]);
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
    return hid && hid !== "R3-middle-high" && el.style.visibility !== "hidden";
  }).map(el => ({ el, hid: el.getAttribute("data-hole"), ...geom(el) }));
  const GAP = 0.55;
  for (const h of holes) {
    if (!SMALL.has(h.hid)) continue;
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
