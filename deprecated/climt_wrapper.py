"""Adapted from https://github.com/CliMT/climt/blob/develop/examples/full_radiation_gcm_energy_balanced.py
""" # 'C:\Users\colem\AppData\Local\Programs\Python\Python37\Scripts'

import sys
sys.path.append(r'C:\Users\colem\AppData\Local\Programs\Python\Python37\Scripts')
sys.path.append(r'C:\Users\colem\AppData\Roaming\Python\Python37\site-packages\climt\_components\simple_physics')

import climt
from sympl import (
    TimeDifferencingWrapper, UpdateFrequencyWrapper,
)
import numpy as np
from datetime import timedelta
import pygame
from matplotlib import cm
hot = cm.get_cmap('hot')

# global display constants


NUM_ROWS = 62
NUM_COLS = 128
NUM_TILES = NUM_ROWS*NUM_COLS
TILE_WIDTH = 5
LOOP_MS = 150  # ms per frame
CURRENT_DRAW = 'alt'


# Set up the climate model

fields_to_store = ['air_temperature', 'air_pressure', 'eastward_wind',
                   'northward_wind', 'air_pressure_on_interface_levels',
                   'surface_pressure', 'upwelling_longwave_flux_in_air',
                   'specific_humidity', 'surface_temperature',
                   'latitude', 'longitude',
                   'convective_heating_rate']

climt.set_constants_from_dict({
    'stellar_irradiance': {'value': 200, 'units': 'W m^-2'}})

model_time_step = timedelta(seconds=600)
# Create components


convection = climt.EmanuelConvection()
simple_physics = TimeDifferencingWrapper(climt.SimplePhysics())

constant_duration = 6

radiation_lw = UpdateFrequencyWrapper(
    climt.RRTMGLongwave(), constant_duration*model_time_step)

radiation_sw = UpdateFrequencyWrapper(
    climt.RRTMGShortwave(), constant_duration*model_time_step)

slab_surface = climt.SlabSurface()

dycore = climt.GFSDynamicalCore(
    [simple_physics, slab_surface, radiation_sw,
     radiation_lw, convection], number_of_damped_levels=5
)
grid = climt.get_grid(nx=NUM_COLS, ny=NUM_ROWS)

# Create model state
my_state = climt.get_default_state([dycore], grid_state=grid)

# Set initial/boundary conditions
latitudes = my_state['latitude'].values
longitudes = my_state['longitude'].values

zenith_angle = np.radians(latitudes)
surface_shape = [len(longitudes), len(latitudes)]

my_state['zenith_angle'].values = zenith_angle
my_state['eastward_wind'].values[:] = np.random.randn(
    *my_state['eastward_wind'].shape)
my_state['ocean_mixed_layer_thickness'].values[:] = 50

surf_temp_profile = 290 - (40*np.sin(zenith_angle)**2)
my_state['surface_temperature'].values = surf_temp_profile

def draw_temperature(screen, state, alpha=0.1):
    """Draw temperature from climt state
    """
    temp_vector = state["surface_temperature"]
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            tile_x = j * TILE_WIDTH
            tile_y = i * TILE_WIDTH
            temp = temp_vector[i * NUM_COLS + j]
            temp_pct = max(0, min(1, temp / 1000))
            if temp_pct >= 1:
                color = (255, 255, 255, alpha)
            else :
                htmp = hot(temp_pct)
                color = (int(255*htmp[0]), int(255*htmp[1]), int(255*htmp[2]), alpha)
                # if temp_pct > 0.1: print(color)
            pygame.draw.rect(screen, color, (tile_x, tile_y, TILE_WIDTH, TILE_WIDTH))
    return

if __name__ == "__main__":
    pygame.init()
    pygame.font.init()

    size = width, height = NUM_COLS*TILE_WIDTH, NUM_ROWS*TILE_WIDTH
    screen = pygame.display.set_mode(size)

    while True:
        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

        draw_temperature(screen, my_state, alpha=0.1)
        pygame.display.flip()