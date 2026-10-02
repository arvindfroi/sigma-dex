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


def generate(prompt, out, refs=(), size=(1024, 1024), steps=25, seed=None, transparent=False, quiet=False):
    """Make one picture and save it to `out`. Returns the seed that was used."""
    seed = int(time.time() * 1000) % (2 ** 31) if seed is None else seed
    if transparent:
        prompt = TRANSPARENT % prompt.strip()
    references = [upload(path) for path in refs]
    graph = workflow(prompt, references, size[0], size[1], steps, seed, "sigma/" + Path(out).stem)
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
