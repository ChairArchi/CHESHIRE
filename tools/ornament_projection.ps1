param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Web.Extensions
# Task-local faster execution of the existing fixed headless polygon projection.
# No geometry smoothing, render assets, per-frame fitting or perspective changes.
$projectionSource = @'
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
public class CV { public int id; public double[] xyz; }
public class CF { public int id; public int[] vertices; }
public class CM { public CV[] vertices; public CF[] faces; }
public class Frame { public string mesh,file,label,camera,depthfile; public int width,height; public double[] bounds; public bool silhouette,wireframe; }
public class Sheet { public string file,title; public string[] images; public int width,height,columns; }
public class Plan { public Frame[] frames; public Sheet[] sheets; }
public class CapabilityProjection {
 static JavaScriptSerializer J = new JavaScriptSerializer { MaxJsonLength=Int32.MaxValue, RecursionLimit=100 };
 public static void Run(string path) {
  string dir=Path.GetDirectoryName(Path.GetFullPath(path)); Plan plan=J.Deserialize<Plan>(File.ReadAllText(path));
  foreach(Frame f in plan.frames) {
   string input=File.ReadAllText(Path.Combine(dir,f.mesh))+J.Serialize(f);
   if(!String.IsNullOrEmpty(f.depthfile)) input+=File.ReadAllText(Path.Combine(dir,f.depthfile));
   string signature; using(var hash=SHA256.Create()) signature=BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(input)));
   string target=Path.Combine(dir,f.file), stamp=target+".signature";
   if(File.Exists(target) && File.Exists(stamp) && File.ReadAllText(stamp)==signature) { Console.WriteLine("verified view cache: "+f.file); continue; }
   Paint(dir,f); File.WriteAllText(stamp,signature); Console.WriteLine(f.file);
  }
  foreach(Sheet s in plan.sheets) {
   int rows=(s.images.Length+s.columns-1)/s.columns;
   using(Bitmap b=new Bitmap(s.width*s.columns,s.height*rows+70)) using(Graphics g=Graphics.FromImage(b)) using(Font font=new Font("Arial",14)) using(Font small=new Font("Arial",10)) {
    g.Clear(Color.White); g.DrawString(s.title,font,Brushes.Black,12,8);
    g.DrawString("HEADLESS actual polygons / fixed camera, scale, light and registered crop",small,Brushes.Black,12,35);
    for(int i=0;i<s.images.Length;i++) using(Image image=Image.FromFile(Path.Combine(dir,s.images[i]))) g.DrawImageUnscaled(image,(i%s.columns)*s.width,(i/s.columns)*s.height+70);
    b.Save(Path.Combine(dir,s.file),ImageFormat.Png);
   } Console.WriteLine(s.file);
  }
 }
 static void Paint(string dir,Frame f) {
  CM mesh=J.Deserialize<CM>(File.ReadAllText(Path.Combine(dir,f.mesh)));
  var ornamentDepth=String.IsNullOrEmpty(f.depthfile)?null:J.Deserialize<Dictionary<string,int>>(File.ReadAllText(Path.Combine(dir,f.depthfile)));
  var xyz=new Dictionary<int,double[]>(); var screen=new Dictionary<int,PointF>(); var depth=new Dictionary<int,double>();
  double scale=Math.Min((f.width-50)/(f.bounds[1]-f.bounds[0]),(f.height-80)/(f.bounds[3]-f.bounds[2]));
  foreach(CV v in mesh.vertices) {
   double[] p=v.xyz; bool front=f.camera=="front";
   double u=front?p[0]:p[0]+.65*p[1], w=front?p[2]:p[2]+.30*p[1];
   xyz[v.id]=p; screen[v.id]=new PointF((float)(25+(u-f.bounds[0])*scale),(float)(55+(f.bounds[3]-w)*scale));
   depth[v.id]=front?-p[1]:.65*p[0]-p[1]+.30*p[2];
  }
  double[] order=new double[mesh.faces.Length]; int[] indices=new int[mesh.faces.Length];
  for(int i=0;i<indices.Length;i++) { indices[i]=i; foreach(int v in mesh.faces[i].vertices) order[i]+=depth[v]; order[i]/=mesh.faces[i].vertices.Length; }
  Array.Sort(order,indices);
  using(Bitmap bitmap=new Bitmap(f.width,f.height)) using(Graphics g=Graphics.FromImage(bitmap)) using(Font font=new Font("Arial",13)) using(Font small=new Font("Arial",9)) using(Pen pen=new Pen(Color.FromArgb(160,65,75,84),.65f)) {
   g.Clear(Color.White); g.SmoothingMode=SmoothingMode.AntiAlias;
   g.DrawString("HEADLESS / same camera, scale and gray light",small,Brushes.Black,12,8); g.DrawString(f.label,font,Brushes.Black,12,27);
   g.SetClip(new Rectangle(5,52,f.width-10,f.height-57)); var brushes=new Dictionary<int,SolidBrush>();
   try { foreach(int i in indices) {
    CF face=mesh.faces[i]; PointF[] polygon=new PointF[face.vertices.Length];
    for(int j=0;j<polygon.Length;j++) polygon[j]=screen[face.vertices[j]];
    double[] a=xyz[face.vertices[0]],b=xyz[face.vertices[1]],c=xyz[face.vertices[2]];
    double ax=b[0]-a[0],ay=b[1]-a[1],az=b[2]-a[2],bx=c[0]-a[0],by=c[1]-a[1],bz=c[2]-a[2];
    double nx=ay*bz-az*by,ny=az*bx-ax*bz,nz=ax*by-ay*bx,length=Math.Sqrt(nx*nx+ny*ny+nz*nz);
    int gray=f.silhouette?45:(length>0?(int)(130+100*Math.Abs((.3*nx-.8*ny+.5*nz)/length)):130); gray=Math.Max(0,Math.Min(255,gray));
    if(ornamentDepth!=null) { int d=ornamentDepth[face.id.ToString()]; Color[] palette={Color.FromArgb(160,166,174),Color.FromArgb(46,132,190),Color.FromArgb(230,146,32),Color.FromArgb(178,61,129)}; using(var brush=new SolidBrush(palette[Math.Min(d,3)])) g.FillPolygon(brush,polygon); }
    else if(f.wireframe) g.DrawPolygon(pen,polygon); else { if(!brushes.ContainsKey(gray)) brushes[gray]=new SolidBrush(Color.FromArgb(gray,gray,gray)); g.FillPolygon(brushes[gray],polygon); }
   }} finally { foreach(SolidBrush brush in brushes.Values) brush.Dispose(); }
   g.ResetClip(); if(ornamentDepth!=null) g.DrawString("DEPTH 0 gray / 1 blue / 2 orange / 3 purple; ancestry, not aesthetic score",small,Brushes.Black,12,f.height-18);
   bitmap.Save(Path.Combine(dir,f.file),ImageFormat.Png);
  }
 }
}
'@
Add-Type -TypeDefinition $projectionSource -ReferencedAssemblies 'System.Drawing','System.Web.Extensions'
[CapabilityProjection]::Run($PlanPath)
