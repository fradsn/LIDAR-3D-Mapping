import json
import numpy as np

def export_to_ply(filepath: str, points: list, colors: np.ndarray = None):
    """
    Esporta la nuvola di punti in formato PLY ASCII (con colori RGB).
    Perfettamente compatibile con Blender, CloudCompare e MeshLab.
    """
    if not points:
        return False

    pts_np = np.array(points, dtype=np.float32)
    n_pts = len(pts_np)

    # Calcola colori RGB (0-255) se non forniti esplicitamente
    if colors is None or len(colors) != n_pts:
        z = pts_np[:, 2]
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-5)
        rgb = np.zeros((n_pts, 3), dtype=np.uint8)
        rgb[:, 0] = (z_norm * 255).astype(np.uint8)          # R
        rgb[:, 1] = ((1.0 - z_norm) * 255).astype(np.uint8)  # G
        rgb[:, 2] = 200                                      # B
    else:
        rgb = (colors[:, :3] * 255).astype(np.uint8)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n_pts}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for i in range(n_pts):
            f.write(f"{pts_np[i, 0]:.2f} {pts_np[i, 1]:.2f} {pts_np[i, 2]:.2f} {rgb[i, 0]} {rgb[i, 1]} {rgb[i, 2]}\n")
    return True

def export_to_xyz(filepath: str, points: list):
    """Esporta la nuvola di punti in formato testo XYZ/CSV."""
    if not points:
        return False
    with open(filepath, 'w', encoding='utf-8') as f:
        for pt in points:
            f.write(f"{pt[0]:.2f} {pt[1]:.2f} {pt[2]:.2f}\n")
    return True

def save_to_json(filepath: str, points: list, metadata: dict = None):
    """Salva una sessione di scansione con metadati in formato JSON."""
    data = {
        "metadata": metadata or {},
        "points": points
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return True

def load_from_json(filepath: str):
    """Carica una scansione precedentemente salvata da file JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("points", []), data.get("metadata", {})