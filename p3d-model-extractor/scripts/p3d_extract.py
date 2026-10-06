#!/usr/bin/env python
"""Extract a p3d.in share model into standard glTF and Blender."""
from __future__ import annotations
import argparse, json, os, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"

def get(url: str, referer: str | None = None) -> bytes:
    h = {"User-Agent": UA}
    if referer: h["Referer"] = referer
    req = Request(url, headers=h)
    with urlopen(req, timeout=90) as r:
        return r.read()

def short_id(url: str) -> str:
    parts = [x for x in urlparse(url).path.split('/') if x]
    if not parts: raise ValueError('URL has no p3d.in model id')
    # /<shortid>/spin, /e/<shortid>, and bare /<shortid>
    if parts[0] == 'e' and len(parts) > 1: return parts[1]
    return parts[0]

def write_json(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf-8')

def find_blender():
    for exe in ['blender', 'blender.exe']:
        p = shutil.which(exe)
        if p: return p
    roots = [r'C:\Program Files\Blender Foundation']
    for root in roots:
        if os.path.isdir(root):
            choices = sorted(Path(root).glob('Blender*/blender.exe'), reverse=True)
            if choices: return str(choices[0])
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--output','-o', type=Path)
    ap.add_argument('--no-blender', action='store_true')
    ap.add_argument('--keep-work', action='store_true')
    args=ap.parse_args()
    sid=short_id(args.url); ref=f'https://p3d.in/{sid}/spin'
    out=args.output or Path.cwd()/f'p3d-{sid}'
    out=out.resolve(); out.mkdir(parents=True,exist_ok=True)
    texdir=out/'textures'; texdir.mkdir(exist_ok=True)
    work=out/'work'; work.mkdir(exist_ok=True)
    print('Fetching API...')
    api=json.loads(get(f'https://p3d.in/api/viewer_models/{sid}?type=editor&cdn=true&webp=true',ref))
    write_json(out/'api.json',api)
    vm=api['viewer_model']; source_url=vm['base_url']
    payload=get(source_url,ref); (out/'source-model.bin').write_bytes(payload)
    if payload[:4] != b'P3D ' and payload[:3] != b'P3D': print('Warning: unexpected P3D header',payload[:8])
    json_len=struct.unpack_from('<I',payload,12)[0]
    if payload[16:20] != b'JSON': raise RuntimeError('P3D JSON marker missing')
    model=json.loads(payload[20:20+json_len].rstrip(b' \t\r\n\0'))
    write_json(out/'source-model.json',model)
    bin_start=20+json_len+8; original=payload[bin_start:bin_start+model['buffers'][0]['byteLength']]
    tex_by_id={int(t['id']):t for t in api.get('textures',[])}
    assignments={int(t['id']):t for t in api.get('texture_assignments',[])}
    material_api=api.get('materials',[{}])[0]
    settings=json.loads(material_api.get('settings','{}') or '{}')
    id_to_file={}
    for tid,t in tex_by_id.items():
        url=t.get('url')
        if not url: continue
        name=Path(urlparse(url).path).name or f'texture-{tid}.webp'
        path=texdir/name
        if not path.exists():
            print('Downloading texture',tid,name); path.write_bytes(get(url,ref))
        id_to_file[tid]=str(Path('textures')/name).replace('\\','/')
    # Fetch the decoder worker's current decoder filename from the share page.
    html=get(ref,ref).decode('utf-8','replace')
    m=re.search(r'"dracoDecoder"\s*:\s*"([^"]+)"',html)
    decoder_name = m.group(1) if m else None
    if not decoder_name:
        m2=re.search(r'draco-decoder-[a-f0-9]+\.js',html)
        decoder_name = '/assets/'+m2.group(0) if m2 else None
    decoder_url=urljoin('https://p3d.in/',decoder_name) if decoder_name else ''
    if not decoder_url: decoder_url='https://p3d.in/assets/draco-decoder-5fcad04db3893d9fbb79418b1f8e44a1.js'
    decoder_path=work/'draco-decoder.js'; decoder_path.write_bytes(get(decoder_url,ref))
    decode_js=work/'decode.js'
    decode_js.write_text(r'''const fs=require('fs');
(async()=>{
 const base=process.argv[2], input=fs.readFileSync(base+'/source-model.bin'), j=JSON.parse(fs.readFileSync(base+'/source-model.json'));
 const D=require('./draco-decoder.js'); const d=await D({}); await d.ready; const start=20+Number(new DataView(input.buffer,input.byteOffset+12,4).getUint32(0,true))+8;
 const out=[];
 for(let mi=0;mi<j.meshes.length;mi++){
  const decodedMesh=[];
  for(let pi=0;pi<j.meshes[mi].primitives.length;pi++){
   const p=j.meshes[mi].primitives[pi];
   if(p.extensions && p.extensions.KHR_draco_mesh_compression){
    const ex=p.extensions.KHR_draco_mesh_compression, v=j.bufferViews[ex.bufferView];
    const raw=input.subarray(start+v.byteOffset,start+v.byteOffset+v.byteLength), db=new d.DecoderBuffer(); db.Init(new Int8Array(raw),raw.length);
    const dec=new d.Decoder(), mesh=new d.Mesh(), st=dec.DecodeBufferToMesh(db,mesh); if(mesh.num_points()===0||mesh.num_faces()===0) throw Error('empty mesh '+mi+' primitive '+pi);
    const attrs={}; for(const [name,id] of Object.entries(ex.attributes)){const a=dec.GetAttributeByUniqueId(mesh,id), n=a.num_components()*mesh.num_points(), ar=new d.DracoFloat32Array(); dec.GetAttributeFloatForAllPoints(mesh,a,ar); attrs[name]=Array.from({length:n},(_,i)=>ar.GetValue(i)); d.destroy(ar)}
    const ia=new d.DracoInt32Array(), indices=[]; for(let f=0;f<mesh.num_faces();f++){dec.GetFaceFromMesh(mesh,f,ia); indices.push(ia.GetValue(0),ia.GetValue(1),ia.GetValue(2))}
    decodedMesh.push({attributes:attrs,indices});
   } else {
    const comps={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}, sizes={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4};
    const readAccessor=(ai)=>{const a=j.accessors[ai],v=j.bufferViews[a.bufferView],n=comps[a.type],size=sizes[a.componentType],off=start+(v.byteOffset||0)+(a.byteOffset||0),dv=new DataView(input.buffer,input.byteOffset+off,v.byteLength-(a.byteOffset||0)),out=[];for(let q=0;q<a.count;q++)for(let c=0;c<n;c++){let z=(q*n+c)*size;out.push(a.componentType===5126?dv.getFloat32(z,true):a.componentType===5123?dv.getUint16(z,true):a.componentType===5125?dv.getUint32(z,true):a.componentType===5122?dv.getInt16(z,true):a.componentType===5121?dv.getUint8(z):dv.getInt8(z))}return out};
    const attrs={}; for(const [name,ai] of Object.entries(p.attributes)) attrs[name]=readAccessor(ai); const iv=readAccessor(p.indices); decodedMesh.push({attributes:attrs,indices:iv});
   }
  }
  out.push({name:j.meshes[mi].name,primitives:decodedMesh});
 }
 fs.writeFileSync(base+'/decoded.json',JSON.stringify(out));
})().catch(e=>{console.error(e);process.exit(1)});
''',encoding='utf-8')
    print('Decoding Draco geometry...')
    subprocess.run(['node',str(decode_js),str(out)],check=True)
    decoded=json.loads((out/'decoded.json').read_text())
    blob=bytearray(); views=[]; accessors=[]
    def align4():
        while len(blob)%4: blob.append(0)
    def add(rows, fmt, typ, comp, mins=None, maxs=None):
        align4(); off=len(blob)
        for row in rows: blob.extend(struct.pack('<'+fmt*len(row),*row))
        vi=len(views); views.append({'buffer':0,'byteOffset':off,'byteLength':len(blob)-off})
        a={'bufferView':vi,'componentType':comp,'count':len(rows),'type':typ}
        if mins is not None:a['min']=mins
        if maxs is not None:a['max']=maxs
        accessors.append(a); return len(accessors)-1
    def bounds(rows): return ([min(r[k] for r in rows) for k in range(len(rows[0]))],[max(r[k] for r in rows) for k in range(len(rows[0]))])
    # Copy animation accessors (the original first accessors point into the source buffer).
    remap={}
    for ai,a in enumerate(model.get('accessors',[])[:8]):
        if 'bufferView' not in a: continue
        bv=model['bufferViews'][a['bufferView']]; start=bv.get('byteOffset',0)+a.get('byteOffset',0); size=bv['byteLength']-a.get('byteOffset',0)
        align4(); off=len(blob); blob.extend(original[start:start+size]); nview=len(views); views.append({'buffer':0,'byteOffset':off,'byteLength':size})
        na=dict(a); na['bufferView']=nview; na.pop('byteOffset',None); accessors.append(na); remap[ai]=len(accessors)-1
    newmeshes=[]
    for mi,m in enumerate(model['meshes']):
        dm=decoded[mi]; primitives=[]
        for pi,(p,d) in enumerate(zip(m['primitives'],dm['primitives'])):
            attrs={}
            for name,old_ai in p['attributes'].items():
                if name not in d['attributes']: continue
                vals=d['attributes'][name]; typ='VEC2' if name=='TEXCOORD_0' else ('VEC4' if name in ('COLOR_0','TANGENT') else 'VEC3'); comp={'VEC2':2,'VEC3':3,'VEC4':4}[typ]; rows=[vals[i:i+comp] for i in range(0,len(vals),comp) if len(vals[i:i+comp])==comp]; mn,mx=bounds(rows); attrs[name]=add(rows,'f',typ,5126,mn,mx)
            idx=d['indices']
            index_fmt='I' if max(idx)>65535 else 'H'; index_comp=5125 if max(idx)>65535 else 5123
            attrs_idx=add([[x] for x in idx],index_fmt,'SCALAR',index_comp,[min(idx)],[max(idx)])
            primitives.append({'attributes':attrs,'indices':attrs_idx,'material':p.get('material',0)})
        newmeshes.append({'primitives':primitives, 'name':m.get('name','Mesh'+str(mi))})
    # Remap animation sampler accessors.
    animations=[]
    for anim in model.get('animations',[]):
        a=json.loads(json.dumps(anim))
        for s in a.get('samplers',[]):
            s['input']=remap.get(s['input'],s['input']); s['output']=remap.get(s['output'],s['output'])
        animations.append(a)
    # Build glTF material references from all p3d.in material assignments.
    materials=[]; images=[]; textures=[]; type_to_index={}; material_index={}
    api_materials={int(x['id']):x for x in api.get('materials',[])}
    for mi,ma in enumerate(model.get('materials',[])):
        match=next((x for x in api.get('materials',[]) if x.get('name')==ma.get('name')), None)
        match=match or (api.get('materials',[{}])[0] if api.get('materials') else {})
        ms=json.loads(match.get('settings','{}') or '{}'); tids={x.get('texture_type'):x.get('texture_id') for x in assignments.values() if x.get('material_id')==match.get('id')}
        def tex_index(tid):
            if tid not in id_to_file:return None
            if tid not in type_to_index:
                type_to_index[tid]=len(images); images.append({'uri':id_to_file[tid], 'name':tex_by_id[tid].get('name',str(tid))}); textures.append({'source':type_to_index[tid]})
            return type_to_index[tid]
        col=(str(ms.get('diff_col','ffffff'))+'ffffff')[:6]
        mm={'name':match.get('name',ma.get('name','Material'+str(mi))),'pbrMetallicRoughness':{'baseColorFactor':[int(col[i:i+2],16)/255 for i in (0,2,4)]+[float(ms.get('diff_alpha',1))], 'metallicFactor':float(ms.get('metalness',0)), 'roughnessFactor':float(ms.get('roughness',.5))}}
        ti=tex_index(tids.get('diff'))
        if ti is not None:mm['pbrMetallicRoughness']['baseColorTexture']={'index':ti}
        ti=tex_index(tids.get('roughness') or tids.get('metalness'))
        if ti is not None:mm['pbrMetallicRoughness']['metallicRoughnessTexture']={'index':ti}
        ti=tex_index(tids.get('norm'))
        if ti is not None:mm['normalTexture']={'index':ti,'scale':float(ms.get('norm_str',1))}
        if ms.get('alpha_blend'):mm['alphaMode']='BLEND'
        materials.append(mm)
    if not materials: materials=[{'name':'Default','pbrMetallicRoughness':{}}]
    gltf={'asset':{'version':'2.0','generator':'p3d.in extracted and Draco-decoded'},'scene':model.get('scene',0),'scenes':model['scenes'],'nodes':model['nodes'],'meshes':newmeshes,'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(blob),'uri':'model.bin'}],'materials':materials,'images':images,'textures':textures}
    if animations:gltf['animations']=animations
    write_json(out/'model.gltf',gltf); (out/'model.bin').write_bytes(blob)
    if not args.no_blender:
        blender=find_blender()
        if not blender: print('Blender not found; glTF output is ready')
        else:
            bs=work/'import_blend.py'; bs.write_text('''import bpy,sys\nfrom pathlib import Path\np=Path(sys.argv[-1]); out=p.parent/"model.blend"; glb=p.parent/"model.glb"\nbpy.ops.wm.read_factory_settings(use_empty=True)\nbpy.ops.import_scene.gltf(filepath=str(p))\n# Pack source images into the blend and replace WebP datablocks with PNG\n# datablocks so the exported single-file GLB does not require EXT_texture_webp.\ntmp=p.parent/"_compat_png"; tmp.mkdir(exist_ok=True)\nfor image in list(bpy.data.images):\n    if image.source != "FILE" or image.size[0] == 0: continue\n    png=tmp/(image.name.replace("/","_")+".png")\n    image.save_render(str(png))\n    converted=bpy.data.images.load(str(png),check_existing=False)\n    for material in bpy.data.materials:\n        if not material.use_nodes: continue\n        for node in material.node_tree.nodes:\n            if getattr(node,"image",None)==image: node.image=converted\n    converted.pack()\nfor image in bpy.data.images:\n    try: image.pack()\n    except: pass\nbpy.ops.wm.save_as_mainfile(filepath=str(out))\nbpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",export_keep_originals=False,export_image_format="AUTO",export_materials="EXPORT")\nprint("SAVED_BLEND",out)\nprint("SAVED_GLB",glb)\n''',encoding='utf-8')
            print('Importing glTF in Blender and exporting textured single-file GLB...'); subprocess.run([blender,'--background','--python',str(bs),'--',str(out/'model.gltf')],check=True)
    if not args.keep_work: shutil.rmtree(work,ignore_errors=True)
    print('Done:',out)
    print('glTF:',out/'model.gltf'); print('GLB:',out/'model.glb' if not args.no_blender else '(not requested)'); print('Blend:',out/'model.blend' if not args.no_blender else '(not requested)')
if __name__=='__main__': main()
