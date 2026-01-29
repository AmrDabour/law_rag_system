"""
Device Detection Utility
Auto-detects GPU/CPU and provides fallback without errors
"""

import torch
import logging
from typing import Literal

logger = logging.getLogger(__name__)

DeviceType = Literal["cuda", "cpu"]


def get_device() -> DeviceType:
    """
    Auto-detect best available device.
    Returns 'cuda' if GPU available and working, otherwise 'cpu'.
    Never raises errors - always falls back to CPU gracefully.
    
    Returns:
        DeviceType: Either "cuda" or "cpu"
    """
    try:
        if torch.cuda.is_available():
            # Test that CUDA actually works
            torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"✅ CUDA available: {device_name} ({vram:.1f} GB VRAM)")
            return "cuda"
    except Exception as e:
        logger.warning(f"⚠️ CUDA detection failed: {e}")
    
    logger.info("ℹ️ Using CPU (CUDA not available)")
    return "cpu"


def get_torch_dtype(device: DeviceType) -> torch.dtype:
    """
    Get optimal dtype for the given device.
    
    Args:
        device: The device type ("cuda" or "cpu")
        
    Returns:
        torch.dtype: float16 for GPU, float32 for CPU
    """
    if device == "cuda":
        return torch.float16  # Faster on GPU
    return torch.float32  # CPU needs float32 for stability


def get_device_info() -> dict:
    """
    Get detailed device information for diagnostics.
    
    Returns:
        dict: Device information including type, name, and memory
    """
    info = {
        "device": get_device(),
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": None,
        "device_name": None,
        "vram_total_gb": None,
        "vram_free_gb": None,
    }
    
    if torch.cuda.is_available():
        try:
            info["cuda_version"] = torch.version.cuda
            info["device_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["vram_total_gb"] = round(props.total_memory / (1024**3), 2)
            free_mem = torch.cuda.memory_reserved(0) - torch.cuda.memory_allocated(0)
            info["vram_free_gb"] = round(free_mem / (1024**3), 2)
        except Exception:
            pass
    
    return info
