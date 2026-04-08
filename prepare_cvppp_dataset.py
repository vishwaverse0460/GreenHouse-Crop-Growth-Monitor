"""
CVPPP2017 Dataset Preparation Script
Extracts and organizes the CVPPP2017_LCC_training.zip dataset
for use with the Frame Differencing + Contour Area Growth Rate model.
"""

import os
import shutil
import zipfile
from pathlib import Path

DATASET_ZIP = "dataset/CVPPP2017_LCC_training.zip"
DATASET_DIR = "dataset"
EXTRACT_DIR = "dataset/CVPPP2017_LCC_training_extracted"


def extract_dataset():
    """Extract the CVPPP2017 ZIP file if not already extracted."""
    if os.path.exists(EXTRACT_DIR):
        print(f"[INFO] Dataset already extracted at: {EXTRACT_DIR}")
        return EXTRACT_DIR
    
    if not os.path.exists(DATASET_ZIP):
        print(f"[ERROR] Dataset ZIP not found: {DATASET_ZIP}")
        return None
    
    print(f"[INFO] Extracting {DATASET_ZIP}...")
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    
    try:
        with zipfile.ZipFile(DATASET_ZIP, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
        print(f"[SUCCESS] Dataset extracted to: {EXTRACT_DIR}")
        return EXTRACT_DIR
    except Exception as e:
        print(f"[ERROR] Failed to extract dataset: {e}")
        return None


def find_training_dir(extract_dir):
    """Find the actual training data directory (handles nested structure)."""
    # Try common locations
    candidates = [
        extract_dir,  # Direct extraction
        os.path.join(extract_dir, "CVPPP2017_LCC_training", "training"),  # Nested structure
        os.path.join(extract_dir, "training"),  # Alternative nesting
    ]
    
    for candidate in candidates:
        if os.path.exists(candidate):
            # Check if this directory contains sequence folders
            for item in os.listdir(candidate):
                item_path = os.path.join(candidate, item)
                if os.path.isdir(item_path) and not item.startswith('_'):
                    # Check if it contains images
                    try:
                        images = [f for f in os.listdir(item_path)
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                        if images:
                            return candidate
                    except PermissionError:
                        pass
    return None


def list_available_sequences(extract_dir):
    """List all available plant sequences in the extracted dataset."""
    sequences = []
    
    # Find the actual training directory
    training_dir = find_training_dir(extract_dir)
    if not training_dir:
        return sequences
    
    # Look for sequence folders (A1, A2, A3, etc. or similar structure)
    for item in sorted(os.listdir(training_dir)):
        item_path = os.path.join(training_dir, item)
        if os.path.isdir(item_path) and not item.startswith('_'):
            # Check if it contains images
            try:
                images = [f for f in os.listdir(item_path) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                if images:
                    sequences.append((item, len(images)))
            except PermissionError:
                pass
    
    return sequences


def get_sequence_info(extract_dir):
    """Print info about available sequences."""
    sequences = list_available_sequences(extract_dir)
    if not sequences:
        print("[WARN] No image sequences found in extracted dataset.")
        training_dir = find_training_dir(extract_dir)
        if training_dir:
            print(f"[DEBUG] Training directory found at: {training_dir}")
        return
    
    print("\n" + "="*50)
    print(f"{'SEQUENCE':<20} {'IMAGE COUNT':<15}")
    print("="*50)
    for seq_name, img_count in sequences:
        print(f"{seq_name:<20} {img_count:<15}")
    print("="*50 + "\n")
    
    return sequences


def main():
    print("\nCVPPP2017 Dataset Preparation")
    print("=" * 50)
    
    # Step 1: Extract dataset
    extracted_path = extract_dataset()
    if not extracted_path:
        return
    
    # Step 2: Find actual training directory
    training_dir = find_training_dir(extracted_path)
    if not training_dir:
        print("[ERROR] Could not find training data directory in extracted dataset")
        return
    
    print(f"[INFO] Training data directory: {training_dir}\n")
    
    # Step 3: List available sequences
    sequences = get_sequence_info(extracted_path)
    
    if sequences:
        print(f"\n[INFO] Found {len(sequences)} plant growth sequences")
        print("[INFO] You can now use any of these sequences with the main model")
        print("\nExample usage in greenhouse_growth_monitor_cvppp.py:")
        print(f'  CVPPP_DATASET_DIR = "{training_dir}"')
    
    return training_dir, sequences


if __name__ == "__main__":
    main()
