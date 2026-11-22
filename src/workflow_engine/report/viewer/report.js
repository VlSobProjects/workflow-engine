(() => {
  "use strict";
  // The viewer of ADR 022. It presents the model the engine embedded beside it and computes no
  // engine fact: transitions are built, values rendered and origins decided in Python.
  const MODEL = JSON.parse(document.getElementById("report-data").textContent);
  const app = document.getElementById("app");
  let highlight = null;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const nodeA = (id) => `node-${slug(id)}`;
  const visitA = (r) => `visit-${slug(r.node_id)}-${r.visit}` + (r.attempt > 1 ? `-a${r.attempt}` : "");
  const paramA = (n) => `param-${slug(n)}`;
  const time = (ts) => ts ? ts.slice(11, 23) : "";
  const ms = (a, b) => Math.round(new Date(b) - new Date(a));
  const shortCodec = (c) => c.replace(/^builtins\./, "").replace(/^pathlib\._local\./, "pathlib.");

  function endingText(m) {
    const e = m.session.ending, n = m.session.nodes_visited;
    const node = (id) => `<a class="mono" href="#${nodeA(id)}">${esc(id)}</a>`;
    if (e.status === "completed") return `Completed at ${node(e.node_id)} after ${n} node visits.`;
    if (e.status === "failed") return `Failed${e.node_id ? ` at ${node(e.node_id)}` : ""}${e.code ? ` under <code class="err">${esc(e.code)}</code>` : ""} after ${n} node visits.`;
    if (m.pending && m.pending.kind === "question") return `Paused at ${node(e.node_id)}, waiting for an answer.`;
    if (m.pending && m.pending.kind === "budget") return `Paused before ${node(e.node_id)}: the session budget of ${m.pending.max_nodes_visited} node visits is spent.`;
    if (m.pending && m.pending.kind === "safety") return `Paused before ${node(e.node_id)}: the global safety cap of ${m.pending.hard_max_nodes_visited} node visits is reached.`;
    if (m.pending && m.pending.kind === "interrupted") return `Interrupted at ${node(e.node_id)} after ${n} node visits: the run ended with no outcome recorded.`;
    if (m.pending && m.pending.kind === "start") return `Not started yet: the run begins at ${node(m.pending.node_id)}.`;
    return `${esc(e.status)} (${esc(e.event)}).`;
  }

  function guardChip(g) {
    return `<span class="g ${g.passed ? "pass" : "fail"}" title="${esc(g.name)} ${g.passed ? "held" : "did not hold"}">${esc(g.name)}</span>`;
  }
  function targetHtml(t) {
    if (t.kind === "node") return `<span class="to">→ <a href="#${nodeA(t.target)}">${esc(t.target)}</a></span>`;
    if (t.kind === "end") return `<span class="to end">■ end</span>`;
    if (t.kind === "fail") return `<span class="to fail">✕ fail ${t.target ? esc(t.target) : "(own code)"}</span>`;
    return `<span class="to">${esc(t.kind)}</span>`;
  }
  function visitRow(r, i) {
    const writes = (r.writes || []).map((w) => `<a href="#${paramA(w.name)}">${esc(w.name)}</a> <span title="${esc(w.codec)}">${esc(w.mode)}</span>`).join(", ");
    const arts = (r.artifacts || []).map((a) => esc(typeof a === "string" ? a : a.name)).join(", ");
    return `<div class="visit ${r.status === "failed" ? "failed" : ""} ${highlight === r.node_id ? "hl" : ""}" id="${visitA(r)}" data-node="${esc(r.node_id)}" data-seq="${i + 1}">
      <span class="seq">${i + 1}</span>
      <div class="who"><a class="node" href="#${nodeA(r.node_id)}">${esc(r.node_id)}</a>
        <div class="ord">visit ${r.visit}${r.attempt > 1 ? ` · attempt ${r.attempt}` : ""} · <a href="#${visitA(r)}" title="Link to this visit">${time(r.timestamp)}</a></div></div>
      <div class="what">
        <span class="fn">${esc(r.function ? `${r.action}:${r.function}` : r.action)}</span>
        ${r.error_code ? `<span class="err">${esc(r.error_code)}</span>` : ""}
        ${(r.guards || []).map(guardChip).join("")}
        ${targetHtml(r.transition)}
        ${r.taken_origin ? `<span class="hint">${esc(r.taken_origin)}</span>` : ""}
        ${writes ? `<span class="w">writes ${writes}</span>` : ""}
        ${arts ? `<span class="w">artifact ${arts}</span>` : ""}
      </div></div>`;
  }

  // Presentation only: group the path into passes of the first node that is visited again.
  function segment(path) {
    const seen = new Map();
    let head = null;
    for (const r of path) { if (seen.has(r.node_id)) { head = r.node_id; break; } seen.set(r.node_id, true); }
    if (!head) return [{ type: "visits", items: path.map((r, i) => [r, i]) }];
    const first = path.findIndex((r) => r.node_id === head);
    const starts = path.map((r, i) => (r.node_id === head ? i : -1)).filter((i) => i >= 0);
    const passes = starts.map((s, k) => path.slice(s, k + 1 < starts.length ? starts[k + 1] : path.length).map((r, j) => [r, s + j]));
    const body = new Set(passes.slice(0, -1).flat().map(([r]) => r.node_id));
    const last = passes[passes.length - 1];
    let cut = last.findIndex(([r], j) => j > 0 && !body.has(r.node_id));
    let after = [];
    if (cut >= 0) { after = last.slice(cut); passes[passes.length - 1] = last.slice(0, cut); }
    return [
      { type: "visits", items: path.slice(0, first).map((r, i) => [r, i]) },
      { type: "loop", head, passes, open: false },
      { type: "visits", items: after },
    ].filter((s) => s.type === "loop" || s.items.length);
  }

  function routeHtml(items) {
    return items.map(([r], j) => {
      const g = (r.guards || []).find((x) => x.passed);
      return `${j ? '<span class="arr">→</span>' : ""}<span class="step ${highlight === r.node_id ? "hl" : ""}" title="${esc(g ? g.name : "")}">${esc(r.node_id)}</span>`;
    }).join("") + (items.length && items[items.length - 1][0].transition.kind !== "node" ? "" : "");
  }

  function pathHtml(m, filter) {
    const segs = segment(m.path);
    const match = (r) => (!filter.node || r.node_id === filter.node) && (!filter.failed || r.status === "failed");
    const filtering = filter.node || filter.failed;
    const out = [];
    for (const s of segs) {
      if (s.type === "visits") { out.push(s.items.filter(([r]) => match(r)).map(([r, i]) => visitRow(r, i)).join("")); continue; }
      const mixes = new Map();
      s.passes.forEach((p) => { const k = p.map(([r]) => r.node_id).join(" → "); mixes.set(k, (mixes.get(k) || 0) + 1); });
      const total = s.passes.reduce((a, p) => a + p.length, 0);
      const open = filtering || state.openLoops.has(s.head) || (location.hash && s.passes.some((p) => p.some(([r]) => "#" + visitA(r) === location.hash)));
      const passesHtml = s.passes.map((p, k) => {
        const vis = p.filter(([r]) => match(r));
        if (filtering && !vis.length) return "";
        const key = `${s.head}:${k}`;
        const popen = filtering || state.openPasses.has(key) || (location.hash && p.some(([r]) => "#" + visitA(r) === location.hash));
        return `<div class="pass" data-open="${popen}">
          <button class="pass-head" data-pass="${esc(key)}" aria-expanded="${popen}"><span class="seq">${p[0][1] + 1}</span>
            <span class="route"><span class="label" style="margin-right:6px">pass ${k + 1}</span>${routeHtml(p)}</span></button>
          <div class="pass-body" ${popen ? "" : "hidden"}>${vis.map(([r, i]) => visitRow(r, i)).join("")}</div></div>`;
      }).join("");
      out.push(`<div class="loop" data-open="${open}">
        <button class="loop-head" data-loop="${esc(s.head)}" aria-expanded="${open}"><span class="chev">▸</span>
          <span>Loop at <strong>${esc(s.head)}</strong> · ${s.passes.length} passes · ${total} visits</span>
          <span class="mix">${[...mixes].map(([k, c]) => `<span>${c}× ${esc(k)}</span>`).join("<span>·</span>")}</span></button>
        <div class="loop-body" ${open ? "" : "hidden"}>${passesHtml}</div></div>`);
    }
    if (m.pending && m.pending.kind === "budget") out.push(`<div class="cut-note">The run stopped here: the next visit would be <strong class="mono">${esc(m.pending.node_id)}</strong>, and the budget of ${m.pending.max_nodes_visited} visits is spent.</div>`);
    if (m.pending && m.pending.kind === "interrupted") out.push(`<div class="cut-note">The run ended here with no outcome recorded; the state stands at <strong class="mono">${esc(m.pending.node_id)}</strong>.</div>`);
    if (m.pending && m.pending.kind === "safety") out.push(`<div class="cut-note">The run stopped here: the next visit would be <strong class="mono">${esc(m.pending.node_id)}</strong>, and the global safety cap of ${m.pending.hard_max_nodes_visited} visits is reached.</div>`);
    if (m.pending && m.pending.kind === "question") out.push(`<div class="cut-note">The run waits at <strong class="mono">${esc(m.pending.node_id)}</strong>. Its action has not run yet, so it has no visit.</div>`);
    return out.join("");
  }

  function jsonHtml(obj, refs) {
    const s = JSON.stringify(obj, null, 2);
    return esc(s).replace(/(&quot;(?:[^&]|&(?!quot;))*?&quot;)(\s*:)?/g, (mm, str, colon) => {
      if (colon) return `<span class="k">${str}</span>${colon}`;
      const inner = str.slice(6, -6);
      if (/^(param|output|artifact)\./.test(inner)) return `<span class="s">&quot;<span class="p">${inner}</span>&quot;</span>`;
      return `<span class="s">${str}</span>`;
    });
  }
  function tmplHtml(t) { return esc(t ?? "").replace(/\$\{([^}]+)\}/g, '<span class="ref">${$1}</span>'); }

  function visitsByNode(m) {
    const visits = new Map();
    m.path.forEach((r) => { if (!visits.has(r.node_id)) visits.set(r.node_id, []); visits.get(r.node_id).push(r); });
    return visits;
  }
  function guardCell(g) {
    if (!g) return '<span class="hint">always</span>';
    if (g.startsWith("errors:")) return `<span class="codes"><span class="hint">error is one of</span>${g.slice(7).split(",").map((c) => `<code>${esc(c)}</code>`).join("")}</span>`;
    return esc(g);
  }
  function guardShort(g) {
    if (!g) return "";
    if (g.startsWith("errors:")) { const n = g.slice(7).split(",").length; return n === 1 ? g.slice(7) : `errors (${n})`; }
    return g.length > 24 ? g.slice(0, 23) + "…" : g;
  }
  function nodeFunction(n) {
    const ap = n.written.action_parameters || {};
    if (ap.function_name) return ap.function_name;
    if (ap.functions) return `${Object.keys(ap.functions).length} functions`;
    return "";
  }

  function nodeCard(m, n, inDialog) {
    const vs = visitsByNode(m).get(n.id) || [];
    const counts = new Map();
    vs.forEach((r) => counts.set(r.taken_origin, (counts.get(r.taken_origin) || 0) + 1));
    const tags = [
      n.id === m.definition.start_node_id ? '<span class="tag start">start</span>' : "",
      m.pending && m.pending.node_id === n.id ? `<span class="tag pending">${m.pending.kind === "question" ? "run waits here" : "next node at the pause"}</span>` : "",
      `<span class="tag">${esc(n.action_type)}</span>`,
      vs.length ? `<span class="hint">${vs.length} visit${vs.length > 1 ? "s" : ""}</span>` : '<span class="hint">not visited</span>',
    ].join("");
    return `<article class="nodecard" ${inDialog ? "" : `id="print-${nodeA(n.id)}"`}>
      <header><h3>${esc(n.id)}</h3>${tags}
        <span style="margin-left:auto;display:flex;gap:6px">
        ${vs.length ? `<button class="btn" data-hl="${esc(n.id)}" style="font-size:12px;padding:2px 8px">${highlight === n.id ? "Clear highlight" : "Highlight visits in path"}</button>` : ""}
        ${inDialog ? '<button class="x" data-close aria-label="Close">Close</button>' : ""}</span></header>
      <div class="views">
        <div><span class="label">As written</span><pre class="json">${jsonHtml(n.written)}</pre></div>
        <div><span class="label">As built · effective transitions in order</span>
          ${n.build_error ? `<div class="build-err">The node does not build with the components loaded when this report was written: ${esc(n.build_error)}. ${n.effective.length ? "Its transitions are built without the action." : "Its transitions could not be built either; the view as written is all there is."}</div>` : ""}
          ${n.effective.length ? `<table class="tr"><thead><tr><th>Origin</th><th>Guard</th><th>Target</th><th title="visits that took it">Taken</th></tr></thead><tbody>
          ${n.effective.map((t) => `<tr><td>${esc(t.origin)}</td><td>${guardCell(t.guard)}${t.attempts ? ' <span class="hint">attempts</span>' : ""}</td><td>${targetHtml(t)}</td><td class="n">${counts.get(t.origin) || ""}</td></tr>`).join("")}
          </tbody></table>` : `<p class="hint" style="margin:0">No transitions: a <code>${esc(n.action_type)}</code> node ends the workflow itself.</p>`}</div>
      </div>
      ${vs.length ? `<div class="visits-of"><span class="label" style="margin-right:4px">Visits</span>${vs.map((r) => `<a class="${r.status === "failed" ? "f" : ""}" href="#${visitA(r)}" title="${esc(r.status)}">${r.visit}${r.attempt > 1 ? "." + r.attempt : ""}</a>`).join("")}</div>` : ""}
    </article>`;
  }

  function graphList(m) {
    const visits = visitsByNode(m);
    return `<div class="graph" aria-label="The graph as a list">${m.definition.nodes.map((n) => {
      const c = (visits.get(n.id) || []).length;
      return `<div class="row ${c ? "" : "unvisited"}"><span>${n.id === m.definition.start_node_id ? '<span class="start" title="start node">▶ </span>' : ""}<a class="node" href="#${nodeA(n.id)}">${esc(n.id)}</a>${n.build_error ? ' <span class="err" title="does not build now">✕ build</span>' : ""}</span>
        <span class="cnt" title="visits">${c ? c + "×" : "—"}</span>
        <span class="tgts">${n.effective.map((t) => `<span>${t.guard ? `<span class="hint">${esc(guardShort(t.guard))}</span> ` : ""}${targetHtml(t)}</span>`).join("")}</span></div>`;
    }).join("")}</div>`;
  }

  // Presentation only: a layered drawing of the definition. Back edges (to a node still on the
  // depth-first stack) run in lanes on the right; end and fail targets are small terminals.
  function diagramSvg(m) {
    const nodes = m.definition.nodes, byId = new Map(nodes.map((n) => [n.id, n]));
    const visits = visitsByNode(m);
    const taken = new Map();
    m.path.forEach((r) => { const k = r.node_id + "|" + r.taken_origin; taken.set(k, (taken.get(k) || 0) + 1); });
    const terms = new Map(), edges = [];
    nodes.forEach((n) => n.effective.forEach((t) => {
      let to = t.target;
      if (t.kind !== "node") {
        to = `~${t.kind}~${n.id}~${t.target || ""}`;
        if (!terms.has(to)) terms.set(to, { id: to, kind: t.kind, code: t.target, parent: n.id });
      }
      edges.push({ from: n.id, to, guard: t.guard, count: taken.get(n.id + "|" + t.origin) || 0 });
    }));
    const out = new Map();
    edges.forEach((e) => { if (!out.has(e.from)) out.set(e.from, []); out.get(e.from).push(e); });
    const mark = new Map(), post = [];
    const dfs = (u) => {
      mark.set(u, 1);
      for (const e of out.get(u) || []) {
        if (e.from === e.to) { e.self = true; continue; }
        const s = mark.get(e.to);
        if (s === 1) e.back = true; else if (!s) dfs(e.to);
      }
      mark.set(u, 2); post.push(u);
    };
    dfs(m.definition.start_node_id);
    nodes.forEach((n) => { if (!mark.has(n.id)) dfs(n.id); });
    const rank = new Map();
    post.slice().reverse().forEach((u) => {
      if (!rank.has(u)) rank.set(u, 0);
      for (const e of out.get(u) || []) if (!e.back && !e.self) rank.set(e.to, Math.max(rank.get(e.to) ?? 0, rank.get(u) + 1));
    });
    const NW = 196, NH = 50, TH = 26, GX = 30, GY = 66, PAD = 14;
    const size = (id) => terms.has(id) ? { w: Math.max(64, 18 + 6.6 * (terms.get(id).kind === "end" ? 3 : (terms.get(id).code || "own code").length + 2)), h: TH } : { w: NW, h: NH };
    const rows = [];
    rank.forEach((r, id) => { (rows[r] = rows[r] || []).push(id); });
    const defIdx = (id) => terms.has(id) ? nodes.findIndex((n) => n.id === terms.get(id).parent) + 0.5 : nodes.findIndex((n) => n.id === id);
    const pos = new Map();
    let maxW = 0;
    rows.forEach((row, r) => {
      const preds = (id) => edges.filter((e) => e.to === id && !e.back && !e.self && pos.has(e.from)).map((e) => pos.get(e.from).cx);
      row.sort((a, b) => {
        const pa = preds(a), pb = preds(b);
        const ba = pa.length ? pa.reduce((x, y) => x + y) / pa.length : 0, bb = pb.length ? pb.reduce((x, y) => x + y) / pb.length : 0;
        return ba - bb || defIdx(a) - defIdx(b);
      });
      let x = 0;
      row.forEach((id) => { const s = size(id); pos.set(id, { x, w: s.w, h: s.h, r }); x += s.w + GX; });
      row.width = x - GX; maxW = Math.max(maxW, row.width);
    });
    rows.forEach((row, r) => {
      const off = (maxW - row.width) / 2;
      row.forEach((id) => { const p = pos.get(id); p.x += off + PAD; p.y = PAD + r * (NH + GY) + (NH - p.h) / 2; p.cx = p.x + p.w / 2; p.cy = p.y + p.h / 2; });
    });
    const backs = edges.filter((e) => e.back);
    const selfs = edges.some((e) => e.self) ? 44 : 0;
    const laneBase = maxW + PAD + 22 + selfs;
    const W = laneBase + backs.length * 18 + 30, H = PAD * 2 + rows.length * (NH + GY) - GY;
    const label = (x, y, e) => {
      const txt = [guardShort(e.guard), e.count ? `×${e.count}` : ""].filter(Boolean).join("  ");
      if (!txt) return "";
      const w = txt.length * 6.3 + 8;
      return `<g class="gl ${e.count ? "taken" : ""}"><title>${esc(e.guard || "always")}${e.count ? ` · taken ${e.count}×` : " · never taken"}</title><rect x="${x - w / 2}" y="${y - 8}" width="${w}" height="15" rx="3"/><text x="${x}" y="${y + 3.5}" text-anchor="middle">${esc(txt)}</text></g>`;
    };
    const edgeSvg = edges.map((e) => {
      const a = pos.get(e.from), b = pos.get(e.to), cls = e.count ? "taken" : "";
      const mk = `url(#ah${e.count ? "t" : "m"})`;
      if (e.self) {
        const x = a.x + a.w, y = a.cy;
        return `<path class="ge ${cls}" marker-end="${mk}" d="M${x} ${y - 10} C${x + 40} ${y - 34}, ${x + 40} ${y + 34}, ${x + 3} ${y + 11}"/>${label(x + 30, y, e)}`;
      }
      if (e.back) {
        const lane = laneBase + backs.indexOf(e) * 18, sx = a.x + a.w, sy = a.cy, tx = b.x + b.w, ty = b.cy - 8, rr = 8;
        return `<path class="ge ${cls}" marker-end="${mk}" d="M${sx} ${sy} H${lane - rr} Q${lane} ${sy} ${lane} ${sy - rr} V${ty + rr} Q${lane} ${ty} ${lane - rr} ${ty} H${tx + 4}"/>${e.count ? label(lane, (sy + ty) / 2, { ...e, guard: null }) : ""}`;
      }
      const sx = a.cx + (b.cx - a.cx) * 0.18, sy = a.y + a.h, tx = b.cx, ty = b.y - 3, dy = (ty - sy) / 2;
      return `<path class="ge ${cls}" marker-end="${mk}" d="M${sx} ${sy} C${sx} ${sy + dy}, ${tx} ${ty - dy}, ${tx} ${ty}"/>${label((sx + tx) / 2, (sy + ty) / 2, e)}`;
    }).join("");
    const nodeSvg = [...pos].map(([id, p]) => {
      if (terms.has(id)) {
        const t = terms.get(id);
        return `<g class="term ${t.kind}"><rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="${p.h / 2}"/><text x="${p.cx}" y="${p.cy + 4}" text-anchor="middle">${t.kind === "end" ? "■ end" : "✕ " + esc(t.code || "own code")}</text></g>`;
      }
      const n = byId.get(id), vs = visits.get(id) || [];
      const failed = vs.some((r) => r.status === "failed"), pend = m.pending && m.pending.node_id === id;
      const cls = [vs.length ? "visited" : "unvisited", failed ? "failed" : "", pend ? "pending" : "", n.build_error ? "unbuilt" : "", highlight === id ? "hl" : ""].join(" ");
      const fn = nodeFunction(n);
      const sub = `${n.action_type}${fn ? " · " + fn : ""}`;
      return `<a class="gn ${cls}" href="#${nodeA(id)}" aria-label="${esc(id)}, ${vs.length} visits"><title>${esc(id)} · ${esc(sub)}${n.build_error ? " · does not build now" : ""}</title>
        <rect class="box" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="7"/>
        ${id === m.definition.start_node_id ? `<path class="start" d="M${p.x - 11} ${p.cy - 6} L${p.x - 3} ${p.cy} L${p.x - 11} ${p.cy + 6} Z"/>` : ""}
        <text class="id" x="${p.x + 10}" y="${p.y + 20}">${esc(id.length > 19 ? id.slice(0, 18) + "…" : id)}</text>
        <text class="sub" x="${p.x + 10}" y="${p.y + 37}">${esc(sub.length > 27 ? sub.slice(0, 26) + "…" : sub)}</text>
        <text class="cnt" x="${p.x + p.w - 9}" y="${p.y + 20}" text-anchor="end">${vs.length ? vs.length + "×" : "—"}</text>
        ${pend ? `<text class="flag" x="${p.x + p.w - 9}" y="${p.y + 37}" text-anchor="end">${m.pending.kind === "question" ? "waits" : "next"}</text>` : ""}</a>`;
    }).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" style="min-width:${Math.min(W, 560)}px" role="img" aria-label="Graph of ${esc(m.definition.flow_id)}">
      <defs><marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker>
      <marker id="aht" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah taken" d="M0 0 L10 5 L0 10 z"/></marker></defs>
      ${edgeSvg}${nodeSvg}</svg>`;
  }

  function nodesHtml(m) {
    const seg = `<div class="tools"><span class="viewseg" role="group" aria-label="Graph view">
      <button data-view="diagram" aria-pressed="${state.view === "diagram"}">Diagram</button><button data-view="list" aria-pressed="${state.view === "list"}">List</button></span>
      <span class="hint">Click a node to open it</span></div>`;
    const legend = `<div class="legend"><span><i></i>taken in this run, ×count</span><span><i class="never"></i>never taken</span><span><b></b>visited</span><span><b class="un"></b>not visited</span><span><b class="fa"></b>failed</span>${m.definition.nodes.some((n) => n.build_error) ? '<span><b class="ub"></b>does not build now</span>' : ""}${m.pending ? '<span><b class="pe"></b>where the run stands</span>' : ""}</div>`;
    const body = state.view === "diagram" ? `<div class="diagram">${diagramSvg(m)}</div>${legend}` : graphList(m);
    return `${seg}${body}<div class="print-only">${m.definition.nodes.map((n) => nodeCard(m, n, false)).join("")}</div>`;
  }

  const dlg = document.getElementById("node-dlg");
  function openNode(id) {
    const m = MODEL;
    const n = m.definition.nodes.find((x) => nodeA(x.id) === id);
    if (!n) return false;
    dlg.innerHTML = nodeCard(m, n, true);
    if (!dlg.open) dlg.showModal();
    return true;
  }
  dlg.addEventListener("close", () => { if (location.hash.startsWith("#node-")) history.replaceState(null, "", location.pathname + location.search); });
  dlg.addEventListener("click", (ev) => {
    if (ev.target === dlg || ev.target.closest("[data-close]")) { dlg.close(); return; }
    const hl = ev.target.closest("[data-hl]");
    if (hl) { dlg.close(); state.tab = "path"; history.replaceState(null, "", "#path"); setHighlight(hl.dataset.hl); window.scrollTo(0, 0); return; }
    if (ev.target.closest('a[href^="#visit-"]')) dlg.close();
  });

  function paramsHtml(m) {
    if (!m.parameters.length) return `<p class="hint">The session holds no parameter.</p>`;
    const sid = m.session.id;
    return `<div class="tbl"><table><thead><tr><th>Name</th><th>Codec</th><th>Written by</th><th>Value</th></tr></thead><tbody>
      ${m.parameters.map((p) => `<tr id="${paramA(p.name)}"><td class="mono">${esc(p.name)}</td><td class="mono" title="${esc(p.codec)}">${esc(shortCodec(p.codec))}</td>
        <td>${p.is_input ? '<span class="tag">input</span>' : `<a class="mono" href="#${nodeA(p.source_node)}">${esc(p.source_node)}</a>`}</td>
        <td>${p.value === null ? '<span class="hint">not included in this report</span>' : `<div class="val">${esc(p.value)}${p.cut ? "…" : ""}</div>`}${p.cut ? `<span class="cutmark">Cut at ${m.options.value_cut} of ${p.length} characters. Read it whole with <code>workflow-engine show-parameter --session-id ${esc(sid)} --name ${esc(p.name)}</code></span>` : ""}</td></tr>`).join("")}
      </tbody></table></div>`;
  }
  function artifactsHtml(m) {
    if (!m.artifacts.length) return `<p class="hint">The session registered no artifact${m.definition.deliverables.length ? `; it declares ${m.definition.deliverables.map((d) => `<code>${esc(d)}</code>`).join(", ")} as deliverables` : ""}.</p>`;
    return `<div class="tbl"><table><thead><tr><th>Name</th><th>Path in the session</th><th>Description</th></tr></thead><tbody>
      ${m.artifacts.map((a) => `<tr><td class="mono">${esc(a.name)} ${a.deliverable ? '<span class="tag">deliverable</span>' : ""}</td><td class="mono">artifacts/${esc(a.path)}</td><td>${esc(a.description)}</td></tr>`).join("")}
      </tbody></table></div>`;
  }
  function journalHtml(m) {
    return `<div class="tbl"><table class="ev"><thead><tr><th>Time</th><th>Actor</th><th>Event</th><th>Details</th></tr></thead><tbody>
      ${m.journal.map((e) => `<tr><td>${time(e.timestamp)}</td><td>${esc(e.actor)}</td><td class="mono">${esc(e.code)}</td><td class="val">${esc(Object.entries(e.details || {}).filter(([k]) => k !== "session_id").map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("  ·  "))}</td></tr>`).join("")}
      </tbody></table></div>`;
  }
  function inputsHtml(m) {
    const ins = m.definition.inputs || [];
    if (!ins.length) return "";
    const val = (n) => {
      const p = m.parameters.find((x) => x.name === n);
      if (!p) return "not bound";
      return p.value === null ? "value not included" : p.value + (p.cut ? "…" : "");
    };
    return `<div class="facts">${ins.map((i) => `<div><span class="label">input ${esc(i.name)}${i.type ? ` · ${esc(i.type)}` : ""}</span><span class="v"><a href="#${paramA(i.name)}">${esc(val(i.name))}</a></span></div>`).join("")}</div>`;
  }

  function unbuiltHtml(m) {
    const ids = m.definition.nodes.filter((n) => n.build_error).map((n) => n.id);
    if (!ids.length) return "";
    return `<div class="build-err">${ids.length === 1 ? "1 node does" : `${ids.length} nodes do`} not build with the components loaded when this report was written: ${ids.map((id) => `<a class="mono" href="#${nodeA(id)}">${esc(id)}</a>`).join(", ")}. The run is reported as recorded; open the node for the reason.</div>`;
  }

  function pendingHtml(m) {
    const p = m.pending;
    if (!p) return "";
    const copy = `<div class="cmd"><pre>${esc(p.resume)}</pre><button data-copy>Copy</button></div>`;
    if (p.kind === "budget") return `<section class="pending" id="pending"><h2>Paused: session budget spent</h2>
      <p style="margin:0">The run made ${p.nodes_visited} of the ${p.max_nodes_visited} node visits the session allows. Its next node is <a class="mono" href="#${nodeA(p.node_id)}">${esc(p.node_id)}</a>. Raise the limit and resume:</p>${copy}</section>`;
    if (p.kind === "safety") return `<section class="pending" id="pending"><h2>Paused: global safety cap reached</h2>
      <p style="margin:0">The run made ${p.nodes_visited} node visits and reached the cap of ${p.hard_max_nodes_visited} that no session command raises. Its next node is <a class="mono" href="#${nodeA(p.node_id)}">${esc(p.node_id)}</a>. Raise <code>hard_max_nodes_visited</code> in the engine configuration and resume:</p>${copy}</section>`;
    if (p.kind === "interrupted") return `<section class="pending" id="pending"><h2>Interrupted: the run ended with no outcome</h2>
      <p style="margin:0">The run was entered and recorded neither a completion, a failure nor a pause, so the process ended mid-run. The state stands at <a class="mono" href="#${nodeA(p.node_id)}">${esc(p.node_id)}</a>. Resume it from there:</p>${copy}</section>`;
    if (p.kind === "start") return `<section class="pending" id="pending"><h2>Not started</h2>
      <p style="margin:0">The session exists and has not run. Its first node is <a class="mono" href="#${nodeA(p.node_id)}">${esc(p.node_id)}</a>. Start it:</p>${copy}</section>`;
    // The question as presented is resolved by the engine; the viewer only chooses which view to show.
    const presented = state.question === "presented" && p.presented;
    const fields = presented ? p.presented.fields : p.presentation;
    const lists = presented ? p.presented.lists : p.lists || {};
    const text = (t) => (presented ? esc(t) : tmplHtml(t));
    const seg = `<span class="viewseg" role="group" aria-label="Question view">
      <button data-qview="presented" aria-pressed="${!!presented}" ${p.presented ? "" : "disabled"}>As presented</button><button data-qview="written" aria-pressed="${!presented}">As written</button></span>`;
    const note = presented
      ? "References resolved against the session state at the pause, as the answerer was shown them."
      : p.presented_error
        ? `The question as presented cannot be shown: ${esc(p.presented_error)}`
        : p.presented ? "The template text of the definition; the values are under Parameters." : "Written without values, so the question is shown as the definition writes it.";
    return `<section class="pending" id="pending"><h2>Paused: waiting for an answer at <a href="#${nodeA(p.node_id)}">${esc(p.node_id)}</a></h2>
      <div class="grid">
        <div><div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:6px"><span class="label">Presentation</span>${seg}</div>
          <dl class="kv">${["title", "description", "instruction", "goal", "context"].filter((k) => fields[k]).map((k) => `<dt>${k}</dt><dd><div class="tmpl">${text(fields[k])}</div></dd>`).join("")}</dl>
          <p class="hint" style="margin:6px 0 0">${note}</p></div>
        <div style="display:grid;gap:10px;align-content:start">
          ${Object.entries(lists).map(([k, items]) => `<div><span class="label">${esc(k)}</span><div class="mix" style="margin-top:3px">${items.map((o) => `<code class="g">${text(o)}</code>`).join("")}</div></div>`).join("")}
          <div><span class="label">Answer fields</span><dl class="kv">${p.answer.map((a) => `<dt><code>${esc(a.name)}</code>${a.required ? " *" : ""}</dt><dd>${esc(a.description || "")}${a.type ? ` <span class="tag">${esc(a.type)}</span>` : ""}</dd>`).join("")}</dl></div>
          <div><span class="label">Error catalogue</span><dl class="kv">${Object.entries(p.errors).map(([k, v]) => `<dt><code class="err">${esc(k)}</code></dt><dd>${esc(v)}</dd>`).join("")}<dt><code class="err">${esc(p.generic_error_code)}</code></dt><dd class="hint">any other failure of the answer</dd></dl></div>
        </div></div>
      <div><span class="label">Continue the session</span>${copy}</div></section>`;
  }

  const state = { filter: { node: "", failed: false }, openLoops: new Set(), openPasses: new Set(), view: "diagram", tab: "graph", question: "presented" };
  const TABS = ["graph", "path", "parameters", "artifacts", "journal"];
  function tabFor(id) {
    if (TABS.includes(id)) return id;
    if (id.startsWith("visit-")) return "path";
    if (id.startsWith("param-")) return "parameters";
    return null;
  }

  function render() {
    const m = MODEL;
    const s = m.session;
    document.title = `${s.flow_id} · ${s.status}`;
    const nodeIds = [...new Set(m.path.map((r) => r.node_id))];
    app.innerHTML = `
      <header class="run"><div class="wrap">
        <div class="title-row"><h1>${esc(s.flow_id)}</h1><span class="pill s-${esc(s.status)}">${esc(s.status)}</span><span class="sid">session ${esc(s.id)}</span></div>
        <div class="ending">${endingText(m)}</div>
        <div class="facts">
          <div><span class="label">Started</span><span class="v">${esc(s.started_at.slice(0, 19).replace("T", " "))} UTC</span></div>
          <div><span class="label">Last event</span><span class="v">+${ms(s.started_at, s.last_event_at)} ms</span></div>
          <div><span class="label">Node visits</span><span class="v">${s.nodes_visited}${s.max_nodes_visited ? ` of ${s.max_nodes_visited}` : ""}</span></div>
          <div><span class="label">Nodes</span><span class="v">${nodeIds.length} of ${m.definition.nodes.length} visited</span></div>
          <div><span class="label">Deliverables</span><span class="v">${m.definition.deliverables.length ? m.definition.deliverables.map((d) => esc(d)).join(", ") : "none declared"}</span></div>
        </div>
        ${inputsHtml(m)}
        ${unbuiltHtml(m)}
      </div></header>
      <nav class="sections" aria-label="Report"><div class="wrap" role="tablist">
        ${[["graph", "Graph", m.definition.nodes.length], ["path", "Path", m.path.length], ["parameters", "Parameters", m.parameters.length], ["artifacts", "Artifacts", m.artifacts.length], ["journal", "Journal", m.journal.length]]
          .map(([id, name, n]) => `<a href="#${id}" role="tab" id="tab-${id}" aria-controls="${id}" aria-selected="${state.tab === id}" tabindex="${state.tab === id ? 0 : -1}">${name}<span class="n">${n}</span></a>`).join("")}
      </div></nav>
      <main><div class="wrap">
        ${pendingHtml(m)}
        <section id="path" role="tabpanel" aria-labelledby="tab-path" ${state.tab === "path" ? "" : "hidden"}><div class="sec-head"><h2>Path</h2><p>One row per concluded node visit, in order. Loops fold into passes.</p></div>
          <div class="tools">
            <select id="f-node" aria-label="Only visits of node"><option value="">All nodes</option>${nodeIds.map((n) => `<option ${state.filter.node === n ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
            <label class="chk"><input type="checkbox" id="f-failed" ${state.filter.failed ? "checked" : ""}> failed visits only</label>
            <button class="btn" id="b-expand">Expand all</button><button class="btn" id="b-collapse">Collapse all</button>
            ${highlight ? `<span class="hint">Highlighting <strong class="mono">${esc(highlight)}</strong> · <kbd>Esc</kbd> clears</span>` : '<span class="hint">Click a node to open it; highlight its visits from there · <kbd>/</kbd> node filter · <kbd>[</kbd> <kbd>]</kbd> previous / next highlighted visit</span>'}
          </div>
          <div class="path" id="path-list">${m.path.length ? pathHtml(m, state.filter) : '<p class="hint" style="padding:12px;margin:0">No node concluded a visit.</p>'}</div>
        </section>
        <section id="graph" role="tabpanel" aria-labelledby="tab-graph" ${state.tab === "graph" ? "" : "hidden"}><div class="sec-head"><h2>Graph</h2><p>The definition the session runs. Each node opens as written and as built.</p></div>${nodesHtml(m)}</section>
        <section id="parameters" role="tabpanel" aria-labelledby="tab-parameters" ${state.tab === "parameters" ? "" : "hidden"}><div class="sec-head"><h2>Parameters</h2><p>Values rendered by the engine's text rule.</p></div>${paramsHtml(m)}</section>
        <section id="artifacts" role="tabpanel" aria-labelledby="tab-artifacts" ${state.tab === "artifacts" ? "" : "hidden"}><div class="sec-head"><h2>Artifacts</h2><p>Paths relative to the session directory; contents are not included.</p></div>${artifactsHtml(m)}</section>
        <section id="journal" role="tabpanel" aria-labelledby="tab-journal" ${state.tab === "journal" ? "" : "hidden"}><div class="sec-head"><h2>Journal</h2><p>Session events, operator and engine.</p></div>${journalHtml(m)}</section>
      </div></main>
      <footer class="foot"><div class="wrap"><span>workflow-engine report · model ${esc(m.schema_version)}</span><span>written ${esc(m.generated_at.slice(0, 16).replace("T", " "))} UTC</span><span>values ${m.options.values ? `on, cut at ${m.options.value_cut}` : "off"}</span>${m.options.home_replaced ? "<span>the home directory of the machine that wrote the report is shown as <code>~</code> in the values</span>" : ""}</div></footer>`;
  }

  function goHash() {
    const id = location.hash.slice(1);
    if (!id) return;
    if (id.startsWith("node-")) { openNode(id); return; }
    if (TABS.includes(id)) return;
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ block: "center" });
  }

  function setHighlight(n) { highlight = highlight === n ? null : n; render(); }

  app.addEventListener("click", (ev) => {
    const t = ev.target.closest("[data-hl],[data-loop],[data-pass],[data-copy],[data-view],[data-qview],#b-expand,#b-collapse");
    if (!t) return;
    if (t.dataset.view) { state.view = t.dataset.view; render(); return; }
    if (t.dataset.qview) { state.question = t.dataset.qview; render(); return; }
    if (t.dataset.hl !== undefined && t.tagName === "BUTTON") { setHighlight(t.dataset.hl); return; }
    if (t.dataset.hl !== undefined && t.closest(".visit")) { ev.preventDefault(); setHighlight(t.dataset.hl); return; }
    if (t.dataset.loop) { const k = t.dataset.loop; state.openLoops.has(k) ? state.openLoops.delete(k) : state.openLoops.add(k); render(); return; }
    if (t.dataset.pass) { const k = t.dataset.pass; state.openPasses.has(k) ? state.openPasses.delete(k) : state.openPasses.add(k); render(); return; }
    if (t.id === "b-expand") { const m = MODEL; segment(m.path).filter((s) => s.type === "loop").forEach((s) => { state.openLoops.add(s.head); s.passes.forEach((_, k) => state.openPasses.add(`${s.head}:${k}`)); }); render(); return; }
    if (t.id === "b-collapse") { state.openLoops.clear(); state.openPasses.clear(); render(); return; }
    if (t.dataset.copy !== undefined) {
      const text = t.previousElementSibling.textContent;
      const done = () => { t.textContent = "Copied"; setTimeout(() => (t.textContent = "Copy"), 1400); };
      navigator.clipboard?.writeText(text).then(done, () => { const r = document.createRange(); r.selectNodeContents(t.previousElementSibling); getSelection().removeAllRanges(); getSelection().addRange(r); });
    }
  });
  app.addEventListener("change", (ev) => {
    if (ev.target.id === "f-node") { state.filter.node = ev.target.value; render(); document.getElementById("f-node").focus(); }
    if (ev.target.id === "f-failed") { state.filter.failed = ev.target.checked; render(); document.getElementById("f-failed").focus(); }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.target.matches("input, select, textarea")) { if (ev.key === "Escape") ev.target.blur(); return; }
    if (ev.key === "Escape" && highlight) { highlight = null; render(); }
    if (ev.target.getAttribute && ev.target.getAttribute("role") === "tab" && (ev.key === "ArrowRight" || ev.key === "ArrowLeft")) {
      const i = TABS.indexOf(state.tab), j = (i + (ev.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length;
      location.hash = TABS[j]; setTimeout(() => document.getElementById("tab-" + TABS[j])?.focus(), 0); return;
    }
    if (ev.key === "/") { ev.preventDefault(); if (state.tab !== "path") { state.tab = "path"; history.replaceState(null, "", "#path"); render(); } document.getElementById("f-node")?.focus(); }
    if ((ev.key === "]" || ev.key === "[") && highlight) {
      const m = MODEL;
      state.tab = "path";
      segment(m.path).filter((s) => s.type === "loop").forEach((s) => { state.openLoops.add(s.head); s.passes.forEach((p, k) => { if (p.some(([r]) => r.node_id === highlight)) state.openPasses.add(`${s.head}:${k}`); }); });
      render();
      const rows = [...document.querySelectorAll(`.visit[data-node="${CSS.escape(highlight)}"]`)];
      const y = window.scrollY + 120;
      const next = ev.key === "]" ? rows.find((r) => r.getBoundingClientRect().top + window.scrollY > y + 4) : rows.reverse().find((r) => r.getBoundingClientRect().top + window.scrollY < y - 4);
      (next || rows[0])?.scrollIntoView({ block: "start" });
      if (next) history.replaceState(null, "", "#" + next.id);
    }
  });
  window.addEventListener("hashchange", () => {
    if (location.hash.startsWith("#node-")) { openNode(location.hash.slice(1)); return; }
    if (dlg.open) dlg.close();
    const t = tabFor(location.hash.slice(1));
    if (t) state.tab = t;
    render(); goHash();
  });

  { const t = tabFor(location.hash.slice(1)); if (t) state.tab = t; }
  render();
  goHash();
})();
