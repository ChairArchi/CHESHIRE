// Exact AABB candidate search only. Intersection predicates stay in Python.
// Self-contained .NET Framework console helper; no third-party code/packages.
using System;
using System.IO;
using System.Collections.Generic;

class Task36Bounds {
    struct Node { public double x0,y0,z0,x1,y1,z1; public int left,right,start,count; }
    static double[] bounds;
    static int[] vertices, ids;
    static bool includeShared=false;
    static List<Node> nodes=new List<Node>();
    const double Eps=1e-10;
    static double Centre(int id,int axis) { int k=6*id+axis; return (bounds[k]+bounds[k+3])*.5; }
    static void Select(int lo,int hi,int middle,int axis) {
        while(lo<hi) {
            int i=lo,j=hi; double pivot=Centre(ids[(lo+hi)/2],axis);
            while(i<=j) {
                while(Centre(ids[i],axis)<pivot)i++;
                while(Centre(ids[j],axis)>pivot)j--;
                if(i<=j) { int tmp=ids[i];ids[i++]=ids[j];ids[j--]=tmp; }
            }
            if(middle<=j)hi=j;else if(middle>=i)lo=i;else return;
        }
    }
    static int Build(int start,int count) {
        Node n=new Node();n.x0=n.y0=n.z0=Double.PositiveInfinity;n.x1=n.y1=n.z1=Double.NegativeInfinity;
        for(int j=start;j<start+count;j++) {
            int k=6*ids[j];n.x0=Math.Min(n.x0,bounds[k]);n.y0=Math.Min(n.y0,bounds[k+1]);n.z0=Math.Min(n.z0,bounds[k+2]);
            n.x1=Math.Max(n.x1,bounds[k+3]);n.y1=Math.Max(n.y1,bounds[k+4]);n.z1=Math.Max(n.z1,bounds[k+5]);
        }
        int index=nodes.Count;nodes.Add(n);
        if(count<=12) {n.left=-1;n.start=start;n.count=count;}
        else {
            double dx=n.x1-n.x0,dy=n.y1-n.y0,dz=n.z1-n.z0;int axis=dx>=dy&&dx>=dz?0:dy>=dz?1:2;int half=count/2;
            Select(start,start+count-1,start+half,axis);n.left=Build(start,half);n.right=Build(start+half,count-half);
        }
        nodes[index]=n;return index;
    }
    static bool Shared(int a,int b) {
        for(int i=0;i<3;i++)for(int j=0;j<3;j++)if(vertices[3*a+i]==vertices[3*b+j])return true;
        return false;
    }
    static bool Overlap(Node n,int k) {
        return n.x0<=bounds[k+3]+Eps&&bounds[k]<=n.x1+Eps&&n.y0<=bounds[k+4]+Eps&&bounds[k+1]<=n.y1+Eps&&n.z0<=bounds[k+5]+Eps&&bounds[k+2]<=n.z1+Eps;
    }
    static bool Pair(int a,int b) {
        for(int d=0;d<3;d++)if(Math.Min(bounds[6*a+3+d],bounds[6*b+3+d])+Eps<Math.Max(bounds[6*a+d],bounds[6*b+d]))return false;
        return includeShared||!Shared(a,b);
    }
    static void Main(string[] args) {
        includeShared=args.Length==2&&args[1]=="--include-shared";
        using(BinaryReader input=new BinaryReader(File.OpenRead(args[0]))) {
            int count=input.ReadInt32();bounds=new double[count*6];vertices=new int[count*3];ids=new int[count];
            byte[] data=input.ReadBytes(count*6*8);if(data.Length!=count*6*8)throw new EndOfStreamException();Buffer.BlockCopy(data,0,bounds,0,data.Length);
            data=input.ReadBytes(count*3*4);if(data.Length!=count*3*4)throw new EndOfStreamException();Buffer.BlockCopy(data,0,vertices,0,data.Length);for(int i=0;i<count;i++)ids[i]=i;
        }
        Build(0,ids.Length);int[] stack=new int[128];List<int> near=new List<int>();int[] batch=new int[16384];int used=0;
        using(BinaryWriter output=new BinaryWriter(new BufferedStream(Console.OpenStandardOutput(),1<<20))) {
            for(int a=0;a<ids.Length;a++) {
                near.Clear();int top=0;stack[top++]=0;
                while(top>0) {
                    Node n=nodes[stack[--top]];if(!Overlap(n,6*a))continue;
                    if(n.left<0) {for(int j=n.start;j<n.start+n.count;j++){int b=ids[j];if(b>a&&Pair(a,b))near.Add(b);}}
                    else {stack[top++]=n.left;stack[top++]=n.right;}
                }
                near.Sort();foreach(int b in near) {
                    batch[used++]=a;batch[used++]=b;
                    if(used==batch.Length){output.Write(used/2);for(int i=0;i<used;i++)output.Write(batch[i]);used=0;}
                }
            }
            if(used>0){output.Write(used/2);for(int i=0;i<used;i++)output.Write(batch[i]);}output.Write(0);
        }
    }
}
