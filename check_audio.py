import soundfile as sf
import numpy as np
import sys

path = r'c:\Users\smmgo\Documents\Generation Null\Mastering app\uploads\be1cfdb7-28a7-44d5-b9a0-fc6e0b9ac149\output_51_norm.wav'
try:
    data, sr = sf.read(path)
    print(f"Stats for {path}:")
    print(f"Shape: {data.shape}")
    print(f"Max: {np.max(data)}")
    print(f"Min: {np.min(data)}")
    print(f"Mean: {np.mean(data)}")
    print(f"Has NaN: {np.isnan(data).any()}")
    print(f"Has Inf: {np.isinf(data).any()}")
    
    # Check if it's all zeros
    print(f"All zeros: {np.all(data == 0)}")
    
    # Check first few samples
    print(f"First 10 samples (channel 0):\n{data[:10, 0]}")
except Exception as e:
    print(f"Error: {e}")
