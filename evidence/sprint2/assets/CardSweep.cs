using System; using System.IO; using System.Reflection; using UnityEngine;
using OCS.VR.Telemetry; using OCS.VR.Rig;
public static class CardSweep {
  static void Call(object o,string m){var mi=o.GetType().GetMethod(m,BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic); if(mi!=null) mi.Invoke(o,null);}
  public static int Main(string[] a){
    var player=new TracePlayer{traceAsset=new TextAsset(File.ReadAllText(a[0])),playOnStart=true,timeScale=0.5f};
    var layout=new RigLayout{cardCount=8,cardSpacing=0.075f,firstCardOffset=new Vector3(-0.2625f,0.2155f,-0.045f),cardAxis=Vector3.right,tempMinC=35f,tempMaxC=85f};
    var cards=new Transform[8]; for(int i=0;i<8;i++) cards[i]=new Transform();
    var d=new RigCardDisplay{player=player,layout=layout,cards=cards,activeLift=0.02f,lerpSpeed=6f};
    Call(d,"Awake");Call(d,"OnEnable");Call(d,"Start");Call(player,"Start");
    Time.deltaTime=1f/72f; Console.WriteLine("frame,trace_ms,g0,g1,g2,g3,g4,g5,g6,g7");
    for(int f=0;f<72*120;f++){Call(player,"Update");Call(d,"Update");
      var s=f+","+player.ElapsedMs.ToString("F1"); for(int i=0;i<8;i++) s+=","+d.LoadOf(i).ToString("F3"); Console.WriteLine(s);
      if(!player.IsPlaying&&f>10) break;}
    return 0;}}
