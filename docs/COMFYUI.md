# The image generator (ComfyUI)

Sprites and concept art can be drawn by an image model running on a gaming PC. Set up on
2026-10-02 on Arvind's Lenovo Legion (RTX 5080 Laptop, 16 GB VRAM, Windows 11).

## What is installed

| What | Where on the PC |
|---|---|
| ComfyUI 0.38 (from github.com/Comfy-Org/ComfyUI) with its own Python 3.12 and PyTorch (CUDA 13.0) | `D:\LocalAI\ComfyUI` |
| Qwen-Image-2.1, int8 version (7.3 GB) | `models\diffusion_models\qwen_image_2.1_int8_convrot.safetensors` |
| Its text encoder, int8 (9.4 GB) | `models\text_encoders\qwen3vl_8b_int8_convrot.safetensors` |
| Its VAE (0.7 GB) | `models\vae\qwen_image_2.1_vae_bf16.safetensors` |

The model files come from huggingface.co/Comfy-Org/Qwen-Image-2.1. One 1024x1024 picture
takes about 25 seconds.

**Licence:** Qwen-Image-2.1 is released under the Qwen Research License: non-commercial use
only. Our game is free and non-commercial; if that ever changes, this model has to be replaced.

## Using it yourself

Double-click `D:\LocalAI\ComfyUI\start_comfyui.bat`, wait for "To see the GUI go to", and
open http://127.0.0.1:8188. In Templates, search for "Qwen Image 2.1".

## Using it from the dex scripts

ComfyUI only listens on the PC itself. From another computer, open a tunnel over SSH and
leave it running (here the PC is `pc` in `~/.ssh/config`, reached over Tailscale):

```bash
ssh -L 8188:127.0.0.1:8188 pc "cd D:\LocalAI\ComfyUI; .venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188"
```

Then, from this repository:

```bash
python scripts/ai_sprites.py bergflabbser
```

```bash
python scripts/comfy.py --prompt "a round brown fish monster" --out test.png --transparent
```

`scripts/comfy.py` sends the job, waits and downloads the picture; `--ref picture.png` gives
the model a reference (call it `<image1>` in the prompt). See [SPRITES.md](SPRITES.md) for
how sprites are made from the results. If ComfyUI lives somewhere else, set `COMFY_URL`.
