"""
Greenhouse Crop Growth Monitoring - Frame Differencing + Contour Area Growth Rate
Dataset: CVPPP2017_LCC_training
Algorithm: Frame Differencing + Contour Area Growth Rate
Tools: Python + OpenCV + Matplotlib
"""

import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import json

# ─────────────────────────────────────────────
# CONFIGURATION — DATASET SELECTION
# ─────────────────────────────────────────────

# Option 1: Use extracted CVPPP dataset (recommended)
CVPPP_DATASET_DIR = "dataset/CVPPP2017_LCC_training_extracted"

# Option 2: Use specific sequence (uncomment to override)
# Set to None to auto-detect, or specify sequence folder path
DATASET_DIR = None  # Will be set by main()
GT_MASK_DIR = None  # Will be set by main() if available

# Output configuration
OUTPUT_DIR = "output/results"
IMAGE_SIZE = (256, 256)
BLUR_KERNEL = (5, 5)
DIFF_THRESH = 50  # Increased from 15 to reduce false positives (white masks)
MIN_CONTOUR = 1000  # Increased to filter more noise

# ─────────────────────────────────────────────
# STEP 1: AUTO-DETECT AND LOAD SEQUENCE
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# STEP 1: AUTO-DETECT AND LOAD SEQUENCE
# ─────────────────────────────────────────────

def find_actual_dataset_dir(base_dir):
    """
    Find the actual dataset directory (handles nested structure).
    The CVPPP dataset may be nested: base_dir/CVPPP2017_LCC_training/training/
    """
    # Try direct path first
    if os.path.exists(base_dir):
        # Check if base_dir contains sequence folders directly
        for item in os.listdir(base_dir):
            if not item.startswith('_'):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path):
                    try:
                        images = [f for f in os.listdir(item_path)
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                        if images:
                            return base_dir
                    except PermissionError:
                        pass
    
    # Try nested structure: base_dir/CVPPP2017_LCC_training/training/
    nested_path = os.path.join(base_dir, "CVPPP2017_LCC_training", "training")
    if os.path.exists(nested_path):
        for item in os.listdir(nested_path):
            if not item.startswith('_'):
                item_path = os.path.join(nested_path, item)
                if os.path.isdir(item_path):
                    try:
                        images = [f for f in os.listdir(item_path)
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                        if images:
                            return nested_path
                    except PermissionError:
                        pass
    
    # Try alternative: base_dir/training/
    alt_path = os.path.join(base_dir, "training")
    if os.path.exists(alt_path):
        for item in os.listdir(alt_path):
            if not item.startswith('_'):
                item_path = os.path.join(alt_path, item)
                if os.path.isdir(item_path):
                    try:
                        images = [f for f in os.listdir(item_path)
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                        if images:
                            return alt_path
                    except PermissionError:
                        pass
    
    return None


def find_plant_sequences(dataset_dir):
    """
    Find all plant sequences in the dataset directory.
    Returns list of (sequence_name, sequence_path) tuples.
    """
    sequences = []
    
    # Find the actual dataset directory
    actual_dir = find_actual_dataset_dir(dataset_dir)
    if not actual_dir:
        print(f"[ERROR] Dataset directory not found or empty: {dataset_dir}")
        return sequences
    
    print(f"[INFO] Using dataset directory: {actual_dir}")
    
    for item in sorted(os.listdir(actual_dir)):
        if item.startswith('_'):
            continue
        item_path = os.path.join(actual_dir, item)
        if os.path.isdir(item_path):
            # Check if folder contains images
            try:
                images = [f for f in os.listdir(item_path)
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                if images:
                    sequences.append((item, item_path))
            except PermissionError:
                pass
    
    return sequences


def load_image_sequence(folder):
    """Load all images from a folder, sorted by filename."""
    supported = (".png", ".jpg", ".jpeg", ".bmp")
    files = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(supported)
    ])
    images = []
    filenames = []
    for f in files:
        path = os.path.join(folder, f)
        img = cv2.imread(path)
        if img is not None:
            images.append(img)
            filenames.append(f)
    print(f"[INFO] Loaded {len(images)} images from '{folder}'")
    return images, filenames


def load_gt_masks(folder):
    """Load ground truth binary masks for IoU evaluation."""
    if not os.path.exists(folder):
        print(f"[WARN] GT mask folder not found: {folder}")
        return []
    supported = (".png", ".jpg", ".bmp")
    files = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(supported)
    ])
    masks = []
    for f in files:
        path = os.path.join(folder, f)
        mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            masks.append(mask)
    print(f"[INFO] Loaded {len(masks)} GT masks from '{folder}'")
    return masks


# ─────────────────────────────────────────────
# STEP 2: PREPROCESSING (3 mandatory filters)
# ─────────────────────────────────────────────

def preprocess_image(img):
    """
    Apply 3 filters:
      1. Resize     — standardise image dimensions
      2. Denoise    — Gaussian blur to remove sensor/lighting noise
      3. Enhance    — CLAHE for improved leaf-background contrast
    Returns grayscale preprocessed image.
    """
    # Filter 1: Resize
    resized = cv2.resize(img, IMAGE_SIZE)

    # Filter 2: Grayscale + Gaussian blur (denoise)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)

    # Filter 3: CLAHE (contrast enhancement)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)

    return enhanced


def preprocess_sequence(images):
    """Preprocess all images in sequence."""
    processed = [preprocess_image(img) for img in images]
    print(f"[INFO] Preprocessed {len(processed)} images")
    return processed


def save_preprocessing_demo(original, processed, output_dir):
    """Save before/after preprocessing comparison images for report."""
    os.makedirs(output_dir, exist_ok=True)

    orig_resized = cv2.resize(original, IMAGE_SIZE)
    gray = cv2.cvtColor(orig_resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    clahe_obj = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe_obj.apply(blurred)

    cv2.imwrite(os.path.join(output_dir, "pre_1_original.png"), orig_resized)
    cv2.imwrite(os.path.join(output_dir, "pre_2_grayscale.png"), gray)
    cv2.imwrite(os.path.join(output_dir, "pre_3_blurred.png"), blurred)
    cv2.imwrite(os.path.join(output_dir, "pre_4_clahe.png"), enhanced)
    print("[INFO] Preprocessing demo images saved.")


# ─────────────────────────────────────────────
# STEP 3 & 4: FRAME DIFFERENCING + CONTOUR DETECTION
# ─────────────────────────────────────────────

def frame_difference(frame1, frame2):
    """
    Compute absolute difference between two frames.
    Returns binary change mask.
    """
    diff = cv2.absdiff(frame1, frame2)
    _, mask = cv2.threshold(diff, DIFF_THRESH, 255, cv2.THRESH_BINARY)

    # Morphological ops: remove small noise blobs, fill gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return mask


def get_largest_contour_area(binary_mask):
    """
    Find contours in binary mask.
    Returns the area of the largest contour (the plant leaf region).
    Also returns the contour itself for drawing.
    """
    contours, _ = cv2.findContours(
        binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return 0, None

    # Filter tiny contours (noise)
    valid = [c for c in contours if cv2.contourArea(c) > MIN_CONTOUR]
    if not valid:
        return 0, None

    largest = max(valid, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    return area, largest


def get_full_leaf_mask(processed_frame):
    """
    For evaluation: create a binary leaf mask from a single preprocessed frame
    using adaptive thresholding for better plant segmentation.
    """
    mask = cv2.adaptiveThreshold(
        processed_frame, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def run_frame_differencing(processed_frames):
    """
    Run frame differencing across the entire sequence.
    Returns:
      - areas: leaf contour area at each frame (from frame 1 onward)
      - diff_masks: binary diff mask for each consecutive pair
      - contours: largest contour for each pair
    """
    areas = []
    diff_masks = []
    contours = []

    for i in range(1, len(processed_frames)):
        mask = frame_difference(processed_frames[i - 1], processed_frames[i])
        area, contour = get_largest_contour_area(mask)
        areas.append(area)
        diff_masks.append(mask)
        contours.append(contour)

    print(f"[INFO] Frame differencing done. {len(areas)} area values extracted.")
    return areas, diff_masks, contours


# ─────────────────────────────────────────────
# STEP 4 (continued): GROWTH RATE CALCULATION
# ─────────────────────────────────────────────

def compute_growth_rates(areas):
    """
    Compute growth rate between consecutive frames.
    GR(t) = (Area(t) - Area(t-1)) / Area(t-1)
    Returns list of growth rate values.
    """
    growth_rates = []
    for i in range(1, len(areas)):
        if areas[i - 1] > 0:
            gr = (areas[i] - areas[i - 1]) / areas[i - 1]
        else:
            gr = 0.0
        growth_rates.append(gr)
    return growth_rates


# ─────────────────────────────────────────────
# STEP 5: EVALUATION — IoU
# ─────────────────────────────────────────────

def compute_iou(pred_mask, gt_mask):
    """
    Compute Intersection over Union between predicted mask and GT mask.
    Both must be binary (0 or 255).
    """
    pred_bin = (pred_mask > 127).astype(np.uint8)
    gt_bin = (cv2.resize(gt_mask, IMAGE_SIZE) > 127).astype(np.uint8)

    intersection = np.logical_and(pred_bin, gt_bin).sum()
    union = np.logical_or(pred_bin, gt_bin).sum()

    if union == 0:
        return 0.0
    return float(intersection) / float(union)


def evaluate_iou(processed_frames, gt_masks, areas):
    """Compute IoU and area accuracy for each frame against its GT mask."""
    if not gt_masks:
        print("[WARN] No GT masks found. Skipping evaluation.")
        return [], []

    iou_scores = []
    area_errors = []
    n = min(len(processed_frames), len(gt_masks), len(areas))
    for i in range(n):
        pred_mask = get_full_leaf_mask(processed_frames[i])
        iou_score = compute_iou(pred_mask, gt_masks[i])
        iou_scores.append(iou_score)
        
        # Compute GT area
        gt_mask_resized = cv2.resize(gt_masks[i], IMAGE_SIZE)
        gt_bin = (gt_mask_resized > 127).astype(np.uint8)
        gt_area = np.sum(gt_bin)
        
        # Area error (absolute difference)
        area_error = abs(areas[i] - gt_area)
        area_errors.append(area_error)

    mean_iou = np.mean(iou_scores) if iou_scores else 0
    mean_area_error = np.mean(area_errors) if area_errors else 0
    area_error_std = np.std(area_errors) if area_errors else 0
    
    print(f"[RESULT] Mean IoU: {mean_iou:.4f}")
    print(f"[RESULT] Mean Area Error: {mean_area_error:.0f} px (±{area_error_std:.0f})")
    
    return iou_scores, area_errors


def save_preprocessing_demo(original_img, processed_img, output_dir):
    """
    Save demo images showing preprocessing steps.
    Saves: original, resized, blurred, enhanced (CLAHE)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Original
    cv2.imwrite(os.path.join(output_dir, "01_original.png"), original_img)
    
    # Resized
    resized = cv2.resize(original_img, IMAGE_SIZE)
    cv2.imwrite(os.path.join(output_dir, "02_resized.png"), resized)
    
    # Grayscale + blurred (without CLAHE to avoid black images)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    cv2.imwrite(os.path.join(output_dir, "03_blurred.png"), blurred)
    
    # Enhanced (CLAHE with lower clipLimit to avoid over-enhancement)
    clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))  # Lower clipLimit
    enhanced = clahe.apply(blurred)
    cv2.imwrite(os.path.join(output_dir, "04_enhanced.png"), enhanced)
    
    print(f"[INFO] Preprocessing demo images saved to '{output_dir}'")

def save_annotated_frames(original_images, diff_masks, contours, areas, output_dir):
    """
    Save output frames with:
      - Green contour drawn on the original image
      - Area value displayed on frame
      - Diff mask saved separately
    """
    frames_dir = os.path.join(output_dir, "annotated_frames")
    masks_dir = os.path.join(output_dir, "diff_masks")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(masks_dir, exist_ok=True)

    for i, (mask, contour, area) in enumerate(zip(diff_masks, contours, areas)):
        # Annotate original frame (frame i+1 corresponds to diff i)
        frame = cv2.resize(original_images[i + 1].copy(), IMAGE_SIZE)
        if contour is not None:
            cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)

        label = f"Frame {i+1} | Area: {int(area)} px"
        cv2.putText(frame, label, (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imwrite(os.path.join(frames_dir, f"frame_{i+1:03d}.png"), frame)
        cv2.imwrite(os.path.join(masks_dir, f"mask_{i+1:03d}.png"), mask)

    print(f"[INFO] Annotated frames saved to '{frames_dir}'")


# ─────────────────────────────────────────────
# OUTPUT: GROWTH CURVE PLOT
# ─────────────────────────────────────────────

def plot_growth_curve(areas, growth_rates, iou_scores, output_dir, sequence_name=""):
    """Plot and save growth analysis charts."""
    os.makedirs(output_dir, exist_ok=True)
    frames = list(range(1, len(areas) + 1))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    title = f"Greenhouse Crop Growth Monitoring — {sequence_name}"
    fig.suptitle(title, fontsize=13, fontweight="bold")

    # Plot 1: Contour area over time
    axes[0].plot(frames, areas, color="#2ecc71", linewidth=2, marker="o", markersize=4)
    axes[0].fill_between(frames, areas, alpha=0.15, color="#2ecc71")
    axes[0].set_title("Leaf Contour Area Over Time")
    axes[0].set_xlabel("Frame")
    axes[0].set_ylabel("Area (pixels)")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Plot 2: Growth rate per frame
    if growth_rates:
        gr_frames = list(range(2, len(growth_rates) + 2))
        colors = ["#e74c3c" if g < 0 else "#3498db" for g in growth_rates]
        axes[1].bar(gr_frames, growth_rates, color=colors, edgecolor="white", linewidth=0.5)
        axes[1].axhline(0, color="black", linewidth=0.8)
        axes[1].set_title("Growth Rate Per Frame")
        axes[1].set_xlabel("Frame")
        axes[1].set_ylabel("Growth Rate (fraction)")
        axes[1].grid(True, linestyle="--", alpha=0.5, axis="y")
        pos_patch = mpatches.Patch(color="#3498db", label="Growth")
        neg_patch = mpatches.Patch(color="#e74c3c", label="Shrinkage / noise")
        axes[1].legend(handles=[pos_patch, neg_patch], fontsize=8)

    # Plot 3: IoU scores
    if iou_scores:
        iou_frames = list(range(1, len(iou_scores) + 1))
        axes[2].plot(iou_frames, iou_scores, color="#9b59b6", linewidth=2, marker="s", markersize=4)
        axes[2].set_ylim(0, 1)
        axes[2].axhline(np.mean(iou_scores), color="orange", linestyle="--",
                        linewidth=1.2, label=f"Mean IoU = {np.mean(iou_scores):.3f}")
        axes[2].set_title("IoU Score Per Frame")
        axes[2].set_xlabel("Frame")
        axes[2].set_ylabel("IoU")
        axes[2].legend(fontsize=8)
        axes[2].grid(True, linestyle="--", alpha=0.5)
    else:
        axes[2].text(0.5, 0.5, "No GT masks\nfound for IoU",
                     ha="center", va="center", transform=axes[2].transAxes,
                     fontsize=11, color="gray")
        axes[2].set_title("IoU Score Per Frame")

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "growth_analysis.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"[INFO] Growth analysis plot saved to '{plot_path}'")
    # Don't display plot - just save it
    plt.close()  # Close the figure to free memory


# ─────────────────────────────────────────────
# SUMMARY: SAVE RESULTS TO JSON
# ─────────────────────────────────────────────

def save_results_json(sequence_name, areas, growth_rates, iou_scores, area_errors, output_dir):
    """Save analysis results to JSON file for further processing."""
    results = {
        "sequence": sequence_name,
        "num_frames": len(areas),
        "areas": [int(a) for a in areas],
        "growth_rates": [float(gr) for gr in growth_rates],
        "iou_scores": [float(iou) for iou in iou_scores],
        "area_errors": [float(err) for err in area_errors] if area_errors else [],
        "statistics": {
            "mean_area": float(np.mean(areas)) if areas else 0,
            "max_area": float(np.max(areas)) if areas else 0,
            "min_area": float(np.min(areas)) if areas else 0,
            "mean_growth_rate": float(np.mean(growth_rates)) if growth_rates else 0,
            "max_growth_rate": float(np.max(growth_rates)) if growth_rates else 0,
            "mean_iou": float(np.mean(iou_scores)) if iou_scores else 0,
            "mean_area_error": float(np.mean(area_errors)) if area_errors else 0,
        }
    }
    
    json_path = os.path.join(output_dir, "results.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"[INFO] Results saved to '{json_path}'")


# ─────────────────────────────────────────────
# PRINT SUMMARY TABLE
# ─────────────────────────────────────────────

def print_summary(areas, growth_rates, iou_scores, area_errors, sequence_name):
    print("\n" + "=" * 60)
    print(f"SEQUENCE: {sequence_name}")
    print("=" * 60)
    print(f"{'FRAME':<8} {'AREA (px)':<14} {'GROWTH RATE':<14} {'IoU':<8}")
    print("=" * 60)
    for i, area in enumerate(areas):
        gr = f"{growth_rates[i-1]:.4f}" if i > 0 and i - 1 < len(growth_rates) else "  —  "
        iou = f"{iou_scores[i]:.4f}" if i < len(iou_scores) else "  —  "
        print(f"{i+1:<8} {int(area):<14} {gr:<14} {iou:<8}")
    print("=" * 60)
    if iou_scores:
        print(f"Mean IoU : {np.mean(iou_scores):.4f}")
    if growth_rates:
        print(f"Mean GR  : {np.mean(growth_rates):.4f}")
    if area_errors:
        print(f"Mean Area Error: {np.mean(area_errors):.0f} px")
        print(f"Max GR   : {max(growth_rates):.4f}  (frame with most growth)")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────
# MAIN PROCESSING FUNCTION
# ─────────────────────────────────────────────

def process_sequence(dataset_dir, gt_mask_dir, sequence_name, output_base_dir):
    """Process a single plant growth sequence."""
    
    print(f"\n{'='*60}")
    print(f"Processing: {sequence_name}")
    print(f"{'='*60}")
    
    # Create output directory for this sequence
    seq_output_dir = os.path.join(output_base_dir, sequence_name)
    
    # 1. Load data
    images, filenames = load_image_sequence(dataset_dir)
    gt_masks = load_gt_masks(gt_mask_dir) if gt_mask_dir else []

    if len(images) < 2:
        print(f"[WARN] Sequence {sequence_name} has fewer than 2 images. Skipping.")
        return None

    # 2. Preprocess
    processed = preprocess_sequence(images)
    save_preprocessing_demo(images[0], processed[0], 
                           os.path.join(seq_output_dir, "preprocessing"))

    # 3 & 4. Frame differencing + contour area extraction + growth rate
    areas, diff_masks, contours = run_frame_differencing(processed)
    growth_rates = compute_growth_rates(areas)

    # 5. Evaluation — IoU
    iou_scores, area_errors = evaluate_iou(processed, gt_masks, areas)

    # Save outputs
    save_annotated_frames(images, diff_masks, contours, areas, seq_output_dir)
    plot_growth_curve(areas, growth_rates, iou_scores, seq_output_dir, sequence_name)
    save_results_json(sequence_name, areas, growth_rates, iou_scores, area_errors, seq_output_dir)
    print_summary(areas, growth_rates, iou_scores, area_errors, sequence_name)
    
    return {
        "sequence": sequence_name,
        "areas": areas,
        "growth_rates": growth_rates,
        "iou_scores": iou_scores,
        "area_errors": area_errors
    }


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main():
    """Main execution function."""
    
    print("\n" + "="*60)
    print("GREENHOUSE CROP GROWTH MONITORING SYSTEM")
    print("Algorithm: Frame Differencing + Contour Area Growth Rate")
    print("Dataset: CVPPP2017_LCC_training")
    print("="*60 + "\n")
    
    # Check if CVPPP dataset exists
    if not os.path.exists(CVPPP_DATASET_DIR):
        print(f"[ERROR] CVPPP dataset not found at: {CVPPP_DATASET_DIR}")
        print("\n[HINT] To prepare the dataset:")
        print("  1. Run: python prepare_cvppp_dataset.py")
        print("  2. This will extract the CVPPP2017_LCC_training.zip file")
        return
    
    # Find all sequences
    sequences = find_plant_sequences(CVPPP_DATASET_DIR)
    
    if not sequences:
        print(f"[ERROR] No plant sequences found in: {CVPPP_DATASET_DIR}")
        return
    
    print(f"[INFO] Found {len(sequences)} plant sequences\n")
    
    # Process all sequences or a specific one
    results = []
    for seq_name, seq_path in sequences:
        # Try to find GT masks - check multiple locations
        gt_path = None
        
        # Try: CVPPP_DATASET_DIR/gt/seq_name
        potential_gt = os.path.join(CVPPP_DATASET_DIR, "gt", seq_name)
        if os.path.exists(potential_gt):
            gt_path = potential_gt
        
        # Try: parent_of_seq_path/gt/seq_name
        if not gt_path:
            parent_dir = os.path.dirname(seq_path)
            potential_gt = os.path.join(parent_dir, "..", "gt", seq_name)
            if os.path.exists(potential_gt):
                gt_path = potential_gt
        
        # Try: direct seq_path/../gt/seq_name
        if not gt_path:
            potential_gt = os.path.join(seq_path, "..", "..", "gt", seq_name)
            if os.path.exists(os.path.normpath(potential_gt)):
                gt_path = os.path.normpath(potential_gt)
        
        # Try: seq_path/gt (inside sequence folder)
        if not gt_path:
            potential_gt = os.path.join(seq_path, "gt")
            if os.path.exists(potential_gt):
                gt_path = potential_gt
        
        result = process_sequence(seq_path, gt_path, seq_name, OUTPUT_DIR)
        if result:
            results.append(result)
    
    # Print final summary
    if results:
        print("\n" + "="*60)
        print(f"FINAL SUMMARY: Processed {len(results)} sequences")
        print("="*60)
        for res in results:
            seq_name = res["sequence"]
            mean_gr = np.mean(res["growth_rates"]) if res["growth_rates"] else 0
            mean_iou = np.mean(res["iou_scores"]) if res["iou_scores"] else 0
            mean_area_error = np.mean(res["area_errors"]) if "area_errors" in res and res["area_errors"] else 0
            print(f"{seq_name:20} | Mean GR: {mean_gr:7.4f} | Mean IoU: {mean_iou:7.4f} | Mean Area Error: {mean_area_error:7.0f}px")
        print("="*60)


if __name__ == "__main__":
    main()
