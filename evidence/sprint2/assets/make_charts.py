import csv, json, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
S, A, VR = sys.argv[1:4]
BG="#191918"; PANEL="#1E1E1C"; GRID="#2E2E2C"; TX="#F4F0E8"; MU="#A8A6A0"; AC="#D97757"; CY="#5BD1FF"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":TX,"axes.labelcolor":MU,"xtick.color":MU,"ytick.color":MU,
  "axes.edgecolor":GRID,"axes.facecolor":PANEL,"figure.facecolor":BG,"svg.fonttype":"none"})
def title(fig,t,sub): fig.text(0.015,0.95,t,fontsize=13,fontweight="bold",color=TX,va="top"); fig.text(0.015,0.875,sub,fontsize=9.5,color=MU,va="top")

# 1 card load heatmap
rows=list(csv.DictReader(open(f"{S}/card-load.csv")))
t=[float(r["trace_ms"])/1000 for r in rows]; M=[[float(r[f"g{i}"]) for r in rows] for i in range(8)]
fig,ax=plt.subplots(figsize=(8,3.1)); fig.subplots_adjust(left=0.08,right=0.98,top=0.7,bottom=0.17)
cm=LinearSegmentedColormap.from_list("h",[PANEL,"#7a3f2c",AC,"#FFD2B8"])
ax.imshow(M,aspect="auto",cmap=cm,vmin=0,vmax=1,extent=[t[0],t[-1],7.5,-0.5],interpolation="nearest")
ax.set_yticks(range(8)); ax.set_yticklabels([f"GPU {i}" for i in range(8)],fontsize=8.5); ax.set_xlabel("playback time (s); network hops are slowed down so they can be followed")
title(fig,"Only the cards in the replica light up","Load of each card from RigCardDisplay, sampled every frame at 72 fps while sample-trace.json plays.\nGPUs 0-3 (the model replica) reach 1.0 while it generates. GPUs 4-7 stay at 0 throughout.")
fig.savefig(f"{A}/card-load.svg"); plt.close(fig)

# 2 hops
tr=json.load(open(f"{VR}/Assets/Data/sample-trace.json"))
H=[(h["node_id"]+"  "+h["hop"], h["t_end_ms"]-h["t_start_ms"], h.get("label","")) for h in tr["hops"]]
fig,ax=plt.subplots(figsize=(8,4.6)); fig.subplots_adjust(left=0.27,right=0.97,top=0.8,bottom=0.1)
y=range(len(H))[::-1]; col=[AC if "rig-2" in n else CY for n,_,_ in H]
ax.barh(list(y),[d for _,d,_ in H],color=col,height=0.62); ax.set_xscale("log")
ax.set_yticks(list(y)); ax.set_yticklabels([n for n,_,_ in H],fontsize=8.2)
for yy,(n,d,l) in zip(y,H): ax.text(d*1.12,yy,f"{d:,} ms",va="center",fontsize=8,color=TX)
ax.set_xlim(3,40000); ax.set_xlabel("duration, ms (log scale)"); ax.grid(axis="x",color=GRID,lw=0.6); ax.set_axisbelow(True)
title(fig,"Where the 10.02 s goes: the GPU takes 98.1%","Every hop in sample-trace.json, the hand-written trace the experience plays.\nOrange: on the rig. Blue: network and services. Total and share as the journey board reports them.")
fig.savefig(f"{A}/request-hops.svg"); plt.close(fig)

# 3 arc
acts=[("1 Empty bench",0,20),("2 Assembly",20,70.2),("3 Power on",70.2,85.2),("4 The request",85.2,124.2),("5 The answer",124.2,144.2)]
fig,ax=plt.subplots(figsize=(8,1.9)); fig.subplots_adjust(left=0.02,right=0.98,top=0.6,bottom=0.25)
cols=["#3a3a37","#4b6b7a",CY,AC,"#FFD2B8"]
for (n,a,b),c in zip(acts,cols):
    ax.barh(0,b-a,left=a,color=c,height=0.8); ax.text((a+b)/2,0,n,ha="center",va="center",fontsize=8.5,color=BG if c in (CY,AC,"#FFD2B8") else TX,fontweight="bold")
ax.set_xlim(0,150); ax.set_yticks([]); ax.set_xticks([0,20,70.2,85.2,124.2,144.2]); ax.set_xticklabels(["0","20","70.2","85.2","124.2","144.2 s"],fontsize=8)
for s in ax.spines.values(): s.set_visible(False)
title(fig,"The five-act arc runs 144 s, inside the 300 s budget","Act start times from FullArc, which plays the real .asset files at 72 fps (headless run, 2026-10-16).")
fig.savefig(f"{A}/arc-timeline.svg"); plt.close(fig)

# 4 commits
import subprocess, collections, datetime
d=subprocess.run(["git","-C",VR,"log","--format=%ad","--date=short"],capture_output=True,text=True).stdout.split()
c=collections.Counter(d); days=sorted(c)
start=datetime.date(2026,9,16); end=datetime.date(2026,10,12)
xs=[start+datetime.timedelta(i) for i in range((end-start).days+1)]
fig,ax=plt.subplots(figsize=(8,2.6)); fig.subplots_adjust(left=0.06,right=0.98,top=0.7,bottom=0.2)
ax.bar(xs,[c.get(x.isoformat(),0) for x in xs],color=AC,width=0.75)
for x in xs:
    v=c.get(x.isoformat(),0)
    if v: ax.text(x,v+0.3,str(v),ha="center",fontsize=8,color=TX)
ax.set_ylim(0,16); ax.grid(axis="y",color=GRID,lw=0.6); ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d")); ax.tick_params(axis="x",labelsize=8)
title(fig,f"{len(d)} commits, 2026-09-16 to 2026-10-12","Commits per day in VirtualLLMVisualizer, from git log.")
fig.savefig(f"{A}/commit-history.svg"); plt.close(fig)
print("ok")
