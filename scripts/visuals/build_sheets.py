"""Render the two printable rig sheets (Letter, 0.5in margins) from one template."""
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "docs" / "visuals"

CSS = r"""
@page { size: Letter; margin: 0.5in; }
:root {
  --paper:#FFFFFF; --panel:#F8F4EE; --panel-2:#F1EAE0; --border:#E4DBCD; --rule:#D8CDBC;
  --ink:#1E1C19; --ink-2:#4F4B45; --muted:#8B867D;
  --accent:#D97757; --accent-ink:#B04F2C; --accent-tint:#FBEBE4;
  --blue:#3B67B5; --blue-tint:#E7EEFA;
  --violet:#6560C4; --violet-tint:#ECEBFA;
  --gold:#B8741C; --gold-tint:#FBF0DF;
  --green:#3C8656; --green-tint:#E6F3EA;
}
* { box-sizing: border-box; }
html, body { margin:0; background: var(--paper); color: var(--ink);
  font-family: "Ubuntu Sans", "Inter", "DejaVu Sans", sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
@media screen { body { padding: 0.5in; width: 8.5in; } }
.sheet { width: 7.5in; height: 10in; display: flex; flex-direction: column; overflow: hidden; }
.mono { font-family: "Ubuntu Sans Mono", "DejaVu Sans Mono", monospace; }

/* header */
header { display:flex; justify-content: space-between; align-items: flex-end;
  border-left: 4px solid var(--accent); padding: 2px 0 2px 14px; }
.kicker { font-size: 8.5pt; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--accent-ink); }
h1 { font-size: 34pt; line-height: 1; margin: 6px 0 6px; font-weight: 800; letter-spacing: -.02em; }
.sub { font-size: 11pt; color: var(--ink-2); }
.sub b { color: var(--ink); font-weight: 600; }
.chips { display:flex; flex-direction: column; gap: 5px; align-items: flex-end; }
.chip { font-size: 8pt; color: var(--ink-2); background: var(--panel); border: 1px solid var(--border);
  border-radius: 4px; padding: 3px 8px; white-space: nowrap; }
.chip b { font-size: 6.8pt; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin-right: 6px; font-weight: 700; }

/* stats */
.stats { display:grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 16px 0 14px; }
.stat { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px 8px; }
.stat .v { font-size: 22pt; font-weight: 800; letter-spacing: -.02em; line-height: 1.05; }
.stat .v small { font-size: 11pt; font-weight: 600; color: var(--ink-2); margin-left: 2px; }
.stat .l { font-size: 7.6pt; color: var(--muted); text-transform: uppercase; letter-spacing: .1em; font-weight: 700; margin-top: 2px; }

h2 { font-size: 11pt; margin: 0 0 8px; display:flex; align-items:center; gap: 8px; font-weight: 800; }
h2::before { content:""; width: 9px; height: 9px; background: var(--accent); display:inline-block; }
h2 .note { font-weight: 400; font-size: 8pt; color: var(--muted); margin-left: auto; }

/* GPU groups */
.groups { display:flex; gap: 12px; }
.group { flex: 1; border: 1.5px solid var(--c); background: var(--tint); border-radius: 10px; padding: 9px 10px 10px; }
.group-head { display:flex; align-items: baseline; gap: 8px; margin: 0 2px 8px; }
.group-head .name { font-weight: 800; font-size: 11pt; color: var(--c); }
.group-head .model { font-size: 9.5pt; font-weight: 700; }
.group-head .meta { margin-left:auto; font-size: 8pt; color: var(--ink-2); }
.tiles { display:grid; grid-template-columns: repeat(var(--cols), 1fr); gap: 8px; }
.tile { background: var(--paper); border: 1px solid var(--border); border-radius: 7px; overflow: hidden; position: relative; }
.tile .band { height: 5px; background: var(--c); }
.tile .body { padding: 6px 9px 7px; }
.tile .row1 { display:flex; align-items: baseline; justify-content: space-between; }
.tile .idx { font-size: 15pt; font-weight: 800; letter-spacing: -.01em; }
.tile .idx span { font-size: 8pt; color: var(--muted); font-weight: 700; margin-right: 2px; letter-spacing: .06em; }
.tile .vram { font-size: 9pt; font-weight: 800; color: var(--c); }
.tile .card { font-size: 9.5pt; font-weight: 700; margin-top: 1px; }
.tile .variant { font-size: 7.8pt; color: var(--ink-2); }
.tile .facts { display:flex; justify-content: space-between; font-size: 7.4pt; color: var(--muted); margin-top: 4px;
  border-top: 1px dashed var(--border); padding-top: 4px; }
.group.inline .card { display:inline; }
.group.inline .variant { display:inline; margin-left: 5px; }
.tile.special { border: 1.5px solid var(--gold); }
.tile.special .band { background: var(--gold); }
.tile.special .vram { color: var(--gold); }
.tile .flag { position:absolute; top: 9px; right: 8px; }

/* bus */
.bus { margin-top: 10px; display:flex; align-items:center; gap: 10px; background: var(--panel-2);
  border: 1px solid var(--border); border-radius: 7px; padding: 7px 12px; font-size: 8.4pt; color: var(--ink-2); }
.bus b { color: var(--ink); }
.bus .pill { margin-left:auto; font-size: 7.6pt; font-weight: 700; color: var(--accent-ink); background: var(--accent-tint);
  border-radius: 999px; padding: 2px 8px; white-space: nowrap; }

/* lower */
.lower { display:grid; grid-template-columns: 1.15fr 1fr; gap: 16px; margin-top: 16px; flex: 1; min-height: 0; }
dl { margin: 0; display:grid; grid-template-columns: 1.05in 1fr; border-top: 1px solid var(--border); }
dt, dd { margin:0; padding: 5.5px 0; border-bottom: 1px solid var(--border); font-size: 8.6pt; line-height: 1.3; }
dt { color: var(--muted); font-weight: 700; font-size: 7.4pt; text-transform: uppercase; letter-spacing: .08em; padding-top: 7px; }
dd b { font-weight: 700; }
dd .dim { color: var(--muted); font-size: 7.8pt; }
.psu { display:flex; align-items:center; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border); }
.psu:first-of-type { border-top: 1px solid var(--border); }
.psu .w { width: 0.95in; }
.psu .w b { display:block; font-size: 10.5pt; font-weight: 800; }
.psu .w span { font-size: 7.6pt; color: var(--muted); }
.slots { display:flex; gap: 3px; flex-wrap: wrap; align-items:center; }
.slot { width: 15px; height: 21px; border-radius: 3px; background: var(--green-tint); border: 1.5px solid var(--green); }
.slot.ti { border-color: var(--gold); background: var(--gold-tint); }
.slot.mb { width: auto; height: 21px; padding: 0 6px; font-size: 7pt; font-weight: 700; color: var(--ink-2);
  background: var(--panel-2); border: 1.5px solid var(--rule); display:flex; align-items:center; }
.psu .cnt { margin-left:auto; font-size: 8pt; color: var(--ink-2); white-space: nowrap; }
.svc { display:grid; grid-template-columns: auto 1fr auto; column-gap: 8px; align-items: baseline;
  padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 8.6pt; }
.svc:first-of-type { border-top: 1px solid var(--border); }
.svc .port { font-weight: 700; color: var(--accent-ink); font-size: 8.4pt; min-width: 0.5in; }
.svc .what b { font-weight: 700; }
.svc .what span { color: var(--muted); font-size: 7.8pt; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); display:inline-block; }
.dot.off { background: transparent; border: 1.5px solid var(--muted); }
.small { font-size: 7.4pt; color: var(--muted); margin-top: 5px; line-height: 1.35; }
.col > section + section { margin-top: 14px; }

footer { margin-top: 12px; padding-top: 7px; border-top: 1px solid var(--rule); display:flex; justify-content: space-between;
  font-size: 7.4pt; color: var(--muted); }
footer b { color: var(--accent-ink); }
"""

def tile(g, special=False):
    return f"""
    <div class="tile{' special' if special else ''}">
      <div class="band"></div>
      <div class="body">
        <div class="row1"><div class="idx"><span>GPU</span>{g['i']}</div><div class="vram">{g['vram']}</div></div>
        <div class="card">{g['card']}</div>
        <div class="variant">{g['variant']}</div>
        <div class="facts mono"><span>bus {g['bus']}</span><span>{g['uuid']}</span></div>
      </div>
    </div>"""

def group(name, model, meta, color, tint, cols, gpus, cls=""):
    tiles = "".join(tile(g, g.get('special', False)) for g in gpus)
    return f"""
    <div class="group {cls}" style="--c:var({color}); --tint:var({tint}); --cols:{cols}">
      <div class="group-head"><span class="name">{name}</span><span class="model mono">{model}</span><span class="meta">{meta}</span></div>
      <div class="tiles">{tiles}</div>
    </div>"""

def psu(watts, label, slots, count):
    cells = "".join(f'<span class="slot{" ti" if s == "ti" else ""}{" mb" if s == "mb" else ""}">{"board + CPU" if s == "mb" else ""}</span>' for s in slots)
    return f'<div class="psu"><div class="w"><b>{watts}</b><span>{label}</span></div><div class="slots">{cells}</div><div class="cnt">{count}</div></div>'

def svc(port, what, sub, on=True):
    return f'<div class="svc"><span class="port mono">{port}</span><span class="what"><b>{what}</b> <span>{sub}</span></span><span class="dot{"" if on else " off"}"></span></div>'

def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><div class="sheet">{body}</div></body></html>"""

E1070 = dict(card="GTX 1070", variant="EVGA FTW Hybrid · 185 W", vram="8 GB")

def g1070(i, bus, uuid):
    return dict(E1070, i=i, bus=bus, uuid=uuid)

COMMON_PLATFORM = """
  <dt>Board</dt><dd><b>ASUS B250 Mining Expert</b> <span class="dim">· BIOS {bios}</span></dd>
  <dt>CPU</dt><dd><b>Intel Celeron G3930</b> <span class="dim">· 2 cores · 2.9 GHz</span></dd>
  <dt>Memory</dt><dd>{ram}</dd>
  <dt>Storage</dt><dd><b>Samsung 860 EVO 250 GB</b> {ssd}<br><span class="dim">{ssd_note}</span></dd>
  <dt>Network</dt><dd><b>Wired Ethernet</b> <span class="dim">· onboard Intel I219-V · NetBird overlay</span></dd>
  <dt>OS</dt><dd><b>{os}</b> <span class="dim">· kernel 7.0.0-38</span></dd>
  <dt>GPU stack</dt><dd><b>NVIDIA 580.178.04</b> (DKMS) <span class="dim">· CUDA 12.6 · Pascal sm_61</span></dd>
  <dt>Inference</dt><dd><b>llama.cpp</b> <span class="dim">llama-server · layer split across cards</span></dd>
"""

def header(rig, host, role, ip):
    return f"""
<header>
  <div>
    <div class="kicker">OCS Intelligence · Hardware</div>
    <h1>{rig}</h1>
    <div class="sub"><b class="mono">{host}</b> · {role}</div>
  </div>
  <div class="chips">
    <span class="chip"><b>NetBird</b><span class="mono">{ip}</span></span>
    <span class="chip"><b>Endpoint</b><span class="mono">ai.opencodingsociety.com</span></span>
    <span class="chip"><b>As of</b>2026-10-20</span>
  </div>
</header>"""

def stats(items):
    return '<div class="stats">' + "".join(f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in items) + "</div>"

FOOT = """<footer><span>Verified over NetBird SSH 2026-10-20 (<span class="mono">nvidia-smi</span>, <span class="mono">dmidecode</span>, <span class="mono">lsblk</span>). Power supplies are team-reported.</span><span>Source of truth: <b class="mono">docs/architecture/hardware.md</b></span></footer>"""

# ---------- Rig 1 ----------
r1_a = [g1070(1, "07:00.0", "GPU-728d79b7"), g1070(3, "0B:00.0", "GPU-71f15481"),
        g1070(5, "0D:00.0", "GPU-fb4eb983"), g1070(7, "0F:00.0", "GPU-24899ea8")]
r1_b = [g1070(0, "03:00.0", "GPU-a25606af"), g1070(2, "0A:00.0", "GPU-4de8c392"),
        g1070(4, "0C:00.0", "GPU-2a70bbf9"), g1070(6, "0E:00.0", "GPU-bc07dc85")]
rig1 = header("Rig 1", "ocs-intelligence-rig", "Production inference for the public API", "100.75.123.203") + stats([
    ("8", "GPUs · GTX 1070"), ("64<small>GB</small>", "Total VRAM"), ("1,480<small>W</small>", "Max GPU power"), ("16<small>GB</small>", "System RAM")
]) + f"""
<section>
  <h2>GPUs, by worker <span class="note">Numbered by nvidia-smi index, not physical position. Workers pin cards by UUID.</span></h2>
  <div class="groups">
    {group("Worker A", "qwen3.8:27b", "port 8081 · 4 cards", "--accent", "--accent-tint", 2, r1_a)}
    {group("Worker B", "gemma4:26b", "port 8082 · 4 cards", "--blue", "--blue-tint", 2, r1_b)}
  </div>
  <div class="bus"><span>Every card reaches the board over a <b>PCIe Gen1 ×1 riser</b> (~250 MB/s). Cards in a worker pass activations to each other over these links.</span><span class="pill">No NVLink</span></div>
</section>
<div class="lower">
  <div class="col"><section><h2>Platform</h2><dl>
  {COMMON_PLATFORM.format(bios="0403", ram='<b>16 GB DDR4</b> <span class="dim">· 2 × 8 GB Corsair Vengeance LPX · 2133 MT/s</span>',
    ssd="", ssd_note="Boot + models. A second SSD (480 GB) is installed but not detected by the OS.", os="Ubuntu 24.04.4 LTS")}
  </dl></section></div>
  <div class="col">
    <section><h2>Power</h2>
      {psu("1800 W", "brand unknown", ["mb"] + ["g"] * 5, "5 GPUs")}
      {psu("1300 W", "Antec", ["g"] * 3, "3 GPUs")}
      <div class="small">Team-reported. Which card is on which supply isn't recorded. Each 1070 is limited to 185 W.</div>
    </section>
    <section><h2>Services</h2>
      {svc(":9000", "Orchestrator", "routes by model, reached from EC2 over NetBird")}
      {svc(":8081", "Worker A", "llama-server, localhost only")}
      {svc(":8082", "Worker B", "llama-server, localhost only")}
      {svc(":3000", "Open WebUI", "Docker, the chat site at /")}
      {svc("—", "Ollama", "stopped, kept as fallback", on=False)}
    </section>
  </div>
</div>
""" + FOOT

# ---------- Rig 2 ----------
r2 = [dict(i=0, card="GTX 1080 Ti", variant="EVGA SC Black · air · 250 W", vram="11 GB", bus="01:00.0", uuid="GPU-51bb095a", special=True),
      g1070(1, "04:00.0", "GPU-83daccf4"), g1070(2, "08:00.0", "GPU-5564a0bd"),
      g1070(3, "0B:00.0", "GPU-8e7ca25c"), g1070(4, "0C:00.0", "GPU-ee8e7563"),
      g1070(5, "0D:00.0", "GPU-69f0a712"), g1070(6, "0E:00.0", "GPU-2b6607e6"),
      g1070(7, "0F:00.0", "GPU-64ccc864"), g1070(8, "10:00.0", "GPU-a512d941")]
rig2 = header("Rig 2", "ocs-intelligence-rig2", "Development and test · serves Open WebUI", "100.75.127.192") + stats([
    ("9", "GPUs · 1080 Ti + 8 × 1070"), ("75<small>GB</small>", "Total VRAM"), ("1,730<small>W</small>", "Max GPU power"), ("8<small>GB</small>", "System RAM · 1 stick")
]) + f"""
<section>
  <h2>GPUs <span class="note">Numbered by nvidia-smi index, not physical position. GPU 3 was added 2026-10-19.</span></h2>
  <div class="groups">
    {group("One worker", "qwen3.6:35b-a3b", "port 8081 · all 9 cards · split 11:8:8:8:8:8:8:8:8", "--violet", "--violet-tint", 3, r2, "inline")}
  </div>
  <div class="bus"><span>Every card reaches the board over a <b>PCIe Gen1 ×1 riser</b> (~250 MB/s). The MoE model runs ~27.7 tok/s, 2 slots of 262k context.</span><span class="pill">No NVLink</span></div>
</section>
<div class="lower">
  <div class="col"><section><h2>Platform</h2><dl>
  {COMMON_PLATFORM.format(bios="1001 (reflashed)", ram='<b>8 GB DDR4</b> <span class="dim">· 1 × 8 GB Corsair Vengeance LPX · 2133 MT/s. With 2 sticks the board won\'t POST</span>',
    ssd="<span class=\"dim\">(M.2 SATA)</span>", ssd_note="Boot + model. A second 256 GB SSD is installed but not detected by the OS.", os="Ubuntu 24.04.3 LTS")}
  </dl></section></div>
  <div class="col">
    <section><h2>Power</h2>
      {psu("1800 W", "brand unknown", ["mb"] + ["g"] * 5, "5 GPUs")}
      {psu("850 W", "EVGA", ["g"] * 2, "2 GPUs")}
      {psu("1300 W", "Antec", ["g"] * 2, "2 GPUs")}
      <div class="small">Team-reported. The 9th card is believed to be on the Antec. Which card is on which supply isn't recorded.</div>
    </section>
    <section><h2>Services</h2>
      {svc(":9000", "Orchestrator", "one model, reached from Open WebUI over NetBird")}
      {svc(":8081", "Worker", "llama-server, localhost only")}
      {svc("—", "Ollama", "disabled (was only used to pull models)", on=False)}
    </section>
  </div>
</div>
""" + FOOT

(OUT / "rig1.html").write_text(page("Rig 1 Hardware", rig1))
(OUT / "rig2.html").write_text(page("Rig 2 Hardware", rig2))
print("ok")
