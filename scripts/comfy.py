#!/usr/bin/env python3
"""Make pictures with ComfyUI (Qwen-Image-2.1) running on another computer.

    python scripts/comfy.py --prompt "..." --out picture.png [--ref concept.png ...]
                            [--size 1024x1024] [--steps 25] [--seed 1] [--transparent]

ComfyUI must be reachable at COMFY_URL (default http://127.0.0.1:8188). How it is set up
and reached is described in docs/COMFYUI.md. With --ref the picture(s) are given to the
model as references; mention them in the prompt as <image1>, <image2>, ...
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
MODEL = "qwen_image_2.1_int8_convrot.safetensors"
TEXT_ENCODER = "qwen3vl_8b_int8_convrot.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"
TRANSPARENT = "This is an RGBA format image with transparency. %s The image has an alpha channel and a transparent background."


class ComfyError(Exception):
    pass


def call(path, data=None, headers=None):
    request = urllib.request.Request(URL + path, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise ComfyError("ComfyUI refused %s: %s" % (path, error.read().decode("utf-8", "replace")[:600]))
    except OSError as error:
        raise ComfyError("ComfyUI is not reachable at %s (%s). See docs/COMFYUI.md." % (URL, error))


def upload(path):
    """Send a reference picture to ComfyUI's input folder; returns the name it got there."""
    path = Path(path)
    boundary = uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: application/octet-stream\r\n\r\n"
             % (boundary, "sigma_" + path.name)).encode() + path.read_bytes()
            + ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (boundary, boundary)).encode())
    answer = json.loads(call("/upload/image", body, {"Content-Type": "multipart/form-data; boundary=" + boundary}))
    return answer["name"]


def workflow(prompt, references, width, height, steps, seed, prefix):
    """The node graph: load the model, read the prompt and references, sample, save."""
    graph = {
        "model": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "cache": {"class_type": "QwenImage21Cache", "inputs": {"model": ["model", 0], "device": "auto", "dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": TEXT_ENCODER, "type": "qwen_image", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "text": {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["clip", 0], "vae": ["vae", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024}},
        "canvas": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "sampler": {"class_type": "KSampler", "inputs": {
            "model": ["cache", 0], "positive": ["text", 0], "negative": ["text", 1], "latent_image": ["canvas", 0],
            "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}},
    }
    for number, name in enumerate(references, 1):
        graph["ref%d" % number] = {"class_type": "LoadImage", "inputs": {"image": name}}
        graph["text"]["inputs"]["images.image_%d" % number] = ["ref%d" % number, 0]
    return graph


def run(graph):
    """Queue a workflow, wait for it and return the bytes of the picture it saved."""
    job = json.loads(call("/prompt", json.dumps({"prompt": graph, "client_id": "sigma-dex"}).encode(), {"Content-Type": "application/json"}))
    if job.get("node_errors"):
        raise ComfyError("ComfyUI rejected the workflow: %s" % json.dumps(job["node_errors"])[:800])
    started = time.time()
    while True:
        history = json.loads(call("/history/" + job["prompt_id"]))
        entry = history.get(job["prompt_id"])
        if entry and entry.get("status", {}).get("completed"):
            break
        if entry and entry.get("status", {}).get("status_str") == "error":
            raise ComfyError("ComfyUI failed: %s" % json.dumps(entry["status"].get("messages"))[-800:])
        if time.time() - started > 1800:
            raise ComfyError("gave up after 30 minutes")
        time.sleep(2)
    image = next(image for output in entry["outputs"].values() for image in output.get("images", []))
    data = call("/view?" + urllib.parse.urlencode({"filename": image["filename"], "subfolder": image["subfolder"], "type": image["type"]}))
    return data


def generate(prompt, out, refs=(), size=(1024, 1024), steps=25, seed=None, transparent=False, quiet=False):
    """Make one picture and save it to `out`. Returns the seed that was used."""
    seed = int(time.time() * 1000) % (2 ** 31) if seed is None else seed
    if transparent:
        prompt = TRANSPARENT % prompt.strip()
    references = [upload(path) for path in refs]
    graph = workflow(prompt, references, size[0], size[1], steps, seed, "sigma/" + Path(out).stem)
    started = time.time()
    data = run(graph)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    if not quiet:
        print("%s  (%d s, seed %d)" % (out, time.time() - started, seed))
    return seed


CHECKPOINT = "Illustrious-XL-v1.0.safetensors"
EMERALD_LORA = "Pokemon_Sprite_Style.safetensors"
CONTROLNET = "controlnet-union-sdxl-promax.safetensors"
EMERALD_NEGATIVE = "human, trainer, text, watermark, signature, border, frame, blurry, gradient, 3d, realistic, photo, multiple views, background scenery"


def restyle(image, prompt, out, denoise=0.85, control=0.7, lora=1.0, steps=28, cfg=5.5, seed=None, quiet=False,
            checkpoint=None, lora_name=None, trigger="Pokemon Emerald Sprite, pixel art, ", negative=None, size=(1024, 1024)):
    """Redraw a picture as a Pokemon Emerald sprite: Illustrious + the Emerald sprite LoRA, image to image.

    `image` gives the creature and its pose: its outlines are held in place by a ControlNet
    (`control` = how firmly), while `denoise` says how freely the surfaces are repainted in the
    sprite style (0.5 keeps the original shading, 1.0 keeps only the outlines).
    """
    seed = int(time.time() * 1000) % (2 ** 31) if seed is None else seed
    graph = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint or CHECKPOINT}},
        "lora": {"class_type": "LoraLoader", "inputs": {"model": ["ckpt", 0], "clip": ["ckpt", 1], "lora_name": lora_name or EMERALD_LORA,
                                                         "strength_model": lora, "strength_clip": lora}},
        "positive": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["lora", 1], "text": trigger + prompt}},
        "negative": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["lora", 1], "text": negative or EMERALD_NEGATIVE}},
        "image": {"class_type": "LoadImage", "inputs": {"image": upload(image) if image else ""}},
        "edges": {"class_type": "Canny", "inputs": {"image": ["image", 0], "low_threshold": 0.2, "high_threshold": 0.5}},
        "cnet": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CONTROLNET}},
        "cnet_type": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["cnet", 0], "type": "canny/lineart/anime_lineart/mlsd"}},
        "control": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["positive", 0], "negative": ["negative", 0], "control_net": ["cnet_type", 0], "image": ["edges", 0],
            "strength": control, "start_percent": 0.0, "end_percent": 0.85, "vae": ["ckpt", 2]}},
        "encode": {"class_type": "VAEEncode", "inputs": {"pixels": ["image", 0], "vae": ["ckpt", 2]}},
        "sampler": {"class_type": "KSampler", "inputs": {
            "model": ["lora", 0], "positive": ["control", 0], "negative": ["control", 1], "latent_image": ["encode", 0],
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": "sigma/" + Path(out).stem}},
    }
    if image is None:                                 # nothing to start from: draw from the text alone
        control, graph["sampler"]["inputs"]["denoise"] = 0, 1.0
        del graph["image"]
        graph["encode"] = {"class_type": "EmptyLatentImage", "inputs": {"width": size[0], "height": size[1], "batch_size": 1}}
    if control <= 0:                                  # no outline lock: leave the ControlNet out entirely
        for name in ("edges", "cnet", "cnet_type", "control"):
            del graph[name]
        graph["sampler"]["inputs"].update(positive=["positive", 0], negative=["negative", 0])
    started = time.time()
    data = run(graph)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    if not quiet:
        print("%s  (%d s, seed %d)" % (out, time.time() - started, seed))
    return seed


IPADAPTER = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIP_VISION = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"


def sprite_ipa(reference, guide, prompt, out, weight=0.7, control=0.6, denoise=1.0, seed=None, quiet=False, checkpoint="NoobAI-XL-v1.1.safetensors",
               lora_name="pkspif_nb_v1-2.safetensors", negative=None, cfg=5.0, steps=28, weight_type="linear", control_end=0.8, ipa_end=0.6):
    """Draw a sprite with the Pokemon sprite LoRA at its own pixel scale, while an IP-Adapter looks at
    the concept art (`reference`: keeps the creature recognisable) and a ControlNet follows the
    outlines of `guide` (pose and proportions, already placed at sprite size on the 768 canvas)."""
    seed = int(time.time() * 1000) % (2 ** 31) if seed is None else seed
    graph = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "lora": {"class_type": "LoraLoader", "inputs": {"model": ["ckpt", 0], "clip": ["ckpt", 1], "lora_name": lora_name, "strength_model": 1.0, "strength_clip": 1.0}},
        "ipa_model": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPADAPTER}},
        "clip_vision": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIP_VISION}},
        "ref": {"class_type": "LoadImage", "inputs": {"image": upload(reference)}},
        "ipa": {"class_type": "IPAdapterAdvanced", "inputs": {"model": ["lora", 0], "ipadapter": ["ipa_model", 0], "image": ["ref", 0], "weight": weight, 
                                                               "weight_type": weight_type, "combine_embeds": "concat", "start_at": 0.0, "end_at": ipa_end,
                                                               "embeds_scaling": "V only", "clip_vision": ["clip_vision", 0]}},
        "positive": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["lora", 1], "text": prompt}},
        "negative": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["lora", 1], "text": negative or EMERALD_NEGATIVE}},
        "guide": {"class_type": "LoadImage", "inputs": {"image": upload(guide)}},
        "edges": {"class_type": "Canny", "inputs": {"image": ["guide", 0], "low_threshold": 0.2, "high_threshold": 0.5}},
        "cnet": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CONTROLNET}},
        "cnet_type": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["cnet", 0], "type": "canny/lineart/anime_lineart/mlsd"}},
        "control": {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": ["positive", 0], "negative": ["negative", 0], "control_net": ["cnet_type", 0],
                                                                         "image": ["edges", 0], "strength": control, "start_percent": 0.0, "end_percent": control_end, "vae": ["ckpt", 2]}},
        "encode": {"class_type": "VAEEncode", "inputs": {"pixels": ["guide", 0], "vae": ["ckpt", 2]}},
        "sampler": {"class_type": "KSampler", "inputs": {"model": ["ipa", 0], "positive": ["control", 0], "negative": ["control", 1], "latent_image": ["encode", 0],
                                                         "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": "sigma/" + Path(out).stem}},
    }
    if control <= 0:
        for name in ("edges", "cnet", "cnet_type", "control"):
            del graph[name]
        graph["sampler"]["inputs"].update(positive=["positive", 0], negative=["negative", 0])
    started = time.time()
    data = run(graph)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    if not quiet:
        print("%s  (%d s, seed %d)" % (out, time.time() - started, seed))
    return seed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ref", action="append", default=[])
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--transparent", action="store_true")
    args = parser.parse_args()
    width, height = (int(v) for v in args.size.lower().split("x"))
    try:
        generate(args.prompt, args.out, args.ref, (width, height), args.steps, args.seed, args.transparent)
    except ComfyError as error:
        sys.exit(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
