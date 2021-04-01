import sys
import csv
import numpy as np
from time import monotonic, sleep
import pygame
import numba as nb
from scipy import sparse
from matplotlib import cm
hot = cm.get_cmap('hot')

# global constants

NUM_ROWS = 30
NUM_COLS = 2*NUM_ROWS
NUM_TILES = NUM_ROWS*NUM_COLS
TILE_WIDTH = 15
LOOP_MS = 150  # ms per frame
CURRENT_DRAW = 'alt'

# geophysical constants
SOLAR_CONST = 5000
STEFAN_BOLTZMANN = 1.39*10**(-7)

def current_time_millis():
    return round(monotonic() * 1000) 

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in radians)
    """
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 1 # 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def lonlat(i, j):
    return ((i + 0.5) * (np.pi/2)/NUM_ROWS, (j + 0.5) * 2 * np.pi / NUM_COLS)

def transport_vector(lon, lat):
    if lat < np.pi/6: return (-1, -1)
    elif lat < np.pi/3: return (-1, 1)
    elif lat < np.pi/2: return (-1, -1)
    elif lat < 2 * np.pi / 3: return (-1, 1)
    elif lat < 5 * np.pi / 6: return (-1, -1)
    else: return (-1, 1)

def construct_world():
    return

def load_world(filename="world.csv"):
    with open(filename, "r") as f:
        rdr = csv.reader(f, delimiter=",")
        alt_vector = [alt for row in rdr for alt in row]
    return np.array(alt_vector)

def save_world(alt_vector, filename="world.csv"):
    with open(filename, "w+") as f:
        wrt = csv.writer(f, delimiter=",")
        for j in range(NUM_ROWS):
            row_to_write = [alt_vector[j*NUM_COLS + i] for i in range(NUM_COLS)]
            wrt.writerow(row_to_write)
    return

def construct_diffusion_matrix(diffusion_coeff=0.3):
    A = sparse.lil_matrix((NUM_TILES, NUM_TILES))
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            base_idx = i * NUM_COLS + j
            north_idx = (i - 1) * NUM_COLS + j
            south_idx = (i + 1) * NUM_COLS + j
            east_idx = i * NUM_COLS + (j + 1) % NUM_COLS
            west_idx = i * NUM_COLS + (j - 1) % NUM_COLS
            base_lon, base_lat = lonlat(i, j)
            north_lon, north_lat = lonlat(j, i-1)
            south_lon, south_lat = lonlat(j, i+1)
            east_lon, east_lat = lonlat(j+1, i)
            west_lon, west_lat = lonlat(j-1, i)
            tonorth = haversine(base_lon, base_lat, north_lon, north_lat) if i > 0 else 0
            tosouth = haversine(base_lon, base_lat, south_lon, south_lat) if i < NUM_ROWS else 0
            toeast = haversine(base_lon, base_lat, east_lon, east_lat)
            towest = haversine(base_lon, base_lat, west_lon, west_lat)
            if i == 0:
                totaldist = 1/tosouth + 1/toeast + 1/towest
            elif i == NUM_ROWS:
                totaldist = 1/tonorth + 1/toeast + 1/towest
            else:
                totaldist = 1/tonorth + 1/tosouth + 1/toeast + 1/towest
            if i > 0: A[north_idx, base_idx] += diffusion_coeff * (1/tonorth) / totaldist
            if i < NUM_ROWS - 1: A[south_idx, base_idx] += diffusion_coeff * (1/tosouth) / totaldist
            A[east_idx, base_idx] += diffusion_coeff * (1/toeast) / totaldist
            A[west_idx, base_idx] += diffusion_coeff * (1/towest) / totaldist
            A[base_idx, base_idx] = 1 - diffusion_coeff
    for r in range(NUM_TILES):
        A[r, :] = A[r, :]/np.sum(A[r, :])
    return A

def construct_transport_matrix(windspeed=0.2):
    A = sparse.lil_matrix((NUM_TILES, NUM_TILES))
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            base_idx = i * NUM_COLS + j
            north_idx = (i - 1) * NUM_COLS + j
            south_idx = (i + 1) * NUM_COLS + j
            west_idx = i * NUM_COLS + (j - 1) % NUM_COLS
            base_lon, base_lat = lonlat(j, i)
            north_lon, north_lat = lonlat(j, i-1)
            south_lon, south_lat = lonlat(j+1, i)
            west_lon, west_lat = lonlat(j-1, i)
            if ((base_lat < np.pi/6)
                or (base_lat >= np.pi/3 and base_lat < np.pi/2)
                or (base_lat >= 2*np.pi/3 and base_lat < 5*np.pi/6)): # (-1, -1)
                tosouth = 1 / haversine(base_lon, base_lat, south_lon, south_lat) if i < NUM_ROWS-2 else 0
                towest = 1 / haversine(base_lon, base_lat, west_lon, west_lat)
                try:
                    totaldist = tosouth + towest
                    A[west_idx, base_idx] += windspeed * (towest / totaldist)
                    A[south_idx, base_idx] += windspeed * (tosouth / totaldist)
                    A[base_idx, base_idx] = 1 - windspeed
                except ZeroDivisionError:
                    print('ZeroDivisionError')
                    print('base:', base_idx, base_lon, base_lat)
                    print('south:', south_idx, south_lon, south_lat, tosouth)
                    print('west:', west_idx, west_lon, west_lat, towest)
            else: #return (-1, 1)
                tonorth = 1 / haversine(base_lon, base_lat, north_lon, north_lat) if i > 0 else 0
                towest = 1 / haversine(base_lon, base_lat, west_lon, west_lat)
                try:
                    totaldist = tonorth + towest
                    A[west_idx, base_idx] += windspeed * (towest / totaldist)
                    A[north_idx, base_idx] += windspeed * (tonorth / totaldist)
                    A[base_idx, base_idx] = 1 - windspeed
                except ZeroDivisionError:
                    print('ZeroDivisionError')
                    print('base:', base_idx, base_lon, base_lat)
                    print('north:', north_idx, north_lon, north_lat, tonorth)
                    print('west:',west_idx, west_lon, west_lat, towest)
    for r in range(NUM_TILES):
        A[:, r] = A[:, r]/np.sum(A[:, r])
    return A

def construct_insolation_matrix():
    I = sparse.lil_matrix((NUM_TILES, NUM_TILES))
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            base_idx = i * NUM_COLS + j
            lat = lonlat(j, i)[1]
            I[base_idx, base_idx] = SOLAR_CONST * np.sin(lat)
    return I

def construct_rainfall_matrix():
    return

def update_state():
    return

def draw_temperature(screen, temp_vector, alpha=1):
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

def draw_humidity():
    return

def draw_pressure():
    return

def draw_altitude(screen, alt_vector, temp_vector):
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            tile_x = j * TILE_WIDTH
            tile_y = i * TILE_WIDTH
            idx = i * NUM_COLS + j
            alt = alt_vector[idx]
            temp = temp_vector[idx]
            if alt <= 0:    # ocean
                if temp < 280:  # frozen
                    pygame.draw.rect(screen, [245, 245, 245], (tile_x, tile_y, TILE_WIDTH, TILE_WIDTH))
                else:
                    pygame.draw.rect(screen, [135, 206, 235], (tile_x, tile_y, TILE_WIDTH, TILE_WIDTH))
            else:   # land
                alt_pct = 1 - max(0, min(1, alt / 10))
                color = [int(alt_pct * 139), int(alt_pct * 69), int(alt_pct * 19)]
                pygame.draw.rect(screen, color, (tile_x, tile_y, TILE_WIDTH, TILE_WIDTH))
    return

def draw_index(screen, idx, x, y, font):
    text = font.render(str(idx), True, (255, 255, 255))
    textrect = text.get_rect()
    textrect.centerx = x
    textrect.centery = y
    screen.blit(text, textrect)
    return

def draw_indices(screen, font):
    for i in range(NUM_ROWS):
        for j in range(NUM_COLS):
            idx = i * NUM_COLS + j
            tilerect = pygame.Rect(j*TILE_WIDTH, i*TILE_WIDTH, TILE_WIDTH, TILE_WIDTH)
            draw_index(screen, idx, tilerect.centerx, tilerect.centery, font)
    return

@nb.njit(parallel=True)
def albedoize(alt, temp):
    alb = np.empty(len(alt))
    for i in nb.prange(len(alt)):
        if alt[i] <= 0 and temp[i] > 280: alb[i] = 0.96
        elif alt[i] <= 0 and temp[i] <= 280: alb[i] = 0.1
        elif alt[i] > 0: alb[i] = 0.6
    return alb


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    size = width, height = NUM_COLS*TILE_WIDTH, NUM_ROWS*TILE_WIDTH
    screen = pygame.display.set_mode(size)

    print("Initializing font...")
    basicfont = pygame.font.SysFont(None, 20)
    basicfont.set_bold(False)

    running = True

    print('Initializing state vectors...')
    alt_vector = np.zeros(NUM_TILES)
    temp_vector = 280 * np.ones(NUM_TILES)
    sol_vector = construct_insolation_matrix()
    print('State vectors initialized! Initializing diffusion matrix...')
    diffusion_matrix = construct_diffusion_matrix(0.5)
    print('Diffusion matrix initialized! Initializing transprot matrix...')
    transport_matrix = construct_transport_matrix(0.05)
    print('Transport matrix initialized!')


    print('Diffusion matrix:')
    print(diffusion_matrix)
    print('\nTransport matrix:')
    print(transport_matrix)

    while True:
        dt = 0.001
        start_time = current_time_millis()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            elif event.type == pygame.KEYDOWN:
                x, y = pygame.mouse.get_pos()
                coord_x = int(x/TILE_WIDTH)
                coord_y = int(y/TILE_WIDTH)
                if event.key == pygame.K_i: # inspect
                    print("==== INSPECTION ====")
                    print("X, Y:", coord_x, coord_y)
                    base_idx = coord_y * NUM_COLS + coord_x
                    north_idx = (coord_y - 1) * NUM_COLS + coord_x
                    south_idx = (coord_y + 1) * NUM_COLS + coord_x 
                    east_idx = coord_y * NUM_COLS + (coord_x + 1) % NUM_COLS
                    west_idx = coord_y * NUM_COLS + (coord_x - 1) % NUM_COLS
                    draw_index(screen, base_idx, int(coord_x * TILE_WIDTH + TILE_WIDTH/2), int(coord_y * TILE_WIDTH + TILE_WIDTH / 2), basicfont)
                    print(base_idx, north_idx, south_idx, east_idx, west_idx)
                    print("Lon, lat:", lonlat(coord_x, coord_y))
                    try:
                        print("Altitude:", alt_vector[base_idx])
                    except:
                        print('Altitude')
                    try:
                        print("Temperature:", temp_vector[base_idx])
                    except:
                        print('Temperature')
                    try:
                        if coord_y > 0: print("Diffusion north:", diffusion_matrix[north_idx, base_idx])
                    except:
                        print('Diffusion north')
                    try:
                        if coord_y < NUM_COLS - 2: print("Diffusion south:", diffusion_matrix[south_idx, base_idx])
                    except:
                        print('Diffusion south', coord_y, NUM_COLS)
                    try:
                        print("Diffusion east:", diffusion_matrix[east_idx, base_idx])
                        print("Diffusion west:", diffusion_matrix[west_idx, base_idx])
                    except:
                        print('Diffusion east/west')
                    try:
                        if coord_y > 0: print("Transport north:", transport_matrix[north_idx, base_idx])
                    except:
                        print('Transport north')
                    try:
                        if coord_y < NUM_COLS - 2: print("Transport south:", transport_matrix[south_idx, base_idx])
                    except:
                        print('Transport south')
                    try:
                        print("Transport east:", transport_matrix[east_idx, base_idx])
                        print("Transport west:", transport_matrix[west_idx, base_idx])
                    except:
                        print('Transport east/west')
                if event.key == pygame.K_u: # land up
                    current_alt = alt_vector[coord_y * NUM_COLS + coord_x]
                    if current_alt < 10: alt_vector[coord_y * NUM_COLS + coord_x] += 1
                if event.key == pygame.K_d: # land down
                    current_alt = alt_vector[coord_y * NUM_COLS + coord_x]
                    if current_alt > -10: alt_vector[coord_y * NUM_COLS + coord_x] -= 1
                if event.key == pygame.K_h: # temperature injection
                    temp_vector[coord_y * NUM_COLS + coord_x] += 750
                if event.key == pygame.K_c: # temperature injection
                    temp_vector[coord_y * NUM_COLS + coord_x] = 0
                if event.key == pygame.K_r: # reset temperature
                    temp_vector = np.ones(NUM_TILES)
                if event.key == pygame.K_1: # draw altitude
                    CURRENT_DRAW = 'alt'
                if event.key == pygame.K_2: # draw temperature
                    CURRENT_DRAW = 'temp'

                if event.key == pygame.K_p: # pause
                    running = not running
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                coord_x = int(x/TILE_WIDTH)
                coord_y = int(y/TILE_WIDTH)
                if event.button == 1:
                    alt_vector[coord_y * NUM_COLS + coord_x] += 1
                else:
                    alt_vector[coord_y * NUM_COLS + coord_x] -= 1
        if running:
            mean_temp = np.mean(temp_vector)
            print(mean_temp)
            albedo_vector = albedoize(alt_vector, temp_vector)
            temp_vector = temp_vector + dt * (albedo_vector * sol_vector - np.maximum(STEFAN_BOLTZMANN * temp_vector**4, np.zeros(NUM_TILES)))
            temp_vector = diffusion_matrix.dot(temp_vector)
            temp_vector = transport_matrix.dot(temp_vector)
            if CURRENT_DRAW == 'temp':
                draw_temperature(screen, temp_vector, alpha=0.1)
            else:
                draw_altitude(screen, alt_vector, temp_vector)
            # draw_indices(screen, basicfont)
            pygame.display.flip()
        end_time = current_time_millis()
        duration = end_time - start_time
        time_left = max(0, LOOP_MS - duration)
        sleep(time_left / 1000)
