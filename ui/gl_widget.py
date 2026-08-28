import pyqtgraph.opengl as gl
import numpy as np

class PointCloudView(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCameraPosition(distance=400, elevation=30, azimuth=45)
        
        # Griglia di riferimento cartesiana
        self.grid = gl.GLGridItem()
        self.grid.scale(20, 20, 1)
        self.grid.setDepthValue(10)
        self.addItem(self.grid)

        self.point_size = 3.0
        self.colormap_mode = "Elevation (Gradient)"
        self.current_points = []
        self.current_colors = np.empty((0, 4))

        # Scatter Plot OpenGL
        self.scatter = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=(0.1, 0.8, 1.0, 0.8),
            size=self.point_size,
            pxMode=True
        )
        self.addItem(self.scatter)

    def set_point_size(self, size: float):
        """Imposta la dimensione dei punti rendering."""
        self.point_size = float(size)
        if self.current_points:
            self.scatter.setData(pos=np.array(self.current_points, dtype=np.float32), 
                                 color=self.current_colors, 
                                 size=self.point_size)

    def set_colormap(self, mode: str):
        """Cambia la mappa colori della nuvola di punti."""
        self.colormap_mode = mode
        if self.current_points:
            self.update_cloud(self.current_points)

    def update_cloud(self, points: list):
        if not points:
            return
        self.current_points = points
        pts_np = np.array(points, dtype=np.float32)
        n = len(pts_np)

        colors = np.zeros((n, 4), dtype=np.float32)
        z = pts_np[:, 2]
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-5)

        if self.colormap_mode == "Elevation (Gradient)":
            colors[:, 0] = z_norm          # R
            colors[:, 1] = 1.0 - z_norm    # G
            colors[:, 2] = 0.8             # B
            colors[:, 3] = 0.85
        elif self.colormap_mode == "Radar Green":
            colors[:, 0] = 0.05
            colors[:, 1] = 0.95
            colors[:, 2] = 0.1
            colors[:, 3] = 0.85
        elif self.colormap_mode == "Monochrome White":
            colors[:, 0] = 0.95
            colors[:, 1] = 0.95
            colors[:, 2] = 0.95
            colors[:, 3] = 0.9
        elif self.colormap_mode == "Heatmap (Turbo)":
            # Approssimazione heatmap (Blu -> Ciano -> Giallo -> Rosso)
            colors[:, 0] = np.clip(1.5 - np.abs(z_norm * 4 - 3), 0, 1)
            colors[:, 1] = np.clip(1.5 - np.abs(z_norm * 4 - 2), 0, 1)
            colors[:, 2] = np.clip(1.5 - np.abs(z_norm * 4 - 1), 0, 1)
            colors[:, 3] = 0.85

        self.current_colors = colors
        self.scatter.setData(pos=pts_np, color=colors, size=self.point_size)

    # --- PRESET TELECAMERA RAPIDI ---
    def set_view_top(self):
        """Vista Pianta 2D dall'alto (Bird's eye)"""
        self.setCameraPosition(distance=450, elevation=90, azimuth=0)

    def set_view_front(self):
        """Vista Frontale X-Z"""
        self.setCameraPosition(distance=450, elevation=0, azimuth=0)

    def set_view_side(self):
        """Vista Laterale Y-Z"""
        self.setCameraPosition(distance=450, elevation=0, azimuth=90)

    def set_view_iso(self):
        """Vista Prospettica Isometrica 3D"""
        self.setCameraPosition(distance=400, elevation=30, azimuth=45)

    def capture_image(self, filepath: str):
        """Cattura uno screenshot HD della scena 3D."""
        image = self.grabFramebuffer()
        image.save(filepath, "PNG")

    def clear(self):
        self.current_points = []
        self.current_colors = np.empty((0, 4))
        self.scatter.setData(pos=np.empty((0, 3)))