import pyqtgraph.opengl as gl
import numpy as np

class PointCloudView(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCameraPosition(distance=400, elevation=30, azimuth=45)
        
        # Griglia di riferimento XY
        grid = gl.GLGridItem()
        grid.scale(20, 20, 1)
        grid.setDepthValue(10)
        self.addItem(grid)

        # Plot per la Nuvola di Punti
        self.scatter = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=(0.1, 0.8, 1.0, 0.8),
            size=3.0,
            pxMode=True
        )
        self.addItem(self.scatter)

    def update_cloud(self, points: list):
        if not points:
            return
        pts_np = np.array(points, dtype=np.float32)
        
        # Colorazione per quota Z
        z_vals = pts_np[:, 2]
        z_norm = (z_vals - z_vals.min()) / (z_vals.max() - z_vals.min() + 1e-5)
        colors = np.zeros((len(pts_np), 4), dtype=np.float32)
        colors[:, 0] = z_norm          # Canale Rosso (alto)
        colors[:, 1] = 1.0 - z_norm    # Canale Verde (basso)
        colors[:, 2] = 0.8
        colors[:, 3] = 0.85

        self.scatter.setData(pos=pts_np, color=colors)

    def clear(self):
        self.scatter.setData(pos=np.empty((0, 3)))