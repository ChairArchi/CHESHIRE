param([Parameter(Mandatory=$true)][string]$ArtifactRoot,
      [string[]]$Names = @('H1','H2','H3'), [string]$InputTag = 'initial', [string]$NamesCsv = '')
$ErrorActionPreference = 'Stop'
if ($NamesCsv) { $Names = $NamesCsv.Split(',') }
$task24RhinoSystem = 'C:\Program Files\Rhino 8\System'
$env:PATH = $task24RhinoSystem + ';' + $env:PATH
Add-Type -Path (Join-Path $task24RhinoSystem 'RhinoCommon.dll')
Add-Type -AssemblyName System.Web.Extensions
Add-Type -AssemblyName System.Drawing
$task24Core = $null
$task24StartupObservation = 'RhinoCore initialized with NoWindow'
try {
    $task24Core = New-Object Rhino.Runtime.InProcess.RhinoCore -ArgumentList @([string[]]@('/NOSPLASH','/NOTEMPLATE'),[Rhino.Runtime.InProcess.WindowStyle]::NoWindow)
} catch {
    # Some installed hosts return E_FAIL after native initialization. Do not
    # pretend the host initialized cleanly; subsequent real file IO must prove
    # whether the native target-format route is available independently.
    $task24StartupObservation = $_.Exception.ToString()
}
$task24Source = @'
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Rhino;
using Rhino.Geometry;
using Rhino.DocObjects;
using Rhino.FileIO;
public class HV { public int id; public double[] xyz; }
public class HF { public int id; public int[] vertices; }
public class HG { public HV[] vertices; public HF[] faces; }
public class HeroRhinoExchange {
 public static JavaScriptSerializer J=new JavaScriptSerializer { MaxJsonLength=Int32.MaxValue,RecursionLimit=100 };
 public static void Run(string root,string name,string input,string startup) {
  string output=Path.Combine(root,"dcc");Directory.CreateDirectory(output);
  HG g=J.Deserialize<HG>(File.ReadAllText(input));
  var mesh=new Mesh(); mesh.Vertices.UseDoublePrecisionVertices=true;
  var indices=new Dictionary<int,int>();
  foreach(HV v in g.vertices) indices[v.id]=mesh.Vertices.Add(v.xyz[0],v.xyz[1],v.xyz[2]);
  foreach(HF f in g.faces) {
   int[] q=f.vertices.Select(v=>indices[v]).ToArray();
   if(q.Length==4)mesh.Faces.AddFace(q[0],q[1],q[2],q[3]);
   else if(q.Length==3)mesh.Faces.AddFace(q[0],q[1],q[2]);
   else throw new Exception("Unsupported polygon; no implicit triangulation.");
  }
  mesh.Normals.ComputeNormals(); // Display normals only; XYZ/topology unchanged.
  if(!mesh.IsValid)throw new Exception("Rhino mesh invalid; exploration OBJ remains intact.");
  string target=Path.Combine(output,name+".3dm");Guid objectId;
  using(var model=new File3dm()) {
   model.Settings.ModelUnitSystem=UnitSystem.None;
   model.Settings.ModelAbsoluteTolerance=.001;
   model.ApplicationName="CHESHIRE Task24 / RhinoCommon 8 native exchange";
   model.Notes.Notes="Original source units are not present in the frozen input. No scaling applied. Z up; original origin. Original OBJ is the exploration master. Double precision coordinates; computed display normals only.";
   var layer=new Layer { Name="TASK24_"+name,Color=System.Drawing.Color.FromArgb(190,190,190) };
   int li=0;model.AllLayers.Add(layer);
   var attr=new ObjectAttributes { Name=name+"_DESIGN_FULL_RESOLUTION",LayerIndex=li };
   attr.SetUserString("Source",input);attr.SetUserString("GeometryProcessing","None; normals computed for display.");
   objectId=model.Objects.AddMesh(mesh,attr);
   if(!model.Write(target,8))throw new Exception("Native .3dm write failed.");
  }
  HG returned;bool same;string bounding;
  Console.WriteLine(name+" .3dm written; reading actual native file");
  using(var actual=File3dm.Read(target)) {
   if(actual==null || actual.Objects.Count!=1)throw new Exception("Actual exported .3dm reimport failed.");
   Console.WriteLine(name+" file read; extracting actual mesh");
   var importedObject=actual.Objects.FindId(objectId);
   if(importedObject==null)throw new Exception("Native file object identity not found: "+objectId);
   var r=importedObject.Geometry as Mesh;
   if(r==null || !r.IsValid)throw new Exception("Actual .3dm contains no valid Rhino mesh.");
   Console.WriteLine(name+" native mesh valid; checking "+r.Vertices.Count+" vertices");
   var vertices=new List<HV>();var faces=new List<HF>();
   for(int i=0;i<r.Vertices.Count;i++) { Point3d p=r.Vertices.Point3dAt(i);vertices.Add(new HV { id=i,xyz=new double[]{p.X,p.Y,p.Z} }); }
   for(int i=0;i<r.Faces.Count;i++) { var f=r.Faces[i];faces.Add(new HF { id=i,vertices=f.IsTriangle?new int[]{f.A,f.B,f.C}:new int[]{f.A,f.B,f.C,f.D} }); }
   returned=new HG { vertices=vertices.ToArray(),faces=faces.ToArray() };
   same=returned.vertices.Length==g.vertices.Length && returned.faces.Length==g.faces.Length;
   for(int i=0;same && i<g.vertices.Length;i++)same=g.vertices[i].xyz.SequenceEqual(returned.vertices[i].xyz);
   for(int i=0;same && i<g.faces.Length;i++)same=g.faces[i].vertices.Select(v=>indices[v]).SequenceEqual(returned.faces[i].vertices);
   if(!same)throw new Exception("Native .3dm reimport changed coordinates or oriented connectivity.");
   Console.WriteLine(name+" exact native reimport validated");
   bounding=r.GetBoundingBox(true).ToString();
   File.WriteAllText(Path.Combine(output,name+"_reimport.json"),J.Serialize(returned));
  }
  bool docOpen=false;int objects=0;
  using(var doc=RhinoDoc.OpenHeadless(target)) {
   docOpen=doc!=null;
   if(docOpen)objects=doc.Objects.Count;
  }
  var evidence=new { target=target,application="Installed RhinoCommon "+RhinoApp.Version,
   actual_native_file_read=true,exact_XYZ_oriented_faces=same,headless_RhinoDoc_open=docOpen,
   imported_document_objects=objects,object_id=objectId,layer="TASK24_"+name,
   vertices=g.vertices.Length,faces=g.faces.Length,units="None / original model units; no scaling",bounding_box=bounding,
   startup_observation=startup,viewport_capture="Not performed: NoWindow target-format route; geometry-based clay preview uses actual reimport.json.",
   processing="Computed normals only. No welding, triangulation, remeshing, smoothing or thickening." };
  File.WriteAllText(Path.Combine(output,name+"_import_evidence.json"),J.Serialize(evidence));
  Console.WriteLine(name+" native .3dm write/read exact; RhinoDoc open="+docOpen+" objects="+objects);
 }
}
'@
Add-Type -TypeDefinition $task24Source -ReferencedAssemblies (Join-Path $task24RhinoSystem 'RhinoCommon.dll'),'System.Web.Extensions','System.Drawing','System.Core'
try {
    foreach ($task24Name in $Names) {
        $task24Input = Join-Path $ArtifactRoot ('renders\'+$InputTag+'\'+$task24Name+'_front.json')
        try { [HeroRhinoExchange]::Run($ArtifactRoot,$task24Name,$task24Input,$task24StartupObservation) }
        catch { Write-Output $_.Exception.ToString(); throw }
    }
} finally { if ($task24Core) { $task24Core.Dispose() } }
