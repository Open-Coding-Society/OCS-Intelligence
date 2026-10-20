import sys, math
src=open(sys.argv[sys.argv.index("--")+1]).read(); outdir=sys.argv[sys.argv.index("--")+2]; which=sys.argv[sys.argv.index("--")+3]
src=src[:src.rstrip().rfind("main()")]
g={"__name__":"gen"}; exec(compile(src,"generate_rig_parts.py","exec"),g)
bpy=g["bpy"]; Vector=g["Vector"]
def scene_reset():
    bpy.ops.wm.read_factory_settings(use_empty=True); g["define_materials"]()
def shoot(builder, name, view, lens=50, dist=1.6, rot=0):
    scene_reset(); root,size=builder(); root.rotation_euler=(0,0,math.radians(rot))
    bpy.context.view_layer.update()
    import mathutils
    mn=mathutils.Vector((1e9,)*3); mx=-mn
    for o in [root]+list(root.children_recursive):
        if o.type=='MESH':
            for c in o.bound_box:
                w=o.matrix_world@mathutils.Vector(c); mn=mathutils.Vector(map(min,mn,w)); mx=mathutils.Vector(map(max,mx,w))
    ctr=(mn+mx)/2; s=(mx-mn).length
    cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam
    cam.data.lens=lens; cam.location=ctr+Vector(view).normalized()*s*dist
    cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
    for loc,e in (((1.2,-1.6,1.8),3.0),((-1.6,-1.0,1.2),1.2),((0,1.6,1.6),1.5)):
        L=bpy.data.objects.new("L",bpy.data.lights.new("L",'AREA')); L.data.energy=e*120*s*s; L.data.size=s
        L.location=ctr+Vector(loc)*s; L.rotation_euler=(ctr-L.location).to_track_quat('-Z','Y').to_euler(); bpy.context.collection.objects.link(L)
    w=bpy.data.worlds.new("W"); w.use_nodes=True; bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.6,0.62,0.66,1); bg.inputs[1].default_value=0.08; bpy.context.scene.world=w
    sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=96; sc.cycles.use_denoising=False
    sc.render.resolution_x=1200; sc.render.resolution_y=760; sc.render.filepath=f"{outdir}/{name}.png"
    bpy.ops.render.render(write_still=True); print("rendered",name)
V={"gpu_card":((0.9,-1.0,0.55),90),"psu":((0.9,-1.1,0.7),0),"motherboard":((0.5,-1.0,1.3),0)}
B={"gpu_card":"build_gpu_card","psu":"build_psu","motherboard":"build_motherboard"}
shoot(g[B[which]],which,V[which][0],rot=V[which][1])
