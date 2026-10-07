param([Parameter(Mandatory=$true)][string]$ArtifactRoot,
      [Parameter(Mandatory=$true)][string]$ObjPath,
      [Parameter(Mandatory=$true)][string]$Name)
$ErrorActionPreference='Stop'
$task28System='C:\Program Files\Rhino 8\System'
$env:PATH=$task28System+';'+$env:PATH
Add-Type -Path (Join-Path $task28System 'RhinoCommon.dll')
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Web.Extensions
$task28Core=New-Object Rhino.Runtime.InProcess.RhinoCore -ArgumentList @([string[]]@('/NOSPLASH','/NOTEMPLATE'),[Rhino.Runtime.InProcess.WindowStyle]::NoWindow)
$task28Source=@'
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Web.Script.Serialization;
using Rhino;
using Rhino.Geometry;
using Rhino.DocObjects;
using Rhino.FileIO;
public class HansmeyerBenchmarkNative {
 public static string Hash(string path) { using(var s=File.OpenRead(path))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLower(); }
 public static void Run(string root,string obj,string name) {
  var clock=Stopwatch.StartNew();
  var mesh=new Mesh();mesh.Vertices.UseDoublePrecisionVertices=true;
  foreach(string line in File.ReadLines(obj)) {
   string[] s=line.Split(new char[]{' '},StringSplitOptions.RemoveEmptyEntries);
   if(s.Length==0)continue;
   if(s[0]=="v")mesh.Vertices.Add(double.Parse(s[1],CultureInfo.InvariantCulture),double.Parse(s[2],CultureInfo.InvariantCulture),double.Parse(s[3],CultureInfo.InvariantCulture));
   if(s[0]=="f") {
    int[] q=s.Skip(1).Select(v=>int.Parse(v)-1).ToArray();
    if(q.Length==4)mesh.Faces.AddFace(q[0],q[1],q[2],q[3]);
    else if(q.Length==3)mesh.Faces.AddFace(q[0],q[1],q[2]);
    else throw new Exception("No implicit polygon conversion.");
   }
  }
  mesh.Normals.ComputeNormals();if(!mesh.IsValid)throw new Exception("Native geometry invalid; no repair.");
  Directory.CreateDirectory(Path.Combine(root,"dcc"));string path=Path.Combine(root,"dcc",name+".3dm");Guid id;
  using(var model=new File3dm()) {
   model.Settings.ModelUnitSystem=UnitSystem.None;model.Settings.ModelAbsoluteTolerance=.001;
   model.ApplicationName="CHESHIRE Task28 / installed RhinoCommon";
   model.Notes.Notes="Original coordinates and unresolved units preserved; Z up. Actual column benchmark OBJ, computed display normals only. Stateful geometry/ancestry/origins live in the separate Task28 checkpoint.";
   model.AllLayers.Add(new Layer { Name="TASK28_"+name,Color=Color.FromArgb(205,205,205) });
   var attributes=new ObjectAttributes { Name=name+"_EXACT_SAVED_SUBDIVISION",LayerIndex=0 };
   attributes.SetUserString("OBJ",obj);attributes.SetUserString("OBJ_sha256",Hash(obj));
   attributes.SetUserString("GeometryChanges","None; normals computed for display.");
   id=model.Objects.AddMesh(mesh,attributes);
   if(!model.Write(path,8))throw new Exception("Native file write failed.");
  }
  Console.WriteLine("Written "+path+"; reading actual native geometry");Console.Out.Flush();
  using(var actual=File3dm.Read(path)) {
   if(actual==null || actual.Objects.Count!=1)throw new Exception("Native file unreadable.");
   var item=actual.Objects.FindId(id);var m=item==null?null:item.Geometry as Mesh;
   if(m==null || !m.IsValid || m.Vertices.Count!=mesh.Vertices.Count || m.Faces.Count!=mesh.Faces.Count)throw new Exception("Native file semantics changed.");
   for(int i=0;i<mesh.Vertices.Count;i++)if(mesh.Vertices.Point3dAt(i)!=m.Vertices.Point3dAt(i))throw new Exception("Native coordinates changed.");
   for(int i=0;i<mesh.Faces.Count;i++)if(mesh.Faces[i]!=m.Faces[i])throw new Exception("Native oriented faces changed.");
   // Analytical sections come from the actual reread file. They are wire
   // evidence of depth/concavity, not a new shaded renderer or volume repair.
   var planes=new Plane[]{new Plane(new Point3d(0,0,0),Vector3d.XAxis),new Plane(new Point3d(0,0,0),Vector3d.YAxis),new Plane(new Point3d(0,0,900),Vector3d.ZAxis)};
   string[] labels=new string[]{"X=0 / YZ","Y=0 / XZ","Z=900 / XY"};
   var rows=new List<object>();
   for(int i=0;i<planes.Length;i++) {
    var lines=Rhino.Geometry.Intersect.Intersection.MeshPlane(m,planes[i]);
    rows.Add(new { plane=labels[i],polylines=lines==null?new double[][][]{}:lines.Select(line=>line.Select(p=>new double[]{p.X,p.Y,p.Z}).ToArray()).ToArray() });
   }
   string sections=Path.Combine(root,"analysis","sections");Directory.CreateDirectory(sections);
   File.WriteAllText(Path.Combine(sections,name+".json"),new JavaScriptSerializer { MaxJsonLength=Int32.MaxValue }.Serialize(new { input=path,actual_native_file_read=true,units="Original unresolved model units",sections=rows }));
  }
  bool opened=false;int count=0;
  using(var doc=RhinoDoc.OpenHeadless(path)) { opened=doc!=null;if(opened)count=doc.Objects.Count; }
  if(!opened || count!=1)throw new Exception("Actual exported model failed headless document open.");
  var proof=new { application="RhinoCommon "+RhinoApp.Version,target=path,OBJ=obj,
   OBJ_sha256=Hash(obj),native_sha256=Hash(path),native_bytes=new FileInfo(path).Length,
   actual_native_file_read=true,exact_XYZ_oriented_faces=true,headless_document_open=opened,
   imported_objects=count,object_id=id,layer="TASK28_"+name,object_name=name+"_EXACT_SAVED_SUBDIVISION",
   vertices=mesh.Vertices.Count,faces=mesh.Faces.Count,units="None / original unknown physical units; no scaling",
   processing="Display normals only; no welding, triangulation, remeshing, smoothing, thickening or intersection repair.",
   native_read_write_document_seconds=clock.Elapsed.TotalSeconds,native_host_peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64,
   resource_scope="Native operation time excludes cold RhinoCore startup. Peak working set is this native PowerShell/RhinoCommon host, not a whole process-tree measurement.",
   display="Native file validation, not an interactive viewport or beauty render. OpenGL depth capture is separate; this evidence verifies native file and headless open only." };
  File.WriteAllText(Path.Combine(root,"dcc",name+"_import_evidence.json"),new JavaScriptSerializer().Serialize(proof));
  Console.WriteLine("Native exact reread and RhinoDoc.OpenHeadless PASS; "+mesh.Faces.Count+" faces");
  mesh.Dispose();
 }
}
'@
try {
 Add-Type -TypeDefinition $task28Source -ReferencedAssemblies (Join-Path $task28System 'RhinoCommon.dll'),'System.Drawing','System.Web.Extensions','System.Core'
 [HansmeyerBenchmarkNative]::Run($ArtifactRoot,$ObjPath,$Name)
} finally { $task28Core.Dispose() }
