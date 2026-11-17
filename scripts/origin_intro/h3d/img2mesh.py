"""Image -> 3D mesh with Hunyuan3D 2.1 in ComfyUI (on the Legion, reached through an SSH tunnel on 8188).
python h3d/img2mesh.py IMAGE.png OUT.glb [seed] [octree] [steps]
Single view. The picture should be the creature alone on white (or RGBA), filling ~85-90 % of a square."""
import sys, os, json, time, uuid, urllib.request, urllib.parse
URL = os.environ.get('COMFY_URL', 'http://127.0.0.1:8188')
img, out = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
octree = int(sys.argv[4]) if len(sys.argv) > 4 else 384
steps = int(sys.argv[5]) if len(sys.argv) > 5 else 40
CKPT = os.environ.get('H3D_CKPT', 'hunyuan_3d_v2.1.safetensors')

def call(path, data=None, headers=None, timeout=600):
    r = urllib.request.Request(URL + path, data=data, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as f: return f.read()

def upload(path):
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="h3d_{os.path.basename(path)}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n').encode() + open(path, 'rb').read() + \
           f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n'.encode()
    return json.loads(call('/upload/image', body, {'Content-Type': 'multipart/form-data; boundary=' + b}))['name']

name = upload(img)
prefix = 'h3d/' + os.path.splitext(os.path.basename(out))[0]
g = {
    'ckpt': {'class_type': 'ImageOnlyCheckpointLoader', 'inputs': {'ckpt_name': CKPT}},
    'img': {'class_type': 'LoadImage', 'inputs': {'image': name}},
    'enc': {'class_type': 'CLIPVisionEncode', 'inputs': {'clip_vision': ['ckpt', 1], 'image': ['img', 0], 'crop': 'none'}},
    'cond': {'class_type': 'Hunyuan3Dv2Conditioning', 'inputs': {'clip_vision_output': ['enc', 0]}},
    'lat': {'class_type': 'EmptyLatentHunyuan3Dv2', 'inputs': {'resolution': 4096, 'batch_size': 1}},
    'ms': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['ckpt', 0], 'shift': 1.0}},
    'ks': {'class_type': 'KSampler', 'inputs': {'model': ['ms', 0], 'positive': ['cond', 0], 'negative': ['cond', 1],
           'latent_image': ['lat', 0], 'seed': seed, 'steps': steps, 'cfg': 5.0, 'sampler_name': 'euler',
           'scheduler': 'normal', 'denoise': 1.0}},
    'dec': {'class_type': 'VAEDecodeHunyuan3D', 'inputs': {'samples': ['ks', 0], 'vae': ['ckpt', 2], 'num_chunks': 8000,
            'octree_resolution': octree}},
    'mesh': {'class_type': 'VoxelToMesh', 'inputs': {'voxel': ['dec', 0], 'algorithm': 'surface net', 'threshold': 0.6}},
    'save': {'class_type': 'SaveGLB', 'inputs': {'mesh': ['mesh', 0], 'filename_prefix': prefix}},
}
job = json.loads(call('/prompt', json.dumps({'prompt': g, 'client_id': 'h3d'}).encode(), {'Content-Type': 'application/json'}))
if job.get('node_errors'): raise SystemExit(json.dumps(job['node_errors'])[:1500])
pid = job['prompt_id']; t0 = time.time()
while True:
    h = json.loads(call('/history/' + pid)).get(pid)
    if h and h.get('status', {}).get('completed'): break
    if h and h.get('status', {}).get('status_str') == 'error': raise SystemExit(json.dumps(h['status'].get('messages'))[-1500:])
    time.sleep(3)
files = [f for o in h['outputs'].values() for k in ('3d', 'meshes', 'glb', 'images') for f in o.get(k, [])]
if not files: raise SystemExit('no output: ' + json.dumps(h['outputs'])[:800])
f = files[0]
data = call('/view?' + urllib.parse.urlencode({'filename': f['filename'], 'subfolder': f.get('subfolder', ''), 'type': f.get('type', 'output')}))
open(out, 'wb').write(data)
print('ok', out, len(data), 'bytes', round(time.time() - t0), 's')
