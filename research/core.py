"""Core classes for: triangulations and assembly of finite element matrices
"""

from dataclasses import dataclass
import numpy as np
import triangle as tr


# Two-dimensional Euclidean geometries

@dataclass
class Geometry2D:
    
    vertices: np.array
    faces: np.array
    
    