from asyncio.windows_events import NULL
import math
import sys
sys.path.insert(0, 'Tech_Calculator')
sys.path.insert(0, '_BackendFiles')
import _BackendFiles.setup as setup
from packaging.version import parse
import numpy as np
from scipy.special import comb
import time
import copy
from collections import deque

# All angles are in conventional mathimatical notations (positive angeles are counter-clockwise, 0° starts in the east direction)
# Works for V2 - V3.3.0
# Easy = 1, Normal = 3, Hard = 5, Expert = 7, Expert+ = 9
# b = time, x and y = grid location from bottom left, a = angle offset, c = left or right respectively, d = direction
cut_direction_index = [90, 270, 180, 0, 135, 45, 225, 315, 270]     # mathamatical 0°, direction of cut
x_grid_distance = 0.43636   # In meters
y_grid_distance = 0.525   # In meters, averaged 0.55m between bottom and middle row, 0.5m between middle and top row.
#Bombs are roughly equal in size to note badcut hitboxes @ 0.36m
bomb_offset = [[x_grid_distance / 2 - 0.18, y_grid_distance / 2 - 0.18, 1 - 0.18], [x_grid_distance / 2 + 0.18, y_grid_distance / 2 + 0.18, 1 + 0.18]]     
saber_hit_distance = 0.5        # The z position where the hitbox will hit the saber. 0 = hilting, 0.5 = mid, 1 = tipping

# ------------------------ Base functions ------------------------

def average(lst, set_len=0):  # Returns the averate of a list of integers
    if len(lst) > 0:
        if set_len == 0:
            return sum(lst) / len(lst)
        else:
            return sum(lst) / set_len
    else:
        return 0

def reverse_cut_direction(angle):
    if angle >= 180:
        return angle - 180
    else:
        return angle + 180

def swap_positions(lis: list, pos1, pos2):
    lis[pos1], lis[pos2] = lis[pos2], lis[pos1]
    return lis

# X is the input, m is the module value.
def mod(x, m):
    return (x % m + m) % m

# Based off unity mathf.lerp
def lerp(p0, p1, t):
    scale = p1 - p0
    offset = p0
    return offset + scale * t

# Generates an S-curve path between two points in 3D space.

# Parameters:
#     start_point (tuple): The starting point (x, y, z).
#     end_point (tuple): The ending point (x, y, z).
#     max_acceleration (float): Maximum acceleration for the S-curve.
#     min_resolution (int): Minimum number of steps between points.
#     max_gap (float): Maximum distance between consecutive points.

# Returns:
#     list of tuples: A list of points representing the S-curve path.

def s_curve_path(start_point, end_point, max_acceleration, min_resolution, max_gap):
    
    start_point = np.array(start_point)
    end_point = np.array(end_point)
    total_distance = np.linalg.norm(end_point - start_point)

    # Ensure min_resolution produces at least that many points
    min_steps = max(min_resolution, int(total_distance / max_gap) + 1)
    
    # Generate an S-curve profile using a sigmoid function
    t = np.linspace(0, 1, min_steps)
    s_curve = 1 / (1 + np.exp(-10 * (t - 0.5)))  # Sigmoid curve with steepness
    
    # Adjust for maximum acceleration constraint by scaling
    s_curve_scaled = s_curve * total_distance
    velocities = np.diff(s_curve_scaled, prepend=0)  # Calculate velocity profile
    max_velocity = np.sqrt(2 * max_acceleration * total_distance)
    if max(velocities) > max_velocity:
        s_curve_scaled *= max_velocity / max(velocities)

    # Interpolate points along the S-curve
    directions = end_point - start_point
    points = [start_point + s * directions for s in s_curve_scaled / total_distance]

    return points

    # Generate a smooth curve path between two points in 3D space, considering
    # starting and ending velocities, acceleration limits, resolution, and maximum gap.
    
    # Parameters:
    # starting_position (tuple): Starting point in 3D space (x, y, z).
    # ending_position (tuple): Ending point in 3D space (x, y, z).
    # max_acceleration (float): Maximum allowable acceleration.
    # minimum_resolution (int): Minimum number of steps between points.
    # maximum_gap (float): Maximum distance allowed between consecutive points.
    # starting_velocity (tuple): Velocity at the start point (optional, default is (0, 0, 0)).
    # ending_velocity (tuple): Velocity at the end point (optional, default is (0, 0, 0)).

    # Returns:
    # list: List of points representing the path in 3D space.

def advanced_s_curve_path(
    starting_position, ending_position, max_acceleration, minimum_resolution,
    maximum_gap, starting_velocity=(0, 0, 0), ending_velocity=(0, 0, 0)):
    
    start_pos = np.array(starting_position)
    end_pos = np.array(ending_position)
    start_vel = np.array(starting_velocity)
    end_vel = np.array(ending_velocity)

    # Total distance and direction
    direction = end_pos - start_pos
    distance = np.linalg.norm(direction)

    # Estimate total time based on max acceleration and velocity constraints
    avg_velocity = (np.linalg.norm(start_vel) + np.linalg.norm(end_vel)) / 2 + 1e-6
    total_time = max(distance / avg_velocity, np.sqrt(2 * distance / max_acceleration))

    # Time step to ensure minimum resolution and maximum gap
    min_time_step = total_time / minimum_resolution
    max_time_step = maximum_gap / avg_velocity
    time_step = min(min_time_step, max_time_step)
    times = np.arange(0, total_time + time_step, time_step)

    # Use a quintic polynomial for smooth position transition with velocity constraints
    coeffs = np.zeros((3, 6))  # Separate coefficients for x, y, z
    for i in range(3):
        A = np.array([
            [0, 0, 0, 0, 0, 1],                          # p(0) = start_pos[i]
            [total_time**5, total_time**4, total_time**3, total_time**2, total_time, 1],  # p(T) = end_pos[i]
            [0, 0, 0, 0, 1, 0],                          # v(0) = start_vel[i]
            [5*total_time**4, 4*total_time**3, 3*total_time**2, 2*total_time, 1, 0],      # v(T) = end_vel[i]
            [0, 0, 0, 2, 0, 0],                          # a(0) = 0
            [20*total_time**3, 12*total_time**2, 6*total_time, 2, 0, 0]                   # a(T) = 0
        ])
        b = np.array([
            start_pos[i], end_pos[i], start_vel[i], end_vel[i], 0, 0
        ])
        coeffs[i] = np.linalg.solve(A, b)

    # Generate positions
    points = []
    for t in times:
        pos = np.zeros(3)
        for i in range(3):
            pos[i] = np.polyval(coeffs[i], t)
        points.append(pos)

    return points

# Not the correct way to define function input type, but it'll help someone.
def point_on_quad_bezier(p0: np.array, p1: np.array, p2: np.array, t):
    return (math.pow(1 - t, 2) * p0) + (2 * (1 - t) * t * p1) + (math.pow(t, 2) * p2)

def angle_on_quad_bezier(p0: np.array, p1: np.array, p2: np.array, t):
    derivative = list((2 * (1 - t) * (p1 - p0)) + (2 * t * (p2 - p1)))      # Pretty sure can remove "list()" but will do later. Not important
    return mod(math.degrees(math.atan2(derivative[1], derivative[0])), 360)

def point_on_cubic_bezier(p0: np.array, p1: np.array, p2: np.array, p3: np.array, t):
    return (math.pow(1 - t, 3) * p0) + (3 * math.pow(1 - t, 2) * t * p1) + (3 * (1 - t) * math.pow(t, 2) * p2) + (math.pow(t, 3) * p3)

def angle_on_cubic_bezier(p0: np.array, p1: np.array, p2: np.array, p3: np.array, t):
    derivative = list((3 * math.pow(1 - t, 2) * (p1 - p0)) + (6 * (1 - t) * t * (p2 - p1)) + (3 * math.pow(t, 2) * (p3 - p2)))      # Pretty sure can remove "list()" but will do later. Not important
    return mod(math.degrees(math.atan2(derivative[1], derivative[0])), 360)

# Rotation around the x-axis (pitch)
def rotate_x(point, center, theta):
    x, y, z = point
    cx, cy, cz = center
    y -= cy
    z -= cz
    y_new = y * math.cos(theta) - z * math.sin(theta)
    z_new = y * math.sin(theta) + z * math.cos(theta)
    return (x, y_new + cy, z_new + cz)

# Rotation around the y-axis (yaw)
def rotate_y(point, center, theta):
    x, y, z = point
    cx, cy, cz = center
    x -= cx
    z -= cz
    x_new = x * math.cos(theta) + z * math.sin(theta)
    z_new = -x * math.sin(theta) + z * math.cos(theta)
    return (x_new + cx, y, z_new + cz)

# Rotation around the z-axis (roll)
def rotate_z(point, center, theta):
    x, y, z = point
    cx, cy, cz = center
    x -= cx
    y -= cy
    x_new = x * math.cos(theta) - y * math.sin(theta)
    y_new = x * math.sin(theta) + y * math.cos(theta)
    return (x_new + cx, y_new + cy, z)

# Perform rotations
def rotate_point(p0, center, pitch, yaw, roll):
    pitch = np.deg2rad(pitch)
    yaw = np.deg2rad(yaw)
    roll = np.deg2rad(roll)

    new_p0 = rotate_x(p0, center, pitch)
    new_p0 = rotate_y(new_p0, center, -yaw)
    new_p0 = rotate_z(new_p0, center, roll)
    return new_p0

def combine_and_sort_list(array1, array2, key):
    combinedArray = array1 + array2
    combinedArray = sorted(combinedArray, key=lambda x: x[f'{key}'])  # once combined, sort by time
    return combinedArray

# ------------------------ Map parsing and information extraction functions ------------------------

def V2_to_V3(V2_map_data: dict):    # Convert V2 JSON to V3
    new_map_data = {'colorNotes':[], 'bombNotes':[], 'obstacles':[], 'sliders':[], 'burstSliders':[]}
    for i in range(0, len(V2_map_data['_notes'])):
        if V2_map_data['_notes'][i]['_type'] in [0, 1]:
            new_map_data['colorNotes'].append({'b': V2_map_data['_notes'][i]['_time']})
            new_map_data['colorNotes'][-1]['x'] = V2_map_data['_notes'][i]['_lineIndex']
            new_map_data['colorNotes'][-1]['y'] = V2_map_data['_notes'][i]['_lineLayer']
            new_map_data['colorNotes'][-1]['a'] = 0
            new_map_data['colorNotes'][-1]['c'] = V2_map_data['_notes'][i]['_type']
            new_map_data['colorNotes'][-1]['d'] = V2_map_data['_notes'][i]['_cutDirection']
        elif V2_map_data['_notes'][i]['_type'] == 3:      # Bombs
            new_map_data['bombNotes'].append({'b': V2_map_data['_notes'][i]['_time']})
            new_map_data['bombNotes'][-1]['x'] = V2_map_data['_notes'][i]['_lineIndex']
            new_map_data['bombNotes'][-1]['y'] = V2_map_data['_notes'][i]['_lineLayer']
    for i in range (0, len(V2_map_data['_obstacles'])):
        new_map_data['obstacles'].append({'b': V2_map_data['_obstacles'][i]['_time']})
        new_map_data['obstacles'][-1]['x'] = V2_map_data['_obstacles'][i]['_lineIndex']
        if V2_map_data['_obstacles'][i]['_type']:  # V2 wall type defines crouch or full walls
            new_map_data['obstacles'][-1]['y'] = 2
            new_map_data['obstacles'][-1]['h'] = 3
        else:
            new_map_data['obstacles'][-1]['y'] = 0
            new_map_data['obstacles'][-1]['h'] = 5
        new_map_data['obstacles'][-1]['d'] = V2_map_data['_obstacles'][i]['_duration']
        new_map_data['obstacles'][-1]['w'] = V2_map_data['_obstacles'][i]['_width']


    return new_map_data

def V3_3_0_to_V3(V3_0_0_map_data: dict):
    new_map_data = copy.deepcopy(V3_0_0_map_data)
    for i in range(0, len(new_map_data['bpmEvents'])):
        new_map_data['bpmEvents'][i]['b'] = new_map_data['bpmEvents'][i].get('b', 0)
        new_map_data['bpmEvents'][i]['m'] = new_map_data['bpmEvents'][i].get('m', 0)

    # for i in range(0, len(newMapData['rotationEvents'])): Used for lighting
    #     newMapData['rotationEvents'][i]['b'] = newMapData['rotationEvents'][i].get('b', 0)
    #     newMapData['rotationEvents'][i]['e'] = newMapData['rotationEvents'][i].get('e', 0)
    #     newMapData['rotationEvents'][i]['r'] = newMapData['rotationEvents'][i].get('r', 0)

    for i in range(0, len(new_map_data['colorNotes'])):
        new_map_data['colorNotes'][i]['b'] = new_map_data['colorNotes'][i].get('b', 0)
        new_map_data['colorNotes'][i]['x'] = new_map_data['colorNotes'][i].get('x', 0)
        new_map_data['colorNotes'][i]['y'] = new_map_data['colorNotes'][i].get('y', 0)
        new_map_data['colorNotes'][i]['a'] = new_map_data['colorNotes'][i].get('a', 0)
        new_map_data['colorNotes'][i]['c'] = new_map_data['colorNotes'][i].get('c', 0)
        new_map_data['colorNotes'][i]['d'] = new_map_data['colorNotes'][i].get('d', 0)
    
    for i in range(0, len(new_map_data['bombNotes'])):
        new_map_data['bombNotes'][i]['b'] = new_map_data['bombNotes'][i].get('b', 0)
        new_map_data['bombNotes'][i]['x'] = new_map_data['bombNotes'][i].get('x', 0)
        new_map_data['bombNotes'][i]['y'] = new_map_data['bombNotes'][i].get('y', 0)
    
    for i in range(0, len(new_map_data['obstacles'])):
        new_map_data['obstacles'][i]['b'] = new_map_data['obstacles'][i].get('b', 0)
        new_map_data['obstacles'][i]['x'] = new_map_data['obstacles'][i].get('x', 0)
        new_map_data['obstacles'][i]['y'] = new_map_data['obstacles'][i].get('y', 0)
        new_map_data['obstacles'][i]['d'] = new_map_data['obstacles'][i].get('d', 0)
        new_map_data['obstacles'][i]['w'] = new_map_data['obstacles'][i].get('w', 0)
        new_map_data['obstacles'][i]['h'] = new_map_data['obstacles'][i].get('h', 0)

    for i in range(0, len(new_map_data['sliders'])):   # Arcs not implemented in the also, so just leave it out.
        new_map_data['sliders'][i]['b'] = new_map_data['sliders'][i].get('b', 0)
        new_map_data['sliders'][i]['c'] = new_map_data['sliders'][i].get('c', 0)
        new_map_data['sliders'][i]['x'] = new_map_data['sliders'][i].get('x', 0)
        new_map_data['sliders'][i]['y'] = new_map_data['sliders'][i].get('y', 0)
        new_map_data['sliders'][i]['d'] = new_map_data['sliders'][i].get('d', 0)
        new_map_data['sliders'][i]['mu'] = new_map_data['sliders'][i].get('mu', 0)
        new_map_data['sliders'][i]['tb'] = new_map_data['sliders'][i].get('tb', 0)
        new_map_data['sliders'][i]['tx'] = new_map_data['sliders'][i].get('tx', 0)
        new_map_data['sliders'][i]['ty'] = new_map_data['sliders'][i].get('ty', 0)
        new_map_data['sliders'][i]['tc'] = new_map_data['sliders'][i].get('tc', 0)
        new_map_data['sliders'][i]['tmu'] = new_map_data['sliders'][i].get('tmu', 0)
        new_map_data['sliders'][i]['m'] = new_map_data['sliders'][i].get('m', 0)

    for i in range(0, len(new_map_data['burstSliders'])):
        new_map_data['burstSliders'][i]['b'] = new_map_data['burstSliders'][i].get('b', 0)
        new_map_data['burstSliders'][i]['c'] = new_map_data['burstSliders'][i].get('c', 0)
        new_map_data['burstSliders'][i]['x'] = new_map_data['burstSliders'][i].get('x', 0)
        new_map_data['burstSliders'][i]['y'] = new_map_data['burstSliders'][i].get('y', 0)
        new_map_data['burstSliders'][i]['d'] = new_map_data['burstSliders'][i].get('d', 0)
        new_map_data['burstSliders'][i]['tb'] = new_map_data['burstSliders'][i].get('tb', 0)
        new_map_data['burstSliders'][i]['tx'] = new_map_data['burstSliders'][i].get('tx', 0)
        new_map_data['burstSliders'][i]['ty'] = new_map_data['burstSliders'][i].get('ty', 0)
        new_map_data['burstSliders'][i]['sc'] = new_map_data['burstSliders'][i].get('sc', 8)
        new_map_data['burstSliders'][i]['s'] = new_map_data['burstSliders'][i].get('s', 1)

    return new_map_data
    
def map_prep(map_data):
    try:
        map_version = parse(map_data['version'])
    except KeyError:
        try:
            map_version = parse(map_data['_version'])
        except KeyError:
            try:
                map_data['_notes']
                map_version = parse('2.0.0')
            except KeyError:
                try:
                    map_data['colorNotes']
                    map_version = parse('3.0.0')
                except KeyError:
                    print("Unknown Map Type. Exiting")
                    exit()
    if map_version < parse('3.0.0'):  # Try to figure out if the map is the V2 or V3 format
        new_map_data = V2_to_V3(map_data)  # Convert to V3
    elif map_version < parse('3.3.0'):
        new_map_data = map_data
    elif map_version < parse('4.0.0'):       # New 3.3.0 spec omits default values, so we need to fill them in
        new_map_data = V3_3_0_to_V3(map_data)
    else:
        # new_map_data = V4_4_0_to_V3(map_data)     #TODO develop 4.0.0 to V3
        pass
    
    new_map_data['colorNotes'] = sorted(new_map_data['colorNotes'], key=lambda d: d['b'])   # Sort data by time (beats).
    new_map_data['bombNotes'] = sorted(new_map_data['bombNotes'], key=lambda d: d['b']) # bombs
    new_map_data['obstacles'] = sorted(new_map_data['obstacles'], key=lambda d: d['b']) # walls
    new_map_data['sliders'] = sorted(new_map_data['sliders'], key=lambda d: d['b'])     # arcs
    new_map_data['brustSliders'] = sorted(new_map_data['burstSliders'], key=lambda d: d['b'])   #chains

    return new_map_data

def split_map_data(map_data: dict, left_or_right):  # False or 0 = Left, True or 1 = Right, 2 = Bombs, 3 = Walls
    match left_or_right:
        case 0:
            block_list = {}
            block_list['notes'] = [block for block in map_data['colorNotes'] if block['c'] == 0]
            block_list['arcs'] = [arcs for arcs in map_data['sliders'] if arcs['c'] == 0]
            block_list['chains'] = [chains for chains in map_data['burstSliders'] if chains['c'] == 0]
        case 1:
            block_list = {}
            block_list['notes'] = [block for block in map_data['colorNotes'] if block['c'] == 1]
            block_list['arcs'] = [arcs for arcs in map_data['sliders'] if arcs['c'] == 1]
            block_list['chains'] = [chains for chains in map_data['burstSliders'] if chains['c'] == 1]
        case 2:
            block_list = [bomb for bomb in map_data['bombNotes']]
        case 3:
            block_list = [wall for wall in map_data['obstacles']]
    return block_list

def calculate_JD(bpm, njs, offset):
    halfjump = 4
    num = 60 / bpm
    
    if njs <= 0.01:
        njs = 10
    
    while (njs * num * halfjump > 18):
        halfjump /= 2

    halfjump += offset

    if halfjump < 0.25:
        halfjump = 0.25

    jumpdistance = njs * num * halfjump * 2

    return jumpdistance

def distance_to_beats(bpm, njs, distance):
    time = distance / njs
    beats = time * bpm / 60

    return beats

def beats_to_seconds(beats, bpm):
    seconds = beats * 60 / bpm
    return seconds

def bind_arcs_to_notes(note_data, arc_data): # Edits noteData
    note_data_index = 0
    note_data_index_t = 0

    for i in range(0, len(note_data)):
        note_data[i]['pre_arc'] = False              # Initialize dict key
        note_data[i]['post_arc'] = False

    for i in range(0, len(arc_data)):
        # Index preparation while loops
        while note_data[note_data_index]['b'] < arc_data[i]['b'] and note_data_index + 1 < len(note_data):      # Increase index until right below correct note (time)
            note_data_index += 1

        while note_data[note_data_index_t]['b'] < arc_data[i]['tb'] and note_data_index_t + 1 < len(note_data):      # Increase index until right below correct note (time)
            note_data_index_t += 1

        same_time_list = []   # Reset list
        found = False

        # Arc matcher while loops
        while True: # Arc beginning note check
            if note_data[note_data_index]['b'] == arc_data[i]['b']:
                same_time_list.append({'data': note_data[note_data_index], 'index': note_data_index})

                if note_data_index + 1 < len(note_data):
                    if note_data[note_data_index + 1]['b'] == arc_data[i]['b']:
                        temp_index = note_data_index
                        while note_data[temp_index + 1]['b'] == arc_data[i]['b'] and temp_index + 1 < len(note_data):
                            temp_index += 1
                            same_time_list.append({'data': note_data[temp_index], 'index': temp_index})
                
                for j in range(0, len(same_time_list)):
                    if (same_time_list[j]['data']['x'] == arc_data[i]['x']) and (same_time_list[j]['data']['y'] == arc_data[i]['y']) and ((same_time_list[j]['data']['d'] == arc_data[i]['d']) or (same_time_list[j]['data']['d'] == 8)):
                        note_data[same_time_list[j]['index']]['post_arc'] = True
                        found = True
                        break
            else:
                if note_data[note_data_index]['b'] > arc_data[i]['b']:
                    break   # If the note index is greater than arc time, then there was no pre
                
                if note_data_index + 1 >= len(note_data):
                    break

                note_data_index += 1
            
            if found:
                break

        same_time_list = []   # Reset list
        found = False

        while True: # Arc ending note check
            if note_data[note_data_index_t]['b'] == arc_data[i]['tb']:
                same_time_list.append({'data': note_data[note_data_index_t], 'index': note_data_index_t})

                if note_data_index_t + 1 < len(note_data):
                    if note_data[note_data_index_t + 1]['b'] == arc_data[i]['tb']:
                        temp_index = note_data_index_t
                        while note_data[temp_index + 1]['b'] == arc_data[i]['tb'] and temp_index + 1 < len(note_data):
                            temp_index += 1
                            same_time_list.append({'data': note_data[temp_index], 'index': temp_index})
                
                for j in range(0, len(same_time_list)):
                    if (same_time_list[j]['data']['x'] == arc_data[i]['tx']) and (same_time_list[j]['data']['y'] == arc_data[i]['ty']) and ((same_time_list[j]['data']['d'] == arc_data[i]['tc']) or (same_time_list[j]['data']['d'] == 8)):
                        note_data[same_time_list[j]['index']]['pre_arc'] = True
                        found = True
                        break
            else:
                if note_data[note_data_index_t]['b'] > arc_data[i]['b']:
                    break   # If the note index is greater than arc time, then there was no post
                
                if note_data_index_t + 1 >= len(note_data):
                    break

                note_data_index_t += 1

            if found:
                break

    return

def bind_chains_to_notes(note_data, chain_data):
    note_data_index = 0

    for i in range(0, len(note_data)):
        note_data[i]['has_chain'] = False              # Initialize dict key

    for i in range(0, len(chain_data)):
        # Index preparation while loops
        while note_data[note_data_index]['b'] < chain_data[i]['b'] and note_data_index + 1 < len(note_data):      # Increase index until right below correct note (time)
            note_data_index += 1

        same_time_list = []   # Reset list
        found = False

        # Chain matcher while loops
        while True: # Chain beginning note check
            if note_data[note_data_index]['b'] == chain_data[i]['b']:
                same_time_list.append({'data': note_data[note_data_index], 'index': note_data_index})

                if note_data_index + 1 < len(note_data):
                    if note_data[note_data_index + 1]['b'] == chain_data[i]['b']:
                        temp_index = note_data_index
                        while note_data[note_data_index + 1]['b'] == chain_data[i]['b'] and note_data_index + 1 < len(note_data):
                            temp_index += 1
                            same_time_list.append({'data': note_data[temp_index], 'index': temp_index})
                
                for j in range(0, len(same_time_list)):
                    if (same_time_list[j]['data']['x'] == chain_data[i]['x']) and (same_time_list[j]['data']['y'] == chain_data[i]['y']) and ((same_time_list[j]['data']['d'] == chain_data[i]['d']) or (same_time_list[j]['data']['d'] == 8)):
                        note_data[same_time_list[j]['index']]['chain_data'] = chain_data[i]
                        note_data[same_time_list[j]['index']]['has_chain'] = True
                        found = True
                        break
            else:
                if note_data[note_data_index]['b'] > chain_data[i]['b']:
                    break   # If the note index is greater than arc time, then there was no pre
                
                if note_data_index + 1 >= len(note_data):
                    break

                note_data_index += 1
            
            if found:
                break

    return
# Base block calculations

# Calculates the entry point of a swing given block position, block angle, and swing angle.
def calc_note_hitbox(block_position, block_angle):
    # Block good hitbox X = 0.8m, Y = 0.5m, Z = 1m
    # Hitbox is Z = -0.15m offset from block position 
    # Distance between 2 blocks on the X axis is 0.436m. /2 equals X middle point of the block hitbox.
    # baseXPosition = 0.21818
    
    # Distance between 2 blocks on the Y axis is average 0.525m. /2 equals Y middle point of the block hitbox.
    # baseYPosition = 0.2625

    hitbox = {'p0': {}, 'p1': {}}

    x_note_pos_relative_to_center = (block_position[0] + 0.5 - 2) * x_grid_distance        # Calculate the xCoordinates relative to the middle of the world.

    x_ang = 0            # Pitch, Yaw, Roll
    y_ang = np.arccos(x_note_pos_relative_to_center / (saber_hit_distance + 0.85))    #  saber length + 0.85 forward z hitbox. 0° is straight forwards, +angle is CC, -angle is clockwise.
    z_ang = block_angle

    # Initialize point positions for hitbox caluclations in world space
    p0 = np.array([0, 0, 0.15])         # front left corner 
    p1 = np.array([0.8, 0.5, 1.15])     # back right corner
    center = np.array([0.4, 0.25, 1])   # center of cube 
    
    # Apply rotation transformes
    rotated_p0 = rotate_point(p0, center, x_ang, y_ang, z_ang)
    rotated_p1 = rotate_point(p1, center, x_ang, y_ang, z_ang)
    
    # Apply grid positioning
    x0_pos = block_position[0] * x_grid_distance + rotated_p0[0]
    x1_pos = block_position[0] * x_grid_distance + rotated_p1[0]
    y0_pos = block_position[1] * y_grid_distance + rotated_p0[1]
    y1_pos = block_position[1] * y_grid_distance + rotated_p1[1]
    z0_pos = rotated_p0[2]
    z1_pos = rotated_p1[2]
    
    hitbox['p0'] = np.array([x0_pos, y0_pos, z0_pos])
    hitbox['p1'] = np.array([x1_pos, y1_pos, z1_pos])
    angle = np.array([x_ang, y_ang, z_ang])
    
    block_data = {'pos_data' : hitbox, 'angle': angle}

    return block_data

def calculate_bomb_hitbox(b_pos: list):
    hitbox_x0 = b_pos[0] * x_grid_distance + bomb_offset[0][0]
    hitbox_y0 = b_pos[1] * y_grid_distance + bomb_offset[0][1]
    hitbox_z0 = bomb_offset[0][2]
    hitbox_x1 = b_pos[0] * x_grid_distance + bomb_offset[1][0]
    hitbox_y1 = b_pos[1] * y_grid_distance + bomb_offset[1][1]
    hitbox_z1 = bomb_offset[1][2]

    hitbox = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1])}
    return hitbox

def calculate_wall_hitbox(x_pos, y_Pos, width, distance, height):
    hitbox_x0 = x_pos * x_grid_distance
    hitbox_y0 = y_Pos * y_grid_distance
    # hitboxZ1 = -0.25                          # Need to verify: Subtract 0.25 to make front face of wall line up with front face of note (walls just built like that) (cred: arcViewer)
    hitbox_z0 = 1                                
    hitbox_x1 = (x_pos + width) * x_grid_distance
    hitbox_y1 = (y_Pos + height) * y_grid_distance
    hitbox_z1 = distance * metadata['njs'] + 1

    hitboxPos = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1])}
    return hitboxPos

def chain_curve(chain_data):
    distance = math.sqrt(math.pow((chain_data['x'] - chain_data['tx']), 2) + math.pow((chain_data['y'] - chain_data['ty']), 2))
    chain_start_pos = np.array([chain_data['x'], chain_data['y']])
    chain_end_pos = np.array([chain_data['tx'], chain_data['ty']])
    mid_offset = np.array([math.cos(math.radians(cut_direction_index[chain_data['d']])), math.sin(math.radians(cut_direction_index[chain_data['d']]))]) * distance / 2
    mid_point = chain_start_pos + mid_offset
    time_end = chain_data['tb']             # tail beat
    link_num = chain_data['sc'] - 1         # link count
    link_duration = time_end - chain_data['b']

    link_pos = []
    link_angle = []
    link_beat = []

    for j in range(1, chain_data['sc']):
        progress_norm = j / (chain_data['sc'] - 1)

        t = progress_norm * chain_data['s']

        link_pos.append(point_on_quad_bezier(chain_start_pos, mid_point, chain_end_pos, t))     # Use new list entry as temp variable to pre-converted position data.
        
        link_angle.append(angle_on_quad_bezier(chain_start_pos, mid_point, chain_end_pos, t))
        
        link_pos[-1] = calc_note_hitbox(link_pos[-1], link_angle[-1])                           # Calculate block swing strike position in meters and save.

        link_beat.append(progress_norm * link_duration + chain_data['b'])

    return link_num, link_pos, link_angle, link_beat

def note_angle_snapping(note_group):   # Expects an array size of 2
    # 3 cases. All involve only 2 notes. 
    # Arrow note angle adjustment +-22.5°
    # Dot note angle adjustment +-45°
    # Case 0: All arrow notes       Only consider arrow notes if they're closly lined up already and facing the same direction
    # Case 1: Arrow + dot note      Angle adjust arrow and dot note towards each other if dot note is in the general tragectory of the arrow note.
    # Case 2: All dot notes         Angle adjust all dot notes.
    
    if len(note_group) != 2:
        print("Note Angle Snapping Function error")
        return

    dot_count = 0
    for forloop_note in note_group:    # Determine angle snap case
        if forloop_note['d'] == 8:
            dot_count += 1
    
    note_angles = []
    match dot_count:
        case 0:
            if note_group[0]['d'] == note_group[1]['d']:      # Arrow notes must have the same d value to snap
                note_angle = cut_direction_index[note_group[0]['d']]

                angle_from_position = mod(math.degrees(math.atan2(note_group[0]['y'] - note_group[1]['y'], note_group[0]['x'] - note_group[1]['x'])), 360)
                mirrored_angle_from_position = mod(angle_from_position + 180, 360)

                if abs(note_angle - angle_from_position) <= 22.5:
                    note_angles.append(angle_from_position)
                    note_angles.append(angle_from_position)
                
                elif abs(note_angle - mirrored_angle_from_position) <= 22.5:
                    note_angles.append(mirrored_angle_from_position)
                    note_angles.append(mirrored_angle_from_position)

                else:
                    note_angles.append(mod(cut_direction_index[note_group[0]['d']] + note_group[0]['a'], 360))
                    note_angles.append(mod(cut_direction_index[note_group[1]['d']] + note_group[1]['a'], 360))

        case 1:     # Arrow note with a dot note
            
            if note_group[0]['d'] != 8:      # Determine where in the array contains the arrow note
                arrow_index = 0
            else:
                arrow_index = 1
            
            note_angle = cut_direction_index[note_group[arrow_index]['d']]     
            angle_from_position = mod(math.degrees(math.atan2(note_group[0]['y'] - note_group[1]['y'], note_group[0]['x'] - note_group[1]['x'])), 360)
            mirrored_angle_from_position = mod(angle_from_position + 180, 360)

            if abs(note_angle - angle_from_position) <= 22.5:
                note_angles.append(angle_from_position)
                note_angles.append(angle_from_position)
            
            elif abs(note_angle - mirrored_angle_from_position) <= 22.5:
                note_angles.append(mirrored_angle_from_position)
                note_angles.append(mirrored_angle_from_position)

            else:
                note_angles.append(mod(cut_direction_index[note_group[0]['d']] + note_group[0]['a'], 360))
                note_angles.append(mod(cut_direction_index[note_group[1]['d']] + note_group[1]['a'], 360))

        case 2:     # 2 dot notes
            angle_from_position = mod(math.degrees(math.atan2(note_group[0]['y'] - note_group[1]['y'], note_group[0]['x'] - note_group[1]['x'])), 360)
            note_angles.append(angle_from_position)
            note_angles.append(angle_from_position)

    return note_angles

def create_note_list(object_data: dict):
    # Purpose of the function is to prepare and condition note data

    # Note data structure
    # beat: float The time of the swing
    # beat_end: float The end of the swing
    # is_dot: bool If the note is a dot note
    # LRhand: bool Left or Right hand
    # hitbox: Array of hitbox data
    # note_angle: float The angle of the note
    # pre_angle_disabled: bool If 100° pre swing angle is required (disabled for arcs)
    # post_angle_disabled: bool If 60° post swing angle is required (disabled for arcs)
    
    notes = object_data['notes']
    arcs = object_data['arcs']
    chains = object_data['chains']
    bind_arcs_to_notes(notes, arcs)        # Assigns pre/post angle required bool values to every note/chain
    bind_chains_to_notes(notes, chains)
    note_data = []
    note_index = 0

    while note_index < len(notes):
        same_time = []
        same_time.append(notes[note_index])
        
        if note_index + 1 < len(notes) - 1:  # Check if array access is valid
            while (notes[note_index]['b'] == notes[note_index + 1]['b']) and (note_index + 1 < len(notes) - 1):
                note_index += 1
                same_time.append(notes[note_index])

        grouped_notes = same_time
        note_angles = []

        if len(grouped_notes) != 2:      # Snap precision angle adjustment only happens with 2 notes.
            for forloop_index in range(0, len(grouped_notes)):
                if grouped_notes[forloop_index]['d'] == 8:
                    is_dot = True
                    note_angles.append(mod(grouped_notes[forloop_index]['a'], 360))
                else:
                    is_dot = False
                    note_angles.append(mod(cut_direction_index[grouped_notes[forloop_index]['d']] + grouped_notes[forloop_index]['a'], 360))       # Get block angle, including precision angle

        else:       # Multiple notes at the same time can alter note angles
            note_angles = note_angle_snapping(grouped_notes)
        
        for grouped_note_index in range(0, len(grouped_notes)):

            current_note = grouped_notes[grouped_note_index]

            hitbox_pos_data = calc_note_hitbox([current_note['x'], current_note['y']], note_angles[grouped_note_index])     

            time_start = current_note['b']
            
            if current_note['has_chain']:
                link_num, link_pos, link_angle, link_beat = chain_curve(current_note['chain_data'])
                


            note_data.append({})
            # swingData[-1]['LRhand'] = handedness                            #Bool
            note_data[-1]['is_dot'] = is_dot                                  #Bool
            note_data[-1]['beat'] = time_start                          #Float
            note_data[-1]['hitbox'] = hitbox_pos_data                         #Array of Vector3
            note_data[-1]['note_angle'] = note_angles[grouped_note_index]                         #Vector3
            note_data[-1]['pre_angle_disabled'] = current_note['pre_arc']             #Bool
            note_data[-1]['post_angle_disabled'] = current_note['post_arc']           #Bool
            note_data[-1]['has_chain'] = current_note['has_chain']                   #Bool
            if current_note['has_chain']:
                note_data[-1]['chain_data'] = {'link_num': link_num, 'link_pos': link_pos, 'link_angle': link_angle, 'link_beat': link_beat}

        note_index += 1

    note_data = sorted(note_data, key=lambda d: d['beat'])  # Sort by time
    return note_data

def create_bomb_list(bombs: list):
    bomb_data = []
    bomb_index = 0
    while bomb_index < len(bombs):
        same_time = []
        same_time.append(bombs[bomb_index])

        # Consolidate bombs on the same beat.

        if bomb_index + 1 < len(bombs) - 1:  # Check if array access is valid
            while (bombs[bomb_index]['b'] == bombs[bomb_index + 1]['b']) and (bomb_index + 1 < len(bombs) - 1):
                bomb_index += 1
                same_time.append(bombs[bomb_index])

        bomb_data.append({})
        bomb_data[-1]['beat'] = same_time[0]['b']

        bomb_data[-1]['hitbox'] = {'pos_data': []}        
        for j in range(0, len(same_time)):
            bomb_pos = [same_time[j]['x'], same_time[j]['y']]
            bomb_data[-1]['hitbox']['pos_data'].append(calculate_bomb_hitbox(bomb_pos))     # We will approximate bombs to be cubes.

        bomb_index += 1
    
    return bomb_data

def create_wall_list(walls: list):
    wall_data = []
    wall_index = 0
    
    while wall_index < len(walls):
        same_time = []
        same_time.append(walls[wall_index])

        # Consolidate walls on the same beat.
        if wall_index + 1 < len(walls) - 1:          # Check if array access is valid
            while (walls[wall_index]['b'] == walls[wall_index + 1]['b']) and (wall_index + 2 < len(walls)):
                same_time.append(walls[wall_index])
                wall_index += 1
        
        wall_data.append({})     # Initialize new entry
        wall_data[-1]['beat'] = same_time[0]['b']
        wall_data[-1]['hitbox'] = {'pos_data': []}      # We will approximate bombs to be cubes instead of sphears for speed.
        
        for j in range(0, len(same_time)):
            wall_data[-1]['hitbox']['pos_data'].append(calculate_wall_hitbox(same_time[j]['x'], same_time[j]['y'], same_time[j]['w'], same_time[j]['d'], same_time[j]['h']))
            wall_data[-1]['hitbox']['pos_data'][-1]['length_seconds'] = beats_to_seconds(same_time[j]['d'], metadata['bpm'])

        wall_index += 1
    
    return wall_data
    
def apply_rotation_data(object_data, rotation_data=[]):
    if len(rotation_data) == 0:
        return object_data
    
    rotation = 0        # Current platform rotation (yaw)
    rotation_index = 0   # Index of future incoming rotation event
    inclusive_flag = not rotation_data[rotation_index]['e']
    # test_rotation_changelog = []
    if isinstance(object_data[0]['hitbox']['pos_data'], list):
        position_data_is_list = True
    else:
        position_data_is_list = False

    for i in range(0, len(object_data)):
        if rotation_index < len(rotation_data):
            
            if inclusive_flag:
                while object_data[i]['beat'] >= rotation_data[rotation_index]['b']:    # While loop to handle cases where there are multiple rotation events between objects
                    rotation += rotation_data[rotation_index]['r']
                    # test_rotation_changelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                    if rotation_index + 1 < len(rotation_data):
                        rotation_index += 1
                        inclusive_flag = not rotation_data[rotation_index]['e']
                    else:
                        break
            else:
                while object_data[i]['beat'] > rotation_data[rotation_index]['b']:     # While loop to handle cases where there are multiple rotation events between objects
                    rotation += rotation_data[rotation_index]['r']
                    # test_rotation_changelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                    if rotation_index + 1 < len(rotation_data):
                        rotation_index += 1
                        inclusive_flag = not rotation_data[rotation_index]['e']
                    else:
                        break

        # p0 = np.array([objectData[i]['hitbox']['p0']['x'],objectData[i]['hitbox']['p0']['y'],objectData[i]['hitbox']['p0']['z']])
        # p1 = np.array([objectData[i]['hitbox']['p1']['x'],objectData[i]['hitbox']['p1']['y'],objectData[i]['hitbox']['p1']['z']])
        if position_data_is_list:
            for pos_index in range(0, len(object_data[i]['hitbox']['pos_data'])):
                p0 = object_data[i]['hitbox']['pos_data'][pos_index]['p0']
                p1 = object_data[i]['hitbox']['pos_data'][pos_index]['p1']
                center = np.array([x_grid_distance * 2, 0, 0])
                # Rotation must be inverted to convert between mathimatical and beatsaber rotation orientation
                object_data[i]['hitbox']['pos_data'][pos_index]['p0'] = rotate_point(p0, center, 0, -rotation, 0)
                object_data[i]['hitbox']['pos_data'][pos_index]['p1'] = rotate_point(p1, center, 0, -rotation, 0)
        else:
            p0 = object_data[i]['hitbox']['pos_data']['p0']
            p1 = object_data[i]['hitbox']['pos_data']['p1']
            center = np.array([0,0,0])
            object_data[i]['hitbox']['pos_data']['p0'] = rotate_point(p0, center, 0, -rotation, 0)
            object_data[i]['hitbox']['pos_data']['p1'] = rotate_point(p1, center, 0, -rotation, 0)
    
    return object_data

# ------------------------ Algo specific functions ------------------------
# TODO: Finish
# hitboxPos: Vector3 (touple of floats)
# hitboxAngle: Angle3 (touple of floats)
# strikeAngle: float
def calculate115(hitbox_pos, hitbox_angle, strike_angle):
    #0.4 = (x) middle of width of hitbox, (y) 0.5 = top of hitbox, (z) length of hitbox
    strike_pos = [0.4, 0.5, hitbox_pos['p0'][2] + saber_hit_distance]    # Initializa strike position.
    
    if strike_angle != -1:        # If given a swingAngle, calculate exact point on the hitbox to strike for 15 acc
        x_distance = 0.4 * math.sin(math.radians(strike_angle - hitbox_angle))
        x_offset = x_distance * math.sin(math.radians(hitbox_angle - 180))
        y_offset = x_distance * math.cos(math.radians(hitbox_angle - 180))
    else:
        x_offset = 0
        y_offset = 0

    strike_pos[0] += x_offset
    strike_pos[1] += y_offset
    # rotated_strikePos = rotatePoint(initStrikePos, center, hitboxAngle[0], hitboxAngle[1], hitboxAngle[2])
    return strike_pos

# 2 ways to do this.
# 1.    Run this function multiple times for various skill levels (25, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000pp) (slow, but simple)
#           Determine the perfect optimal path, then smooth through acceleration limits and introduce noise along path to simulate lower skill levels
# 2.    Run skill checks for every note hit and determine accuracy/hit chance for as many skill levels as possible  (faster, but very complex to program)
#
# Posisibility to modify
# Return possibilities: 
#   a set of points for a acc vs PP graph,
#   a set of fail points for various skill levels for possible PP on fail reward.
#   the optimal swing path data and nothing more, leaving analysis to future functions
#   extra data based on bomb and wall position added to the note/swing data

# Accuracy effects both angle and position. During slower section of songs, the position difference can be minimized, resulting in little variation with angles.
# During faster sections of song, the hand can't reach the note physically, so a small angle deviation will be magnified.
# Instability at speed.

def calculate_hit_pos():
    pass

def calculate_hit_angle():
    pass


def pos_pathing(start_point, end_point, skill_set):
    pos_accel = skill_set['positionAcceleration']
    ang_accel = skill_set['angleAcceleration']
    average_acc = skill_set['accuracy']
    max_acceleration = skill_set
    min_resolution = 50
    max_gap = 0.05

    advanced_s_curve_path(start_pos, end_pos, max_acceleration, minimum_resolution, maximum_gap, starting_velocity, ending_velocity)    # Need to run this twice, one for position and one for angles.

def angle_pathing():
    pass

def bomb_pathing(swing_path, bomb_data):
    pass

def path_analysis(path):
    pass

def vision_analysis(path):
    pass

def swing_path(note_data, bomb_data, wall_data, handedness, skill_set, rotationData = []):
    accGraph = [[]]
    averageAcc = 0.0    # The acc
    readibility = 0.0   # How much vision block
    rotation = 0.0      # How much roll+yaw angle
    speed = 0.0         # How much pitch angle
    position = 0.0      # How much position
    
    noramlity = 0.0     # How common the pattern is

    if handedness == 0:                                                 # X, Y, and Z coordinates in meters
        h_pos = np.array([1.5 * x_grid_distance, 1.5 * y_grid_distance, -saber_hit_distance])     # Left 
    else:
        h_pos = np.array([2.5 * x_grid_distance, 1.5 * y_grid_distance, -saber_hit_distance])     # Right
    
    note_path = []

    for noteDataIndex in range(0, len(note_data)):
        

        start_pos, end_pos = calculate_hit_pos()                            # Find hand positions for swing
        start_angle, end_angle = calculate_hit_angle()                      # Find angles for swing

        basic_note_path = pos_pathing(start_pos, end_pos, skill_set)       # Find path between notes
        basic_angle_path = angle_pathing

        note_path.append({})

        note_path[-1]['path_data'] = bomb_pathing(note_path, bomb_data)         # Adjust path to avoid bombs

        note_path[-1]['path_analysis'] = path_analysis(note_path['path_data'])  # Analyse scoring metrics

    for note_path_index in range(0, len(note_path)):
        readibility = vision_analysis

    return accGraph


def difficultyAnalysis(noteData, bombData, wallData, handedness, rotationData = []):
    skillList = []      # positionAcceleration m/s^2, angleAcceleration °/s^2, accuracy in average acc
    skillList.append({'positionAcceleration': 4294967295, 'angleAcceleration': 4294967295, 'accuracy': 15})
    skillList.append({'positionAcceleration': 100, 'angleAcceleration': 3600, 'accuracy': 10})

    for skillListIndex in range(0, len(skillList)):
        skillList[skillListIndex]['swingPathReturn'] = swing_path(noteData, bombData, wallData, handedness, skillList[skillListIndex], rotationData)

    return skillList



# ------------------------ Function Execution ------------------------

def techOperations(B_mapData: dict, metadata: dict, isuser=True, verbose=True):
    B_LeftNoteData = split_map_data(B_mapData, 0)     # Parse mapdata into separate varables to pass into functions
    B_RightNoteData = split_map_data(B_mapData, 1)
    B_BombData = split_map_data(B_mapData, 2)
    B_WallData = split_map_data(B_mapData, 3)
    LeftNoteData = create_note_list(B_LeftNoteData)    # Create extract object data with game mechanics
    RightNoteData = create_note_list(B_RightNoteData)
    BombData = create_bomb_list(B_BombData)
    WallData = create_wall_list(B_WallData)
    if len(B_mapData['rotationEvents']) > 0:                # Apple rotation data if available
        LeftNoteData = apply_rotation_data(LeftNoteData, B_mapData['rotationEvents'])
        RightNoteData = apply_rotation_data(RightNoteData, B_mapData['rotationEvents'])
        BombData = apply_rotation_data(BombData, B_mapData['rotationEvents'])
        WallData = apply_rotation_data(WallData, B_mapData['rotationEvents'])

    left_results = difficultyAnalysis(LeftNoteData, BombData, WallData, 0, B_mapData['rotationEvents'])
    right_results = difficultyAnalysis(RightNoteData, BombData, WallData, 1, B_mapData['rotationEvents'])
    
    LeftSwingData = []
    RightSwingData = []

    if isuser:
        tech = 1
        print(f"Calculated Tech = {round(tech, 2)}")  # Put Breakpoint here if you want to see
        # print(f"Calculated nerf = {round(low_note_nerf, 2)}")
        # print(f"Calculated balanced tech = {round(balanced_tech, 2)}")
        # print(f"Calculated balanced pass diff = {round(balanced_pass, 2)}")
        pass
    return 0     # returnDict


def mapCalculation(mapData, metadata, isuser=True, verbose=True):
    t0 = time.time()
    newMapData = map_prep(mapData)
    t1 = time.time()
    data = techOperations(newMapData, metadata, isuser, verbose)
    if isuser:
        print(f'Execution Time = {t1 - t0}')
    return data


if __name__ == "__main__":
    print("input map key")
    # mapKey = input()
    # mapKey = mapKey.replace("!bsr ", "")
    mapKey = '38419'
    characteristic = '90Degree'

    infoData = setup.loadInfoData(mapKey)
    availableDiffs = setup.findDiffs(setup.findSongPath(mapKey), characteristic)

    if len(availableDiffs) > 1:
        print(f'Choose Diff num: {availableDiffs}')
        diffNum = int(input())
    else:
        diffNum = availableDiffs[0]
        print(f'autoloading {diffNum}')
    mapData = setup.loadMapData(mapKey, diffNum, characteristic=characteristic)

    for i, d in enumerate(infoData['_difficultyBeatmapSets']):
        if d.get('_beatmapCharacteristicName') == characteristic:
            charIndex = i
            break
    for i, d in enumerate(infoData['_difficultyBeatmapSets'][i]['_difficultyBeatmaps']):
        if d.get('_difficultyRank') == diffNum:
            diffIndex = i
            break
    
    metadata = {'bpm': infoData['_beatsPerMinute']}
    metadata['njs'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpMovementSpeed']
    metadata['offset'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpStartBeatOffset']

    mapCalculation(mapData, metadata, True, True)
    print("Done")
    input()