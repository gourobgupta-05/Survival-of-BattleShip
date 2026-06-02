from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math
import time
import random

# Camera and Window Settings
camera_pos = (0, 1000, 1000)
camera_distance = 1000
camera_angle = 0
first_person_view = False
first_person_height = 50

GRID_LENGTH = 800
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 1000
fovY = 100

# Game State
score = 0               
keys_pressed = set()   # Keeps track of which keys are currently being held down

# Player Ship Stats
ship_x = 0
ship_y = 0
ship_z = 50        # Height above the water
ship_rotation = 0    # Which way the ship is facing (in degrees)
ship_speed = 0
sail_state = 0   # 0 = No Sail, 1 = Half Sail, 2 = Full Sail

# Enemy Ship System
enemies = []  
max_enemies = 10
enemy_health = 50  
enemy_speed = 6 
enemy_attack_range = 600  
enemy_optimal_distance = 400  
enemy_fire_cooldown = 1.5
enemy_spawn_interval = 12
last_enemy_spawn_time = time.time()

# Weather & Environment
rain_drops = []
rain_initialized = False
storm_active = False
storm_start_time = 0
storm_duration = 8
game_start_time = time.time() 
last_storm_end_time = 0
time_until_first_storm = 8

# Cannon System
cannonballs = []
fire_cooldown = 0.6
cannonball_speed = 22
cannonball_size = 8
last_fire_time_left = 0   
last_fire_time_right = 0
cannonball_max_distance = 1000

# Health & Sinking Mechanics
ship_health = 100
max_health = 100
last_damage_time = 0
sinking_speed = 0.8
target_sink_depth = -40
ship_sinking = False

# Wave Hazard System
wave_active = False
wave_x = 0  
wave_y = 0  
wave_z = 0  
wave_direction_x = 0
wave_direction_y = 1  
wave_speed = 15 
wave_spawn_distance= 2000  
wave_damage= 15  
last_wave_damage_time = 0
wave_height = 180
wave_width = 1500 
wave_damage_cooldown = 0.4 
wave_front_curve_factor = 250
wave_attack_arc_degrees = 75
wave_pass_distance = 200
wave_impact_zone_radius = 160
wave_safe_angle_threshold = 35

# Aiming Indicators (Q & E)
aiming_right = False  
aiming_left = False 

# Toggles and Cycles
is_night = False
day_night_cycle_interval = 20
last_day_night_switch_time = time.time()
rain_enabled = True
cheat_mode = False     # Auto-steer mode

# Ship Geometry Constants
bow_back_x = 150
bow_tip_x = 200
bow_width = 60
bow_height = 40
cannon_positions= [80, 30, -20, -70]
cannon_length = 30
cannon_offset = 90

SPEED_NO_SAIL = 0
TURN_SPEED = 2.2
SPEED_HALF_SAIL = 7
SPEED_FULL_SAIL = 14
COLLISION_FATAL_RADIUS = 110

#weather, rain, ocean

def initialize_rain():
    # Generates random raindrops around the world
    global rain_drops, rain_initialized
    rain_drops = []
    for i in range(300):
        x = random.uniform(-1000, 1000)
        y = random.uniform(-1000, 1000)
        z = random.uniform(100, 500)  
        rain_drops.append([x, y, z])
    rain_initialized = True

def draw_rain():
    if not rain_initialized: return
    glColor3f(0.7, 0.7, 0.8)  
    glBegin(GL_LINES)
    for drop in rain_drops:
        glVertex3f(drop[0], drop[1], drop[2])
        glVertex3f(drop[0], drop[1], drop[2] - 22)  
    glEnd()

def update_rain():
    # Makes the rain fall, and resets drops that hit the ocean
    global rain_drops
    if not rain_initialized: return
    for drop in rain_drops:
        drop[2] -= 7
        if drop[2] < 0:
            drop[2] = random.uniform(300, 400) 
            drop[0] = ship_x + random.uniform(-1000, 1000)
            drop[1] = ship_y + random.uniform(-1000, 1000)

def draw_ocean():
    # Draws the ocean grid. Uses sine waves and time to create moving colors
    glPushMatrix()
    t = time.time()
    tile_size = 100
    tiles = 30
    ship_tile_x = int(ship_x / tile_size)
    ship_tile_y = int(ship_y / tile_size)

    if storm_active:
        base_r, base_g, base_b, var = 0.04, 0.12, 0.22, 0.025
    elif is_night:
        base_r, base_g, base_b, var = 0.02, 0.06, 0.18, 0.018
    else:
        base_r, base_g, base_b, var = 0.0, 0.40, 0.70, 0.055

    def get_wave_color(wx, wy):
        w = (math.sin(wx * 0.007 + t * 0.50) * 0.50 
           + math.cos(wy * 0.006 - t * 0.40) * 0.30 
           + math.sin((wx + wy) * 0.004 + t * 0.30) * 0.20) * var
           
        r = max(0.0, min(1.0, base_r + w * 0.30))
        g = max(0.0, min(1.0, base_g + w))
        b = max(0.0, min(1.0, base_b + w * 0.60))
        return (r, g, b)

    for i in range(ship_tile_x - tiles, ship_tile_x + tiles):
        for j in range(ship_tile_y - tiles, ship_tile_y + tiles):
            x1 = i * tile_size
            y1 = j * tile_size
            x2 = x1 + tile_size
            y2 = y1 + tile_size

            c1 = get_wave_color(x1, y1)
            c2 = get_wave_color(x2, y1)
            c3 = get_wave_color(x2, y2)
            c4 = get_wave_color(x1, y2)

            glBegin(GL_QUADS)
            glColor3f(*c1)
            glVertex3f(x1, y1, 0)
            glColor3f(*c2)
            glVertex3f(x2, y1, 0)
            glColor3f(*c3)
            glVertex3f(x2, y2, 0)
            glColor3f(*c4)
            glVertex3f(x1, y2, 0)
            glEnd()
            
    glPopMatrix()
    draw_ocean_foam()

def draw_ocean_foam():
    # Draws white speed streaks on the water that the ship sails past
    t = time.time()
    glLineWidth(1.2)
    
    grid_center_x = (int(ship_x / 800) * 800)
    grid_center_y = (int(ship_y / 800) * 800)
    
    for k in range(50):
        ang = k * 2.399963  
        dist = 120 + (k % 8) * 150 
        
        fx = grid_center_x + math.cos(ang) * dist + math.sin(t * 0.5 + k) * 30
        fy = grid_center_y + math.sin(ang) * dist + math.cos(t * 0.5 + k) * 30

        streak_ang = ang * 1.618 + t * 0.12
        length = 22 + math.sin(t * 0.65 + k * 0.45) * 14
        alpha = 0.55 + math.sin(t * 0.45 + k * 0.28) * 0.30
        
        glColor3f(alpha, alpha, alpha)
        ex = fx + math.cos(streak_ang) * length
        ey = fy + math.sin(streak_ang) * length
        
        glBegin(GL_LINES)
        glVertex3f(fx, fy, 1)
        glVertex3f(ex, ey, 1)
        glEnd()
        
    glLineWidth(1.0)




def draw_enemy_ship(enemy):
    """Draws an enemy ship. Just wraps the standard draw_ship with evil colors."""
    draw_ship(
        x=enemy['x'], 
        y=enemy['y'], 
        z=enemy['z'], 
        rotation=enemy['rotation'],
        hull_color=(0.7, 0.2, 0.2), 
        bow_color=(0.6, 0.3, 0.3),
        sail_color=(0.7, 0.8, 0.8),
        num_masts=1,                
        sail_state_override=2       
    )

def draw_wave():
    """Draws the deadly rogue wave that spawns after storms."""
    if not wave_active: return
    
    glPushMatrix()
    glTranslatef(wave_x, wave_y, 0)
    
    # Rotate the wave to face its travel direction
    angle = math.degrees(math.atan2(wave_direction_y, wave_direction_x))
    glRotatef(angle, 0, 0, 1)
    
    # Draw the body of the wave
    glColor3f(0.1, 0.4, 0.7)
    glBegin(GL_QUADS)
    glVertex3f(-40, -wave_width / 2, 0)
    glVertex3f(20, -wave_width / 2, wave_height * 0.7)
    glVertex3f(20, wave_width / 2, wave_height * 0.7)
    glVertex3f(-40, wave_width / 2, 0)
    glEnd()
    
    # Draw the white foamy crest at the top
    glColor3f(0.85, 0.9, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(20, -wave_width / 2, wave_height * 0.7)
    glVertex3f(40, -wave_width / 2, wave_height)
    glVertex3f(40, wave_width / 2, wave_height)
    glVertex3f(20, wave_width / 2, wave_height * 0.7)
    glEnd()
    
    glPopMatrix()
def draw_cannonball(ball):
    glPushMatrix()
    glTranslatef(ball['pos'][0], ball['pos'][1], ball['pos'][2])
    glColor3f(0, 0.8, 0.5)  
    glutSolidSphere(cannonball_size, 10, 10)
    glPopMatrix()    

def draw_range_indicator(direction): 
    #Draws a green laser line to help aim cannons (triggered by Q or E)
    rad = math.radians(ship_rotation)
    right_x = math.sin(rad)
    right_y = -math.cos(rad)
    
    if direction == 'left':
        dir_x, dir_y = -right_x, -right_y
    else:
        dir_x, dir_y = right_x, right_y

    start_x = ship_x
    start_y = ship_y
    start_z = ship_z + 35  
    end_x = start_x + dir_x * cannonball_max_distance
    end_y = start_y + dir_y * cannonball_max_distance
    end_z = start_z
    
    glColor3f(0, 1, 0) 
    glLineWidth(2)
    glBegin(GL_LINES)
    glVertex3f(start_x, start_y, start_z)
    glVertex3f(end_x, end_y, end_z)
    glEnd()
    glLineWidth(1.0)
    
    arrow_size = 30
    perp_x, perp_y = -dir_y, dir_x
    
    glBegin(GL_TRIANGLES)
    glVertex3f(end_x, end_y, end_z)
    glVertex3f(end_x - dir_x * arrow_size + perp_x * arrow_size * 0.4, 
               end_y - dir_y * arrow_size + perp_y * arrow_size * 0.4, end_z)
    glVertex3f(end_x - dir_x * arrow_size - perp_x * arrow_size * 0.4, 
               end_y - dir_y * arrow_size - perp_y * arrow_size * 0.4, end_z)
    glEnd()

def draw_ship(x=None, y=None, z=None, rotation=None, hull_color=(0.6, 0.7, 0.2), bow_color=(0.3, 0.6, 0.5), sail_color=(0.5, 0.7, 0.9), num_masts=2, sail_state_override=None):
    # The main drawing routine for all ships. Builds the hull, decks, masts, and cannons
    
    x = ship_x if x is None else x
    y = ship_y if y is None else y
    z = ship_z if z is None else z
    rotation = ship_rotation if rotation is None else rotation
    current_sail_state = sail_state if sail_state_override is None else sail_state_override
    
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(rotation, 0, 0, 1)
    
    # 1. Main Hull
    glColor3f(*hull_color)
    glPushMatrix()
    glScalef(4.6, 2.0, 1.2)
    glutSolidCube(70)
    glPopMatrix()

    # 2. Deck Railings
    glColor3f(0.2, 0.15, 0.1)
    glLineWidth(3)
    for side in [-70, 70]:
        glBegin(GL_LINES)
        glVertex3f(-140, side, 44)
        glVertex3f(140, side, 44)
        glEnd()
    glLineWidth(1)

    # 3. Rear Deckhouse (Stern Tower)
    glColor3f(0.12, 0.15, 0.38)
    glPushMatrix()
    glTranslatef(-120, 0, 55)
    glScalef(0.9, 0.7, 1.0)
    glutSolidCube(60)
    glPopMatrix()

    # 4. Central Raised Deck
    glColor3f(0.2, 0.25, 0.5)
    glPushMatrix()
    glTranslatef(-10, 0, 40)
    glScalef(1.4, 0.9, 0.8)
    glutSolidCube(70)
    glPopMatrix()

    # 5. Pointy Bow
    glColor3f(*bow_color)
    glBegin(GL_TRIANGLES)
    glVertex3f(bow_tip_x, 0, -bow_height)
    glVertex3f(bow_back_x, -bow_width, -bow_height)
    glVertex3f(bow_back_x, bow_width, -bow_height)
    
    glVertex3f(bow_tip_x, 0, bow_height)
    glVertex3f(bow_back_x, bow_width, bow_height)
    glVertex3f(bow_back_x, -bow_width, bow_height)
    
    glVertex3f(bow_tip_x, 0, -bow_height)
    glVertex3f(bow_tip_x, 0, bow_height)
    glVertex3f(bow_back_x, -bow_width, bow_height)
    
    glVertex3f(bow_tip_x, 0, -bow_height)
    glVertex3f(bow_back_x, -bow_width, bow_height)
    glVertex3f(bow_back_x, -bow_width, -bow_height)
    
    glVertex3f(bow_tip_x, 0, -bow_height)
    glVertex3f(bow_back_x, bow_width, -bow_height)
    glVertex3f(bow_back_x, bow_width, bow_height)
    
    glVertex3f(bow_tip_x, 0, -bow_height)
    glVertex3f(bow_back_x, bow_width, bow_height)
    glVertex3f(bow_tip_x, 0, bow_height)
    glEnd()
    
    glBegin(GL_QUADS)
    glVertex3f(bow_back_x, -bow_width, -bow_height)
    glVertex3f(bow_back_x, -bow_width, bow_height)
    glVertex3f(bow_back_x, bow_width, bow_height)
    glVertex3f(bow_back_x, bow_width, -bow_height)
    glEnd()
    
    # 6. Masts and Sails
    glColor3f(0.3, 0.3, 0.3)
    positions = [0] if num_masts == 1 else [70, -70]
    
    for mx in positions:
        glPushMatrix()
        glTranslatef(mx, 0, 35)
        gluCylinder(gluNewQuadric(), 6, 6, 150, 10, 10)
        
        glPushMatrix()
        glTranslatef(0, 0, 105)
        glRotatef(90, 1, 0, 0)
        glTranslatef(0, 0, -55)
        gluCylinder(gluNewQuadric(), 3, 3, 110, 8, 8)
        glPopMatrix()
        
        glPopMatrix()
    
    if current_sail_state > 0 or sail_state_override is not None:
        glColor3f(*sail_color)
        sail_width = 42 if current_sail_state == 1 else 60
        sail_height = 48 if current_sail_state == 1 else 75
        
        for mx in positions:
            glPushMatrix()
            glTranslatef(mx, 0, 90)
            glRotatef(90, 0, 0, 1)
            glBegin(GL_QUADS)
            glVertex3f(-sail_width, 0, sail_height)
            glVertex3f(sail_width, 0, sail_height)
            glVertex3f(sail_width, 0, 0)
            glVertex3f(-sail_width, 0, 0)
            glEnd()
            glPopMatrix()
    
    # 7. Cannons
    glColor3f(0.2, 0.2, 0.2)
    for x_pos in cannon_positions:
        glPushMatrix()
        glTranslatef(x_pos, cannon_offset, 10)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 4, 4, cannon_length, 8, 8)
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(x_pos, -cannon_offset, 10)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 4, 4, cannon_length, 8, 8)
        glPopMatrix()
    
    glPopMatrix()


#Game movements
def spawn_enemy(): 
    angle = random.uniform(0, 360)
    distance = random.uniform(1500, 2000)
    rad = math.radians(angle)
    
    enemies.append({
        'x': ship_x + distance * math.cos(rad),
        'y': ship_y + distance * math.sin(rad),
        'z': 50,
        'rotation': 0,
        'health': enemy_health,
        'last_fire_time': 0,
        'sinking': False,
        'sink_depth': 50
    })

def update_enemy_spawning():
    global last_enemy_spawn_time
    current_time = time.time()
    
    if len(enemies) >= max_enemies:
        return
        
    if current_time - last_enemy_spawn_time >= enemy_spawn_interval:
        spawn_enemy()
        last_enemy_spawn_time = current_time


def update_cheat_movement():
    global ship_rotation, sail_state

    if ship_sinking: return

    active_enemies = [e for e in enemies if not e['sinking']]
    if not active_enemies:
        sail_state = 1          
        return

    target = min(active_enemies, key=lambda e: (e['x'] - ship_x) ** 2 + (e['y'] - ship_y) ** 2)

    dx = target['x'] - ship_x
    dy = target['y'] - ship_y
    distance = math.sqrt(dx * dx + dy * dy)
    angle_to_enemy = math.degrees(math.atan2(dy, dx))
    
    if distance > enemy_attack_range:
        target_angle = angle_to_enemy
        sail_state = 2
    else:
        rel = (angle_to_enemy - ship_rotation + 540) % 360 - 180 
        to_left  = (rel - 90 + 540) % 360 - 180
        to_right = (rel + 90 + 540) % 360 - 180
        
        if abs(to_left) < abs(to_right):
            target_angle = angle_to_enemy - 90
        else:
            target_angle = angle_to_enemy + 90
            
        if distance > enemy_optimal_distance + 50: 
            sail_state = 2       
        elif distance < enemy_optimal_distance - 50: 
            sail_state = 0       
        else: 
            sail_state = 1

    angle_diff = (target_angle - ship_rotation + 540) % 360 - 180
    if abs(angle_diff) > TURN_SPEED:
        if angle_diff > 0: 
            ship_rotation = (ship_rotation + TURN_SPEED) % 360
        else: 
            ship_rotation = (ship_rotation - TURN_SPEED) % 360
        
    if distance <= enemy_attack_range:
        rad = math.radians(ship_rotation)
        right_x = math.sin(rad)
        right_y = -math.cos(rad)
        
        dot = dx * right_x + dy * right_y
        dir_x = dx / distance
        dir_y = dy / distance
        
        side_alignment = abs(dir_x * right_x + dir_y * right_y)
        
        if side_alignment > 0.8: 
            if dot > 0:
                fire_side_cannons('right')
            else:
                fire_side_cannons('left')


def update_enemy_ai():
    global ship_health, ship_sinking
    enemies_to_remove = []
    
    for enemy in enemies:
        if enemy['sinking']:
            if enemy['sink_depth'] > -35: 
                enemy['sink_depth'] -= 0.5
                enemy['z'] = enemy['sink_depth']
            else:
                enemies_to_remove.append(enemy)
            continue
        
        dx = ship_x - enemy['x']
        dy = ship_y - enemy['y']
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= COLLISION_FATAL_RADIUS and not ship_sinking:
            ship_health = 0
            ship_sinking = True
            break
        
        if distance < 1: continue
        
        dir_x = dx / distance
        dir_y = dy / distance
        angle_to_player = math.degrees(math.atan2(dy, dx))
        
        if distance > enemy_optimal_distance + 50: 
            enemy['x'] += dir_x * enemy_speed
            enemy['y'] += dir_y * enemy_speed           
            enemy['rotation'] = angle_to_player         
        elif distance < enemy_optimal_distance - 50:    
            enemy['x'] -= dir_x * enemy_speed
            enemy['y'] -= dir_y * enemy_speed
            enemy['rotation'] = angle_to_player + 180   
        else:
            enemy['rotation'] = angle_to_player + 90
            perp_x = -dir_y
            perp_y = dir_x
            enemy['x'] += perp_x * enemy_speed * 0.3
            enemy['y'] += perp_y * enemy_speed * 0.3
        
        if distance <= enemy_attack_range:
            fire_enemy_cannons(enemy)
    
    for enemy in enemies_to_remove:
        if enemy in enemies: 
            enemies.remove(enemy)


def fire_enemy_cannons(enemy):
    current_time = time.time()
    
    if current_time - enemy['last_fire_time'] < enemy_fire_cooldown:
        return

    dx = ship_x - enemy['x']
    dy = ship_y - enemy['y']
    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 1: return

    dir_x = dx / distance
    dir_y = dy / distance

    rad = math.radians(enemy['rotation'])
    forward_x = math.cos(rad)
    forward_y = math.sin(rad)
    right_x = math.sin(rad)
    right_y = -math.cos(rad)

    side_alignment = abs(dir_x * right_x + dir_y * right_y)
    if side_alignment < 0.65:
        return 

    enemy['last_fire_time'] = current_time
    dot = dx * right_x + dy * right_y

    if dot > 0:
        fire_dir = [right_x, right_y, 0.0]
        for x_pos in [80, 30, -20, -70]:
            cannonballs.append({
                'pos': [enemy['x'] + x_pos * forward_x + 70 * right_x, enemy['y'] + x_pos * forward_y + 70 * right_y, enemy['z'] + 10],
                'dir': fire_dir,
                'travelled': 0.0,
                'enemy_shot': True
            })
    else:
        fire_dir = [-right_x, -right_y, 0.0]
        for x_pos in [80, 30, -20, -70]:
            cannonballs.append({
                'pos': [enemy['x'] + x_pos * forward_x - 70 * right_x, enemy['y'] + x_pos * forward_y - 70 * right_y, enemy['z'] + 10],
                'dir': fire_dir,
                'travelled': 0.0,
                'enemy_shot': True
            })


def fire_side_cannons(side):
    global last_fire_time_left, last_fire_time_right
    current_time = time.time()
    
    if ship_sinking: return
    
    rad = math.radians(ship_rotation)
    forward_x = math.cos(rad)
    forward_y = math.sin(rad)
    right_x = math.sin(rad)
    right_y = -math.cos(rad)
    
    if side == 'left':
        if current_time - last_fire_time_left < fire_cooldown: 
            return
        last_fire_time_left = current_time
        
        for x_pos in cannon_positions:
            cannonballs.append({
                'pos': [ship_x + x_pos * forward_x - cannon_offset * right_x, ship_y + x_pos * forward_y - cannon_offset * right_y, ship_z + 10], 
                'dir': [-right_x, -right_y, 0.0], 
                'travelled': 0.0, 
                'enemy_shot': False
            })
            
    elif side == 'right':
        if current_time - last_fire_time_right < fire_cooldown: 
            return
        last_fire_time_right = current_time
        
        for x_pos in cannon_positions:
            cannonballs.append({
                'pos': [ship_x + x_pos * forward_x + cannon_offset * right_x, ship_y + x_pos * forward_y + cannon_offset * right_y, ship_z + 10], 
                'dir': [right_x, right_y, 0.0], 
                'travelled': 0.0, 
                'enemy_shot': False
            })


def check_cannonball_hits():
    global ship_health, ship_sinking, score
    
    balls_to_remove = []
    
    for ball in cannonballs:
        if not ball.get('enemy_shot', False):
            for enemy in enemies:
                if enemy['sinking']: continue
                
                dist = math.sqrt((ball['pos'][0]-enemy['x'])**2 + (ball['pos'][1]-enemy['y'])**2 + (ball['pos'][2]-enemy['z'])**2)
                
                if dist < 80:  
                    enemy['health'] -= 10
                    balls_to_remove.append(ball)
                    
                    if enemy['health'] <= 0:
                        enemy['sinking'] = True
                        score += 100
                    break
        else:
            if not ship_sinking:
                dist = math.sqrt((ball['pos'][0]-ship_x)**2 + (ball['pos'][1]-ship_y)**2 + (ball['pos'][2]-ship_z)**2)
                
                if dist < 100:  
                    ship_health -= 10
                    balls_to_remove.append(ball)
                    if ship_health <= 0:
                        ship_health = 0
                        ship_sinking = True
                    break
    
    for ball in balls_to_remove:
        if ball in cannonballs: 
            cannonballs.remove(ball)


def update_cannonballs():
    global cannonballs
    balls_to_remove = []
    
    for ball in cannonballs:
        ball['pos'][0] += ball['dir'][0] * cannonball_speed
        ball['pos'][1] += ball['dir'][1] * cannonball_speed
        ball['pos'][2] += ball['dir'][2] * cannonball_speed
        ball['travelled'] += cannonball_speed
        
        if ball['travelled'] >= cannonball_max_distance:
            balls_to_remove.append(ball)
            
    for ball in balls_to_remove:
        if ball in cannonballs: 
            cannonballs.remove(ball)


def update_ship_movement():
    global ship_x, ship_y, ship_speed
    
    if ship_sinking:
        ship_speed = 0
        return
        
    if sail_state == 0: 
        ship_speed = SPEED_NO_SAIL
    elif sail_state == 1: 
        ship_speed = SPEED_HALF_SAIL
    else: 
        ship_speed = SPEED_FULL_SAIL
    
    if ship_speed > 0:
        rad = math.radians(ship_rotation)
        ship_x += ship_speed * math.cos(rad)
        ship_y += ship_speed * math.sin(rad)


# 5.Inputs

def normalize_key(key):
    if isinstance(key, bytes): 
        return key.lower()
    if isinstance(key, str): 
        return key.encode().lower()
    return key

def keyboard_up(key, x, y):
    key_lower = normalize_key(key)
    
    if key_lower in keys_pressed: 
        keys_pressed.remove(key_lower)
        
    global aiming_left, aiming_right
    if key_lower == b'q': aiming_left = False
    elif key_lower == b'e': aiming_right = False

def keyboard_down(key, x, y):
    key_lower = normalize_key(key)
    keys_pressed.add(key_lower)
    
    global aiming_left, aiming_right
    if key_lower == b'q': aiming_left = True
    elif key_lower == b'e': aiming_right = True
    elif key_lower == b'j': fire_side_cannons('left')
    elif key_lower == b'l': fire_side_cannons('right')
    
    keyboardListener(key_lower, x, y)

def keyboardListener(key_lower, x, y):
    global sail_state, first_person_view, cheat_mode, rain_enabled, is_night, last_day_night_switch_time
    
    if ship_sinking:
        if key_lower == b'r': reset_game()
        return
    
    if key_lower == b'w' and sail_state < 2: sail_state += 1
    if key_lower == b's' and sail_state > 0: sail_state -= 1
    if key_lower == b'r': reset_game()
    if key_lower == b'v': first_person_view = not first_person_view
    if key_lower == b'c': cheat_mode = not cheat_mode
    if key_lower == b't': rain_enabled = not rain_enabled
    if key_lower == b'n': 
        is_night = not is_night
        last_day_night_switch_time = time.time()
    if key_lower == b'\x1b': 
        glutLeaveMainLoop() 

def update_continuous_keys():
    global ship_rotation
    
    if ship_sinking or ship_speed <= 0: 
        return
        
    if b'a' in keys_pressed:
        ship_rotation = (ship_rotation + TURN_SPEED) % 360
    if b'd' in keys_pressed:
        ship_rotation = (ship_rotation - TURN_SPEED) % 360


def specialKeyListener(key, x, y):
    global camera_distance, camera_angle, first_person_height
    
    if first_person_view:
        if key == GLUT_KEY_UP: first_person_height = min(60, first_person_height + 2)
        if key == GLUT_KEY_DOWN: first_person_height = max(28, first_person_height - 2)
        if key == GLUT_KEY_LEFT: camera_angle += 4
        if key == GLUT_KEY_RIGHT: camera_angle -= 4
    else:
        if key == GLUT_KEY_UP: camera_distance = max(200, camera_distance - 20)
        if key == GLUT_KEY_DOWN: camera_distance = min(1000, camera_distance + 20)
        if key == GLUT_KEY_LEFT: camera_angle += 5
        if key == GLUT_KEY_RIGHT: camera_angle -= 5

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 10000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    if first_person_view:
        view_rad = math.radians(ship_rotation + camera_angle)
        cam_x = ship_x + math.cos(view_rad) * 75
        cam_y = ship_y + math.sin(view_rad) * 75
        cam_z = ship_z + first_person_height
        
        look_x = cam_x + math.cos(view_rad) * 300
        look_y = cam_y + math.sin(view_rad) * 300
        look_z = ship_z + first_person_height - 4
        
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, look_z, 0, 0, 1)
    else:
        cam_angle_rad = math.radians(ship_rotation + camera_angle)
        cam_x = ship_x - camera_distance * math.cos(cam_angle_rad)
        cam_y = ship_y - camera_distance * math.sin(cam_angle_rad)
        cam_z = camera_distance * 0.4  
        
        gluLookAt(cam_x, cam_y, cam_z, ship_x, ship_y, ship_z, 0, 0, 1)

def mouseListener(button, state, x, y):
    pass 


# 6. Stroms and waves

def update_day_night_cycle(): 
    global is_night, last_day_night_switch_time
    current_time = time.time()
    if current_time - last_day_night_switch_time >= day_night_cycle_interval:
        is_night = not is_night
        last_day_night_switch_time = current_time

def start_storm():
    global storm_active, storm_start_time, rain_initialized
    storm_active = True
    storm_start_time = time.time()
    rain_initialized = False  
    initialize_rain()

def update_storm_system():
    global storm_active, storm_start_time, last_storm_end_time, rain_initialized, game_start_time
    current_time = time.time()
    elapsed_game_time = current_time - game_start_time
    
    if not storm_active:
        if elapsed_game_time >= time_until_first_storm and last_storm_end_time == 0: 
            start_storm()
        elif last_storm_end_time > 0 and (current_time - last_storm_end_time) >= 20: 
            start_storm()
    else:
        if (current_time - storm_start_time) >= storm_duration: 
            end_storm()

def end_storm():
    global storm_active, last_storm_end_time, rain_initialized, wave_active, wave_x, wave_y, wave_direction_x, wave_direction_y
    storm_active = False
    last_storm_end_time = time.time()
    rain_initialized = False
    
    spawn_wave()
    spawn_enemy()
    spawn_enemy()

def apply_storm_damage():
    global ship_health, last_damage_time, ship_sinking
    
    if not storm_active or ship_sinking: return
    
    current_time = time.time()
    if current_time - last_damage_time >= 1.0:
        if sail_state == 2: 
            ship_health -= 5
        elif sail_state == 1: 
            ship_health -= 2
            
        last_damage_time = current_time
        
        if ship_health <= 0:
            ship_health = 0
            ship_sinking = True

def spawn_wave():
    global wave_active, wave_x, wave_y, wave_direction_x, wave_direction_y
    
    ship_rad = math.radians(ship_rotation)
    attack_angle = ship_rad + math.radians(random.uniform(-wave_attack_arc_degrees, wave_attack_arc_degrees))
    spawn_dir_x = math.cos(attack_angle)
    spawn_dir_y = math.sin(attack_angle)
    
    wave_x = ship_x + spawn_dir_x * wave_spawn_distance
    wave_y = ship_y + spawn_dir_y * wave_spawn_distance
    wave_direction_x = -spawn_dir_x
    wave_direction_y = -spawn_dir_y
    wave_active = True

def update_wave():
    global wave_active, wave_x, wave_y, ship_health, last_wave_damage_time
    
    if not wave_active: return
    
    wave_x += wave_direction_x * wave_speed
    wave_y += wave_direction_y * wave_speed
    check_wave_collision()
    
    if math.sqrt((wave_x - ship_x)**2 + (wave_y - ship_y)**2) < wave_pass_distance: 
        wave_active = False

def check_wave_collision():
    global ship_health, last_wave_damage_time, wave_active
    
    if not wave_active: return
    
    dist_to_wave = math.sqrt((wave_x - ship_x)**2 + (wave_y - ship_y)**2)
    
    if dist_to_wave < wave_impact_zone_radius:  
        ship_forward_x = math.cos(math.radians(ship_rotation))
        ship_forward_y = math.sin(math.radians(ship_rotation))
        
        wave_mag = math.sqrt(wave_direction_x**2 + wave_direction_y**2)
        if wave_mag == 0: return
        
        norm_wave_dir_x = wave_direction_x / wave_mag
        norm_wave_dir_y = wave_direction_y / wave_mag
        
        dot_prod = ship_forward_x * norm_wave_dir_x + ship_forward_y * norm_wave_dir_y
        angle_deg = math.degrees(math.acos(max(-1, min(1, dot_prod))))
        
        if angle_deg > wave_safe_angle_threshold:
            current_time = time.time()
            if current_time - last_wave_damage_time >= wave_damage_cooldown:
                ship_health -= wave_damage
                last_wave_damage_time = current_time


def update_sinking():
    global ship_z, ship_speed
    if not ship_sinking: return
    ship_speed = 0
    if ship_z > target_sink_depth:
        ship_z -= sinking_speed
        if ship_z < target_sink_depth: 
            ship_z = target_sink_depth



def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
        
    glPopMatrix()
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    
    glMatrixMode(GL_MODELVIEW)

def reset_game():
    global ship_x, ship_y, ship_z, ship_rotation, ship_speed, sail_state, score
    global storm_active, storm_start_time, last_storm_end_time, game_start_time
    global ship_health, last_damage_time, rain_initialized, ship_sinking
    global cannonballs, last_fire_time_left, last_fire_time_right, wave_active, last_wave_damage_time, enemies
    global is_night, last_day_night_switch_time, last_enemy_spawn_time, rain_enabled, cheat_mode, keys_pressed
    
    ship_x, ship_y, ship_z, ship_rotation, ship_speed, sail_state, score = 0, 0, 50, 0, 0, 0, 0
    storm_active, storm_start_time, last_storm_end_time, rain_initialized = False, 0, 0, False
    game_start_time = time.time()
    ship_health, last_damage_time, ship_sinking = 100, 0, False
    cannonballs.clear()
    last_fire_time_left, last_fire_time_right = 0, 0
    wave_active, last_wave_damage_time = False, 0
    enemies.clear()
    last_enemy_spawn_time = time.time()
    is_night, last_day_night_switch_time = False, time.time()
    rain_enabled, cheat_mode = True, False
    keys_pressed.clear()

def showScreen():
    if is_night: 
        glClearColor(0.02, 0.03, 0.08, 1.0)
    else: 
        glClearColor(0.45, 0.72, 0.95, 1.0)
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    
    setupCamera()
    draw_ocean()
    
    if not first_person_view: 
        draw_ship()
        
    if wave_active: 
        draw_wave()
        
    for enemy in enemies: 
        draw_enemy_ship(enemy)
        
    if aiming_left: 
        draw_range_indicator('left')
    if aiming_right: 
        draw_range_indicator('right')
        
    for ball in cannonballs: 
        draw_cannonball(ball)
        
    if storm_active and rain_enabled: 
        draw_rain()
    
    draw_text(10, 800, f"Score: {score}")  
    draw_text(10, 770, f"Sail State: {['No Sail', 'Half Sail', 'Full Sail'][sail_state]}")
    draw_text(10, 740, f"Health: {int(ship_health)}/{max_health}")
    draw_text(10, 710, f"Cycle: {'Night' if is_night else 'Day'}")
    draw_text(10, 680, f"View: {'First Person' if first_person_view else 'Third Person'} (V to toggle)")
    draw_text(10, 650, f"Rain: {'ON' if rain_enabled else 'OFF'} (T to toggle)")
    draw_text(10, 620, f"Cheat Auto-Mode: {'ON' if cheat_mode else 'OFF'} (C to toggle)")
    draw_text(10, 590, f"Fire Left: [J] | Fire Right: [L]")
    
    if ship_sinking:
        draw_text(300, 400, "GAME OVER - SHIP SINKING!")
        draw_text(350, 370, "Press R to Restart")
    elif storm_active:
        draw_text(10, 560, "STORM ACTIVE!")
        if sail_state == 2: 
            draw_text(10, 530, "Full Sail: -5 HP/sec")
        elif sail_state == 1: 
            draw_text(10, 530, "Half Sail: -2 HP/sec")
    
    glutSwapBuffers()

def idle_with_keys():
    if ship_sinking:
        update_sinking()
        glutPostRedisplay()
        return
        
    update_continuous_keys()
    update_ship_movement()
    update_day_night_cycle()
    update_storm_system()
    update_enemy_spawning()
    apply_storm_damage()
    update_sinking()
    
    if cheat_mode:
        update_cheat_movement()
        
    update_cannonballs()
    update_wave()
    update_enemy_ai()
    check_cannonball_hits()
    
    if storm_active and rain_enabled:
        update_rain()
        
    glutPostRedisplay()



def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Survival of Battleship")
    
    glEnable(GL_DEPTH_TEST)
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle_with_keys)
    
    glutMainLoop()

if __name__ == "__main__":
    main()