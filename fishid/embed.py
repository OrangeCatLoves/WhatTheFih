"""Pipeline step 2 (doc §6): BioCLIP 2 turns a crop into a vector of 768 numbers.

BioCLIP 2 stays frozen (no training). Each vector is scaled to length 1.
"""

import numpy as np
import torch

BIOCLIP = "imageomics/bioclip-2"
BIOCLIP_REVISION = "2957b322090f9cb17ae72c71981c7218a28d81e0"  # pinned, so training and the app use the same weights
BIOCLIP_FILES = ["open_clip_config.json", "open_clip_model.safetensors"]


class Embedder:
    def __init__(self, device="cpu"):
        import open_clip
        from huggingface_hub import snapshot_download

        # open_clip can't pin a version itself, so download the pinned version and load it from that folder.
        folder = snapshot_download(BIOCLIP, revision=BIOCLIP_REVISION, allow_patterns=BIOCLIP_FILES)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(f"local-dir:{folder}")
        self.model.to(device).eval()
        self.device = device

    @torch.inference_mode()
    def embed(self, images):
        """One length-1 vector per image (PIL), as a float32 array of shape (len(images), 768)."""
        batch = torch.stack([self.preprocess(image) for image in images]).to(self.device)
        vectors = self.model.encode_image(batch).float()
        vectors = vectors / vectors.norm(dim=-1, keepdim=True)
        return vectors.cpu().numpy().astype(np.float32)
