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
import pickle
import json

# All angles are in conventional mathimatical notations (positive angeles are counter-clockwise, 0° starts in the east direction)
# Works for V2 - V3.3.0
# All distances are in meters
# Easy = 1, Normal = 3, Hard = 5, Expert = 7, Expert+ = 9
# b = time, x and y = grid location from bottom left, a = angle offset, c = left or right respectively, d = direction
cut_direction_index = [90, 270, 180, 0, 135, 45, 225, 315, 270]     # mathamatical 0°, direction of cut
x_grid_distance = 0.43636   # In meters
y_grid_distance = 0.525   # In meters, averaged 0.55m between bottom and middle row, 0.5m between middle and top row.

# Bombs are roughly equal in size to note badcut hitboxes @ 0.36m [[x0,y0,z0],[x1,y1,z1]]
bomb_offset = [[x_grid_distance / 2 - 0.18, y_grid_distance / 2 - 0.18, 1 - 0.18], [x_grid_distance / 2 + 0.18, y_grid_distance / 2 + 0.18, 1 + 0.18]]     
saber_hit_distance = 0.5        # The z position where the hitbox will try to hit the saber. 0 = hilting, 0.5 = mid, 1 = tipping.
refresh_rate = 15              # Simulated refreshrate. Defines the simulation precision

# Debug functions

def convert_for_json(obj):
    """Recursively convert objects to be JSON serializable."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, dict):
        return {convert_for_json(k): convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [convert_for_json(i) for i in obj]
    else:
        return obj

# copy paste this into debug console to export: export_data(note_data, bomb_data, wall_data)
def export_data(note_data, bomb_data, wall_data):
    export_note_data = convert_for_json(note_data)
    export_bomb_data = convert_for_json(bomb_data)
    export_wall_data = convert_for_json(wall_data)

    with open("_TestFiles\\note_data.json", "w") as f:
        json.dump(export_note_data, f, indent=4)
    with open("_TestFiles\\bomb_data.json", "w") as f:
        json.dump(export_bomb_data, f, indent=4)
    with open("_TestFiles\\wall_data.json", "w") as f:
        json.dump(export_wall_data, f, indent=4)


# ------------------------ Base functions ------------------------

def average(lst: list[int], set_len=0) -> float:  # Returns the averate of a list of integers
    if len(lst) > 0:
        if set_len == 0:
            return sum(lst) / len(lst)
        else:
            return sum(lst) / set_len
    else:
        return 0

def reverse_cut_direction(angle) -> float:
    if angle >= 180:
        return angle - 180
    else:
        return angle + 180

def swap_positions(lis: list[int], pos1, pos2):
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

def range_float(start, end, step, accurate_steps=True):
    accum = start
    steps = [start]
    
    if accurate_steps:
        step_count = 1
        while step_count * step <= end:
            steps.append(step_count * step)
            step_count += 1
    
    else:   # My first solution to this problem. I liked it because it's memory efficient and fast, but accumulating floating point operations starts to make the output messy.
        while accum + step <= end:
            accum += step
            steps.append(accum)
    
    return steps

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
def point_on_quad_bezier(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, t):
    return (math.pow(1 - t, 2) * p0) + (2 * (1 - t) * t * p1) + (math.pow(t, 2) * p2)

def angle_on_quad_bezier(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, t):
    derivative = list((2 * (1 - t) * (p1 - p0)) + (2 * t * (p2 - p1)))      # Pretty sure can remove "list()" but will do later. Not important
    return mod(math.degrees(math.atan2(derivative[1], derivative[0])), 360)

def point_on_cubic_bezier(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, t):
    return (math.pow(1 - t, 3) * p0) + (3 * math.pow(1 - t, 2) * t * p1) + (3 * (1 - t) * math.pow(t, 2) * p2) + (math.pow(t, 3) * p3)

def angle_on_cubic_bezier(p0: list, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, t):
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
    new_p0 = rotate_y(new_p0, center, yaw)
    new_p0 = rotate_z(new_p0, center, roll)
    return np.array(new_p0)

def combine_and_sort_list(array1, array2, key):
    combinedArray = array1 + array2
    combinedArray = sorted(combinedArray, key=lambda x: x[f'{key}'])  # once combined, sort by time
    return combinedArray

# ------------------------ Map parsing and information extraction functions ------------------------

def V2_to_V3_NJS(V2_map_data: dict, njs: float):    # Convert V2 JSON to V3
    new_map_data = {'colorNotes':[], 'bombNotes':[], 'obstacles':[], 'sliders':[], 'burstSliders':[]}
    for i in range(0, len(V2_map_data['_notes'])):
        if V2_map_data['_notes'][i]['_type'] in [0, 1]:
            new_map_data['colorNotes'].append({'b': V2_map_data['_notes'][i]['_time']})
            new_map_data['colorNotes'][-1]['x'] = V2_map_data['_notes'][i]['_lineIndex']
            new_map_data['colorNotes'][-1]['y'] = V2_map_data['_notes'][i]['_lineLayer']
            new_map_data['colorNotes'][-1]['a'] = 0
            new_map_data['colorNotes'][-1]['c'] = V2_map_data['_notes'][i]['_type']
            new_map_data['colorNotes'][-1]['d'] = V2_map_data['_notes'][i]['_cutDirection']
            new_map_data['colorNotes'][-1]['njs'] = njs
            # new_map_data['colorNotes'][-1]['bpm'] = bpm
        elif V2_map_data['_notes'][i]['_type'] == 3:      # Bombs
            new_map_data['bombNotes'].append({'b': V2_map_data['_notes'][i]['_time']})
            new_map_data['bombNotes'][-1]['x'] = V2_map_data['_notes'][i]['_lineIndex']
            new_map_data['bombNotes'][-1]['y'] = V2_map_data['_notes'][i]['_lineLayer']
            new_map_data['bombNotes'][-1]['njs'] = njs
            # new_map_data['bombNotes'][-1]['bpm'] = bpm
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
        new_map_data['obstacles'][-1]['njs'] = njs
        # new_map_data['obstacles'][-1]['bpm'] = bpm
    return new_map_data

def V3_3_0_to_V3_NJS(V3_3_0_map_data: dict, njs: float):
    new_map_data = copy.deepcopy(V3_3_0_map_data)
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
        new_map_data['colorNotes'][i]['njs'] = njs
    
    for i in range(0, len(new_map_data['bombNotes'])):
        new_map_data['bombNotes'][i]['b'] = new_map_data['bombNotes'][i].get('b', 0)
        new_map_data['bombNotes'][i]['x'] = new_map_data['bombNotes'][i].get('x', 0)
        new_map_data['bombNotes'][i]['y'] = new_map_data['bombNotes'][i].get('y', 0)
        new_map_data['bombNotes'][i]['njs'] = njs
    
    for i in range(0, len(new_map_data['obstacles'])):
        new_map_data['obstacles'][i]['b'] = new_map_data['obstacles'][i].get('b', 0)
        new_map_data['obstacles'][i]['x'] = new_map_data['obstacles'][i].get('x', 0)
        new_map_data['obstacles'][i]['y'] = new_map_data['obstacles'][i].get('y', 0)
        new_map_data['obstacles'][i]['d'] = new_map_data['obstacles'][i].get('d', 0)
        new_map_data['obstacles'][i]['w'] = new_map_data['obstacles'][i].get('w', 0)
        new_map_data['obstacles'][i]['h'] = new_map_data['obstacles'][i].get('h', 0)
        new_map_data['obstacles'][i]['njs'] = njs

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
    
def V3_0_0_to_V3_NJS(V3_0_0_map_data: dict, njs: float):    # This function is identical to function V3_3_0_to_V3_NJS, I made them different functions just because it's easier to read.
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
        new_map_data['colorNotes'][i]['njs'] = njs
    
    for i in range(0, len(new_map_data['bombNotes'])):
        new_map_data['bombNotes'][i]['b'] = new_map_data['bombNotes'][i].get('b', 0)
        new_map_data['bombNotes'][i]['x'] = new_map_data['bombNotes'][i].get('x', 0)
        new_map_data['bombNotes'][i]['y'] = new_map_data['bombNotes'][i].get('y', 0)
        new_map_data['bombNotes'][i]['njs'] = njs
    
    for i in range(0, len(new_map_data['obstacles'])):
        new_map_data['obstacles'][i]['b'] = new_map_data['obstacles'][i].get('b', 0)
        new_map_data['obstacles'][i]['x'] = new_map_data['obstacles'][i].get('x', 0)
        new_map_data['obstacles'][i]['y'] = new_map_data['obstacles'][i].get('y', 0)
        new_map_data['obstacles'][i]['d'] = new_map_data['obstacles'][i].get('d', 0)
        new_map_data['obstacles'][i]['w'] = new_map_data['obstacles'][i].get('w', 0)
        new_map_data['obstacles'][i]['h'] = new_map_data['obstacles'][i].get('h', 0)
        new_map_data['obstacles'][i]['njs'] = njs

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



def map_prep(map_data, metadata):
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
    njs = metadata['njs']
    if map_version < parse('3.0.0'):  # Try to figure out if the map is the V2 or V3 format
        new_map_data = V2_to_V3_NJS(map_data, njs)  # Convert to V3
    elif map_version < parse('3.3.0'):
        new_map_data = V3_0_0_to_V3_NJS(map_data, njs)
    elif map_version < parse('4.0.0'):       # New 3.3.0 spec omits default values, so we need to fill them in
        new_map_data = V3_3_0_to_V3_NJS(map_data, njs)
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

def calculate_half_jump_duration(note_jump_speed, start_beat_offset, bpm):
    half_jump_duration = 4
    seconds_per_beat = 60 / bpm

    while note_jump_speed * seconds_per_beat * half_jump_duration > 17.999:
        half_jump_duration /= 2

    half_jump_duration += start_beat_offset

    if half_jump_duration < 0.25:
        half_jump_duration = 0.25 

    return half_jump_duration

def caculate_jump_distance(note_jump_speed, start_beat_offset, bpm):
    seconds_per_beat = 60 / bpm
    return calculate_half_jump_duration(note_jump_speed, start_beat_offset, bpm) * seconds_per_beat * note_jump_speed * 2


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

    # Initialize point positions for hitbox caluclations in world space [x,y,z]
    p0 = np.array([0 + (block_position[0] - 2) * x_grid_distance, 0 + block_position[1] * y_grid_distance, 0.15])         # front left corner 
    p1 = np.array([0.8 + (block_position[0] - 2) * x_grid_distance, 0.5 + block_position[1] * y_grid_distance, 1.15])     # back right corner (0.8m (block width) - 2
    center = np.array([0.4 + (block_position[0] - 2) * x_grid_distance, 0.25 + block_position[1] * y_grid_distance, 1])   # center of cube 
    
    # Apply rotation transformes
    rotated_p0 = rotate_point(p0, center, x_ang, y_ang, z_ang)
    rotated_p1 = rotate_point(p1, center, x_ang, y_ang, z_ang)
    
    # Apply grid positioning
    x0_pos = rotated_p0[0]
    x1_pos = rotated_p1[0]
    y0_pos = rotated_p0[1]
    y1_pos = rotated_p1[1]
    z0_pos = rotated_p0[2]
    z1_pos = rotated_p1[2]
    
    hitbox['p0'] = np.array([x0_pos, y0_pos, z0_pos])
    hitbox['p1'] = np.array([x1_pos, y1_pos, z1_pos])
    angle = np.array([x_ang, y_ang, z_ang])
    
    block_data = {'pos_data' : hitbox, 'angle': angle}

    visbox_data = calc_note_visbox(block_position, block_angle)

    return block_data, visbox_data

def calc_note_visbox(block_position, block_angle):
    # Same thing as the above function but only the visable portion of the note

    hitbox = {'p0': {}, 'p1': {}}

    x_note_pos_relative_to_center = (block_position[0] + 0.5 - 2) * x_grid_distance        # Calculate the xCoordinates relative to the middle of the world.

    x_ang = 0            # Pitch, Yaw, Roll
    y_ang = np.arccos(x_note_pos_relative_to_center / (saber_hit_distance + 0.85))    #  saber length + 0.85 forward z hitbox. 0° is straight forwards, +angle is CC, -angle is clockwise.
    z_ang = block_angle

    # Initialize point positions for visbox caluclations in world space with dimentions x = 0.47m, y = 0.47m, z = 0.4m. Can optimize simple calculations later. -2 because the X center is at block grid position 2. 0.5 because we want to find the center of where it occupies
    p0 = np.array([(block_position[0] - 2 + 0.5) * x_grid_distance - (0.47 / 2),(block_position[1] - 2 + 0.5) * y_grid_distance - (0.47 / 2), 1 - 0.2])         # front left corner 
    p1 = np.array([(block_position[0] - 2 + 0.5) * x_grid_distance + (0.47 / 2),(block_position[1] - 2 + 0.5) * y_grid_distance + (0.47 / 2), 1 + 0.2])     # back right corner
    center = np.array([(block_position[0] - 2 + 0.5) * x_grid_distance, 0.25 + block_position[1] * y_grid_distance, 1])   # center of cube 
    
    # Apply rotation transformes
    rotated_p0 = rotate_point(p0, center, x_ang, y_ang, z_ang)
    rotated_p1 = rotate_point(p1, center, x_ang, y_ang, z_ang)
    
    # Apply grid positioning
    x0_pos = rotated_p0[0]
    x1_pos = rotated_p1[0]
    y0_pos = rotated_p0[1]
    y1_pos = rotated_p1[1]
    z0_pos = rotated_p0[2]
    z1_pos = rotated_p1[2]
    
    hitbox['p0'] = np.array([x0_pos, y0_pos, z0_pos])
    hitbox['p1'] = np.array([x1_pos, y1_pos, z1_pos])
    angle = np.array([x_ang, y_ang, z_ang])
    
    block_data = {'pos_data' : hitbox, 'angle': angle}

    return block_data

def calculate_bomb_hitbox(b_pos: list):
    # This program approximates sphears as 0.36m x 0.36m x 0.36 cubes bomb_offset[p0 = 0, p1 = 1][x = 0, y = 1]
    hitbox_x0 = (b_pos[0] - 2) * x_grid_distance + bomb_offset[0][0]
    hitbox_y0 = b_pos[1] * y_grid_distance + bomb_offset[0][1]
    hitbox_z0 = bomb_offset[0][2]
    hitbox_x1 = (b_pos[0] - 2) * x_grid_distance + bomb_offset[1][0]
    hitbox_y1 = b_pos[1] * y_grid_distance + bomb_offset[1][1]
    hitbox_z1 = bomb_offset[1][2]

    hitbox = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1])}
    visbox = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1])}     # temp, good approximation for now
    return hitbox, visbox

def calculate_wall_hitbox(x_pos, y_Pos, width, distance, height):
    hitbox_x0 = (x_pos - 2) * x_grid_distance
    hitbox_y0 = y_Pos * y_grid_distance
    # hitboxZ1 = -0.25                          
    hitbox_z0 = 1                                
    hitbox_x1 = (x_pos - 2 + width) * x_grid_distance
    hitbox_y1 = (y_Pos + height) * y_grid_distance
    hitbox_z1 = distance * metadata['njs'] + 1

    hitbox_pos = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1]), 'width': hitbox_x1}

    visbox_pos = {'p0': np.array([hitbox_x0, hitbox_y0, hitbox_z0 - 0.25]), 'p1': np.array([hitbox_x1, hitbox_y1, hitbox_z1]), 'width': hitbox_x1}   # Subtract 0.25 cause the visible portion of walls just built like that (cred: arcViewer)


    return hitbox_pos, visbox_pos

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
        print(f"Note Angle Snapping only works with 2 notes. There's {len(note_group)} notes here")
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
                mirrored_angle_from_position = mod(angle_from_position + 180, 360)  # Need to check both directions since there's no guarentee on the note order for simultaneous objects

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
                    note_angles.append(mod(grouped_notes[forloop_index]['a'], 360))
                else:
                    note_angles.append(mod(cut_direction_index[grouped_notes[forloop_index]['d']] + grouped_notes[forloop_index]['a'], 360))       # Get block angle, including precision angle

        else:       # Multiple notes at the same time can alter note angles
            note_angles = note_angle_snapping(grouped_notes)    # If there's 2 notes on the same beat, use another function to determine if and how much snapping.
        
        note_data.append({})
        note_data[-1]['beat'] = grouped_notes[0]['b']                          #Float
        note_data[-1]['objects'] = []
        note_data[-1]['njs'] = grouped_notes[0]['njs']

        for grouped_note_index in range(0, len(grouped_notes)):

            current_note = grouped_notes[grouped_note_index]

            hitbox_pos_data, visbox_pos_data = calc_note_hitbox([current_note['x'], current_note['y']], note_angles[grouped_note_index])      # type: ignore
            
            if current_note['has_chain']:
                link_num, link_pos, link_angle, link_beat = chain_curve(current_note['chain_data'])
                
            if current_note['d'] == 8:
                is_dot = True
            else:
                is_dot = False
            
            note_data[-1]['objects'].append({})

            # swingData[-1]['LRhand'] = handedness                            #Bool
            note_data[-1]['objects'][-1]['is_dot'] = is_dot                                  #Bool
            note_data[-1]['objects'][-1]['hitbox'] = hitbox_pos_data                         #Array of Vector3
            note_data[-1]['objects'][-1]['visbox'] = visbox_pos_data
            note_data[-1]['objects'][-1]['note_angle'] = note_angles[grouped_note_index]                         #Vector3
            note_data[-1]['objects'][-1]['pre_angle_disabled'] = current_note['pre_arc']             #Bool
            note_data[-1]['objects'][-1]['post_angle_disabled'] = current_note['post_arc']           #Bool
            note_data[-1]['objects'][-1]['has_chain'] = current_note['has_chain']                   #Bool
            if current_note['has_chain']:
                note_data[-1]['objects'][-1]['chain_data'] = {}
                note_data[-1]['objects'][-1]['chain_data']['link_num'] = link_num
                note_data[-1]['objects'][-1]['chain_data']['link_pos'] = link_pos
                note_data[-1]['objects'][-1]['chain_data']['link_angle'] = link_angle
                note_data[-1]['objects'][-1]['chain_data']['link_beat'] = link_beat

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
        bomb_data[-1]['objects'] = []
        bomb_data[-1]['njs'] = same_time[0]['njs']

        for j in range(0, len(same_time)):
            bomb_pos = [same_time[j]['x'], same_time[j]['y']]
            pos_data, vis_data = calculate_bomb_hitbox(bomb_pos)
            bomb_data[-1]['objects'].append({'hitbox': {'pos_data': {}}, 'visbox': {'pos_data': {}}})
            bomb_data[-1]['objects'][-1]['hitbox']['pos_data'] = pos_data     # We will approximate bombs to be cubes.
            bomb_data[-1]['objects'][-1]['visbox']['pos_data'] = vis_data

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
                if walls[wall_index]['d'] > 0:                  # Exclude fakewalls (negative duration)
                    same_time.append(walls[wall_index])
                    wall_index += 1
        
        wall_data.append({})     # Initialize new entry
        wall_data[-1]['beat'] = same_time[0]['b']
        group_beat_f = same_time[0]['b']
        wall_data[-1]['objects'] = []
        wall_data[-1]['njs'] = same_time[0]['njs']

        for j in range(0, len(same_time)):
            hitbox_data, visbox_data = calculate_wall_hitbox(same_time[j]['x'], same_time[j]['y'], same_time[j]['w'], same_time[j]['d'], same_time[j]['h'])
            wall_data[-1]['objects'].append({'hitbox': {'pos_data': {}}, 'visbox': {'pos_data': {}}})
            wall_data[-1]['objects'][-1]['beat_f'] = same_time[j]['b'] + same_time[j]['d']
            wall_data[-1]['objects'][-1]['hitbox']['pos_data'] = hitbox_data
            wall_data[-1]['objects'][-1]['length_seconds'] = beats_to_seconds(same_time[j]['d'], metadata['bpm'])
            wall_data[-1]['objects'][-1]['hitbox']['pos_data']['angle'] = np.array([0, 0, 0])
            wall_data[-1]['objects'][-1]['visbox']['pos_data'] = visbox_data
            
            if wall_data[-1]['objects'][-1]['beat_f'] > group_beat_f:
                group_beat_f = wall_data[-1]['objects'][-1]['beat_f']

        wall_data[-1]['beat_f'] = group_beat_f

        wall_index += 1
    
    return wall_data
    
def apply_rotation_data(object_data, rotation_data=[]):
    if len(rotation_data) == 0:
        return object_data
    
    rotation = 90        # Current platform rotation (yaw)
    rotation_index = 0   # Index of future incoming rotation event
    inclusive_flag = not rotation_data[rotation_index]['e']
    # test_rotation_changelog = []
    # if isinstance(object_data[0]['hitbox']['pos_data'], list):
    #     position_data_is_list = True
    # else:
    #     position_data_is_list = False

    for object_index in range(0, len(object_data)):     # Gasp, the double for looop
        for group_index in range(0, len(object_data[object_index]['objects'])):    # Thankfully the len of objectdata at objectindex is nearly always 1, and has a max reasonable size of 12. Either way, it scales with O(n) placed objects
            if rotation_index <= len(rotation_data) - 1:
                
                if inclusive_flag:
                    while object_data[object_index]['beat'] >= rotation_data[rotation_index]['b']:    # While loop to handle cases where there are multiple rotation events between objects
                        rotation += -rotation_data[rotation_index]['r']
                        # test_rotation_changelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                        if rotation_index + 1 <= len(rotation_data) - 1:
                            rotation_index += 1
                            inclusive_flag = not rotation_data[rotation_index]['e']
                        else:
                            break
                else:
                    while object_data[object_index]['beat'] > rotation_data[rotation_index]['b']:     # While loop to handle cases where there are multiple rotation events between objects
                        rotation += -rotation_data[rotation_index]['r']
                        # test_rotation_changelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                        if rotation_index + 1 <= len(rotation_data) - 1:
                            rotation_index += 1
                            inclusive_flag = not rotation_data[rotation_index]['e']
                        else:
                            break

                p0 = object_data[object_index]['objects'][group_index]['hitbox']['pos_data']['p0']
                p1 = object_data[object_index]['objects'][group_index]['hitbox']['pos_data']['p1']
                center = np.array([0,0,0])
                object_data[object_index]['objects'][group_index]['hitbox']['pos_data']['p0'] = rotate_point(p0, center, 0, rotation, 0)
                object_data[object_index]['objects'][group_index]['hitbox']['pos_data']['p1'] = rotate_point(p1, center, 0, rotation, 0)
                object_data[object_index]['objects'][group_index]['lane_rotation'] = mod(rotation, 360)
    
    return object_data

def create_rotation_list(rotation_data):
    if len(rotation_data) == 0:
        return []
    
    rotation = 90        # Current platform rotation (yaw)
    rotation_index = 0   # Index of future incoming rotation event
    inclusive_flag = not rotation_data[rotation_index]['e']

    rotation_array = []
    for rotation_index in range(0, len(rotation_data)):
        rotation += -rotation_data[rotation_index]['r']     # Negative because we're using counter clockwise rotation for calculations
        # test_rotation_changelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
        if rotation_index + 1 <= len(rotation_data) - 1:
            rotation_index += 1
            inclusive_flag = not rotation_data[rotation_index]['e']
        else:
            break   # No more entries in list

        rotation_array.append({'beat': rotation_data[rotation_index]['b'],'lane_rotation': mod(rotation, 360), 'inclusive_flag': inclusive_flag})
    
    return rotation_array

# object_data: accepts the formatted_data format
# partial_matching was supposed to be if only a part of the hitbox is in the time selection, not important (For now)
search_frequency = 64           # The size of search bucket when splitting lists. Possible to replace with the sqrt of the list size.
def objects_within_range(object_data, time, partial_matching=True, time_range=1, key='beat', true_for_range_in_seconds=False, exclude_within_saber_distance=False, return_indexs=False):

    if len(object_data) == 0:
        return []
    
    first_object_time = object_data[0][key]
    last_object_time = object_data[-1][key]

    if true_for_range_in_seconds:
        time_range = time_range * metadata['bpm'] / 60

    if time - time_range > last_object_time:    # If there's no objects around the requested time within range, then there's no data of interest.
        return []
    
    if time + time_range < first_object_time:
        return []
    
    object_data_length = len(object_data)       # Setup search parameters
    search_depth = np.round(object_data_length / search_frequency)    # Use a number to ensure square root properties. Maybe switch to a square root method insead of 32
    
    search_index = int(np.round(object_data_length / 2))                # Good place to start searching

    if search_depth >= 1:
        search_count = 0
        
        while search_depth > search_count:      # Use division to quickly but roughly locate the correct index

            if object_data[search_index][key] < time:
                new_search_index = int(np.round(search_index + search_index / 2))

            if object_data[search_index][key] > time:
                new_search_index = int(np.round(search_index - search_index / 2))

            search_index = new_search_index

            search_index = min(search_index, object_data_length - 1)   # Clamp the search index to within accessable memory
            search_index = max(search_index, 0)

            if abs(object_data[search_index][key] - time) <= time_range:     # Lucky, we're within range, good enough to break out of this loop early
                break

            search_count += 1

    index_start = int(search_index) # Find the starting index to define relavent index points on the object list

    if exclude_within_saber_distance:
        # TODO update this from a cube to a sphear
        # distance_from_note_time_in_beats = distance_to_beats(metadata['bpm'], metadata['njs'], saber_hit_distance)  # saber_hit_distance: 0m = hilting, 1m = tipping
        # lower_bound = time + distance_from_note_time_in_beats
        lower_bound = time
    else:
        lower_bound = time - time_range

           
    while object_data[index_start][key] < lower_bound:      # In case the index start-point starts behind the time variable, bring it ahead for the next while loop.
        index_start += 1
        if index_start >= object_data_length - 1:
            break
    while object_data[index_start - 1][key] > lower_bound:     # While the index time is greater than the lower bound
        index_start -= 1
        if index_start == 0:
            break

    index_end = int(search_index)
    
    while object_data[index_end][key] > time + time_range:      # In case the index end point starts ahead the time variable, bring it back for the next while loop.
        if index_end > 0:
            index_end -= 1
        else:
            break
    while object_data[index_end + 1][key] < time + time_range:     
        index_end += 1
        if index_end >= object_data_length - 1:
            break

    # Verify that all objects are within range (might be commented out later)
    object_return = []
    for verification in range(index_start, index_end + 1):
        if abs(object_data[verification][key] - time) <= time_range:
            object_return.append(object_data[verification])
        else:
            print(f"Object at index {verification} is out of range")
    
    if return_indexs:
        return object_return, [index_start, index_end]
    else:
        return object_return

# Returns a list of objects within a specified range at every time index
# Time_range should be much larger than the time steps.
def objects_within_range_array(object_data, time_array, partial_matching=True, true_for_range_in_seconds=False, time_range=1, key='beat', exclude_within_saber_distance2=False):

    if true_for_range_in_seconds:
        time_range = time_range * metadata['bpm'] / 60
    
    timed_object_array = []

    first_object_time = object_data[0][key]
    last_object_time = object_data[-1][key]
    
    in_range = False
    find_first_objects = False
    
    for time_index, time in enumerate(time_array):          # time_index: current index of time_array, time: current beat at time_index in time_array
        if time + time_range < first_object_time:    # Quickly iterate through beginning time indexes with out of range objects
            objects = []
        else:
            if not in_range:    # This will activate only once per function call
                first_time_index = time_index
                in_range = True
                find_first_objects = True
        
        if in_range:
            if find_first_objects:
                objects, returned_indexes = objects_within_range(object_data=object_data, time=time, partial_matching=partial_matching, true_for_range_in_seconds=true_for_range_in_seconds, time_range=time_range, key=key, exclude_within_saber_distance=exclude_within_saber_distance2, return_indexs=True)
                objects = deque(objects)    # Convert from list into queue
                start_index = returned_indexes[0]
                end_index = returned_indexes[1]
                find_first_objects = False

            # Find the new ending index
            if end_index + 1 <= len(object_data) - 1:    # Check to make sure array access is valid
                while object_data[end_index + 1]['beat'] < time + time_range:
                    objects.append(object_data[end_index + 1])
                    end_index += 1
                    if end_index + 1 <= len(object_data) - 1:
                        pass
                    else:
                        break   # We hit the last object in the list.
            
            if exclude_within_saber_distance2:
                # TODO update this from a cube to a sphear
                # saber_distance_from_note_time_in_beats = distance_to_beats(metadata['bpm'], metadata['njs'], saber_hit_distance)  # saber_hit_distance: 0m = hilting, 1m = tipping
                # lower_bound = time + saber_distance_from_note_time_in_beats # Exclude all notes within range and behind player
                lower_bound = time      # The arrival time is already 1m away from the player :)
            else:
                lower_bound = time - time_range

            if start_index <= len(object_data) - 1:    # Check to make sure array access is valid
                while object_data[start_index]['beat'] < lower_bound:
                    
                    if len(objects) > 0:
                        objects.popleft()

                    if start_index + 1 <= len(object_data) - 1:
                        start_index += 1
                    else:
                        break   # We hit the last object in the list.

        timed_object_array.append(list(objects))

    return timed_object_array

def walls_within_range(wall_data, time, time_range=1, true_for_range_in_seconds=False, return_indexs=False):
    if len(wall_data) == 0:
        return -1
    
    key = 'beat'
    key_f = 'beat_f'

    first_object_time = wall_data[0][key]

    last_object_time = 0        # Init
    wall_data_len = 0           # Init
    for grouped_walls in wall_data:
        for wall in grouped_walls['objects']:
            if wall[key_f] > last_object_time:
                last_object_time = wall[key_f]
        wall_data_len += 1              # Good chance to get the true number of walls, not sure if it'll be used.

    
    if true_for_range_in_seconds:
        time_range = time_range * metadata['bpm'] / 60
    
    if time - time_range > last_object_time:    # If there's no objects around the requested time within range, then there's no data of interest.
        return []
    if time + time_range < first_object_time:
        return []
    
    object_data_length = len(wall_data)       # Setup search parameters
    
    # Find the starting index to define relavent index points on the object list
    lower_bound = time - time_range
    upper_bound = time + time_range
    object_return = []
    first_wall = False
    wall_indexes = []

    # 6 cases for wall matching
    # if beat < lower and beat_f < lower                                            0
    # if beat > lower and beat_f > lower                                            0
    # if beat < lower and beat < upper and beat_f > lower and beat_f < upper        1
    # if beat < lower and beat < upper and beat_f > lower and beat_f > upper        1
    # if beat > lower and beat < upper and beat_f > lower and beat_f < upper        1
    # if beat > lower and beat < upper and beat_f > lower and beat_f > upper        1
    # beat < upper and beat_f > lower is true whenever the wall is within range
    # Since there's no need to differentiate between the types of wall vs range overlap, we can simplify to "beat < upper and beat_f > lower"
        
    for wall_data_index in range(0, len(wall_data)):
        if wall_data[wall_data_index][key] <= upper_bound and wall_data[wall_data_index][key_f] >= lower_bound:         # Check the grouped wall statistics to see if there's any walls of interest.
            object_return.append({'objects': []})       # Initialize the 'object' key as list
            object_return[-1]['beat'] = wall_data[wall_data_index][key]
            object_return[-1]['beat_f'] = wall_data[wall_data_index][key_f]
            
            for grouped_wall_index in range(0, len(wall_data[wall_data_index]['objects'])):
                if wall_data[wall_data_index][key] <= upper_bound and wall_data[wall_data_index]['objects'][grouped_wall_index][key_f] >= lower_bound:       # Starting beat inside wall_data[wall_data_index]['objects'][grouped_wall_index] all share the same starting beat, so we don't need to check it again.
                    object_return[-1]['objects'].append(wall_data[wall_data_index]['objects'][grouped_wall_index])
            
            # if not first_wall:      # Capture the first valid wall index.
            #     wall_start_index = wall_data_index
            #     first_wall = True
            
            wall_indexes.append(wall_data_index)            # Create a list of indexs to reference.
        
        elif wall_data[wall_data_index][key] > upper_bound:
            wall_end_index = wall_data_index - 1
            break   # No walls start forwards, then backwards, so we can break the loop early.
    
    if return_indexs:
        # return object_return, [wall_start_index, wall_end_index]
        return object_return, wall_indexes
    else:
        return object_return

def walls_within_range_array(wall_data, time_array, true_for_range_in_seconds=False, time_range=1):

    if len(wall_data) == 0:
        return -1
    
    key = 'beat'
    key_f = 'beat_f'

    first_object_time = wall_data[0][key]

    last_object_time = 0        # Init
    total_num_walls = 0           # Init
    for grouped_walls in wall_data:
        for wall in grouped_walls['objects']:
            if wall[key_f] > last_object_time:
                last_object_time = wall[key_f]
            total_num_walls += 1              # Good chance to get the true number of walls, not sure if it'll be used.
    
    in_range = False
    find_first_objects = False
    timed_object_array = []
    wall_data_index = 0
    
    for time_index, time in enumerate(time_array):          # time_index: current index of time_array, time: current beat at time_index in time_array
        lower_bound = time - time_range
        upper_bound = time + time_range
        
        
        if upper_bound < first_object_time:    # Quickly iterate through beginning time indexes with out of range objects
            objects = []
        else:
            if not in_range:    # This will activate only once per function call
                first_time_index = time_index
                in_range = True
                find_first_objects = True
        
        if in_range:
            if find_first_objects:
                objects_return, wall_indexes = walls_within_range(wall_data, time, true_for_range_in_seconds=true_for_range_in_seconds, time_range=time_range, return_indexs=True)
                objects = deque(objects_return)    # Convert from list into queue
                wall_indexes = deque(wall_indexes)
                # wall_index_of_first_object = wall_indexes[0]        # Load the starting index
                # wall_index_of_last_object = wall_indexes[1]         # Load the ending index  
                find_first_objects = False
                wall_data_index = wall_indexes[-1]                      # Grab the last 

            else:
                fl_wall_index = 0
                
                for fl_1 in range(0, len(objects) - 1):   # Remove walls that are no longer in view (range)
                    fl_group_index = 0
                    
                    for fl2 in range(0, len(objects[fl_wall_index]['objects'])):
                        if objects[fl_wall_index]['objects'][fl_group_index][key_f] < lower_bound:

                            del objects[fl_wall_index]['objects'][fl_group_index]
                            fl_group_index -= 1
                        fl_group_index += 1
                    
                        if len(objects[fl_wall_index]['objects']) == 0:
                            del objects[fl_wall_index]
                            # del wall_indexes[fl_wall_index]
                            fl_wall_index -= 1

                    fl_wall_index += 1

                # Walls are sorted by time and grouped if they start on the same beat, therefore we only need to check a set of walls once
                
                if wall_data_index + 1 <= len(wall_data) - 1:    # Check if there's more walls of interest
                    if wall_data[wall_data_index + 1][key] <= upper_bound:
                        
                        objects.append({'objects': []})
                        objects[-1]['beat'] = wall_data[wall_data_index + 1][key]
                        objects[-1]['beat_f'] = wall_data[wall_data_index + 1][key_f]

                        for grouped_wall_index in range(0, len(wall_data[wall_data_index + 1]['objects'])):
                            objects[-1]['objects'].append(wall_data[wall_data_index + 1]['objects'][grouped_wall_index])
                        # wall_indexes.append(wall_data_index + 1)

                        if wall_data_index - 1 < len(wall_data) - 1:
                            wall_data_index += 1
                        # else:
                        #     # break
                        #     pass  

        timed_object_array.append(pickle.loads(pickle.dumps(list(objects))))

    return timed_object_array

# ------------------------ Algo specific functions ------------------------

def load_starting_head_pos():   # A players height is used to offset objects (notes, wall,s bombs, etc.) up or down. We don't need to include this so our simulated player will be very short
    return np.array([2 * x_grid_distance, 2 * y_grid_distance, 0])     # in a 4x3 grid (xy) with position 2x and 2y, the player should be in the middle (x) and top 2/3'rds of the grid and can see between the middle and top notes.

def define_head_pos(wall_data, bomb_data, rotation_data):



    pass



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

# Use the block before and after to calculate the best position/angle. 
# Weight the influence of the surrounding blocks by distance (closer has more influence)
# Weight of the block to hit is 0.5, with the surrounding blocks sharing the other 0.5. How much the weight is split between them depends on their distances to the block to hit.
# Arrow note block angle adjustment cannot exceed +-60°
# Block position adjustment limitation are...
def target_hit_data(note_data, note_data_index):
    hand_pos = np.array([])
    




    
    return -1


def pos_pathing(start_pos, end_pos, skill_set):
    pos_accel = skill_set['positionAcceleration']
    ang_accel = skill_set['angleAcceleration']
    average_acc = skill_set['accuracy']
    max_acceleration = skill_set
    min_resolution = 50
    max_gap = 0.05
    starting_velocity = 0
    ending_velocity = 0

    advanced_s_curve_path(start_pos, end_pos, max_acceleration, min_resolution, max_gap, starting_velocity, ending_velocity)    # Need to run this twice, one for position and one for angles.

def angle_pathing():
    pass

# Needs to modify swing path positioning to avoid bombs and wrong notes
def badcut_pathing(swing_path, wrong_color_note_data, bomb_data):
    pass

def vision_analysis(path):
    pass

def path_analysis(path):
    vision_analysis(path)
    pass

def swing_path(formatted_map_data, handedness, skill_set):
    
    
    if handedness:
        note_data = formatted_map_data['left_note_data']
        other_note_data = formatted_map_data['right_note_data']
    else:
        note_data = formatted_map_data['right_note_data']
        other_note_data = formatted_map_data['left_note_data']
    bomb_data = formatted_map_data['bomb_data']
    wall_data = formatted_map_data['wall_data']
    metadata = formatted_map_data['metadata']
    lane_rotation_data = formatted_map_data['rotation_events']

    # jump_distance = skill_set['jump_distance']
    jump_distance = metadata['jump_distance']

    accGraph = [[]]
    averageAcc = 0.0    # The acc
    readibility = 0.0   # How much vision block
    rotation = 0.0      # How much roll+yaw angle
    speed = 0.0         # How much pitch angle
    position = 0.0      # How much position
    noramlity = 0.0     # How common the pattern is

    last_object_time = max(note_data[-1]['beat'], other_note_data[-1]['beat'], bomb_data[-1]['beat'], wall_data[-1]['beat_f'])

    time_step = (1 / refresh_rate) * metadata['bpm'] / 60     # In beats, no need to ever convert to seconds
    # time_data = range(0, last_object_time, time_step)   #  Build an array of time values to determine frames to use. Range function doesn't work with float values ;-;
    # time_steps = [t * time_step for t in range(0, last_object_time)]

    time_steps = range_float(0, last_object_time, time_step)
    t0 = time.time()
    # TODO, calculate the best time range to reduce vision blocks, or use the reaction time formula, or bake set reaction times for every skill level.
    notes_of_interest_at_time_steps = objects_within_range_array(note_data, time_steps, time_range=jump_distance, exclude_within_saber_distance2=True)
    other_notes_of_interest_at_time_steps = objects_within_range_array(other_note_data, time_steps, time_range=jump_distance, exclude_within_saber_distance2=True)
    bombs_of_interest_at_time_steps = objects_within_range_array(bomb_data, time_steps, time_range=jump_distance)
    walls_of_interest_at_time_steps = walls_within_range_array(wall_data, time_steps, time_range=jump_distance)
    t1 = time.time()

    

    index = 0
    head_data_at_time_steps = []

    head_pos = load_starting_head_pos()
    head_rotation = 90          # Straight forwards. Lane rotation and
    ave_rotation_queue = deque()
    lane_rotation_data_index = 0
    current_lane_rotation = lane_rotation_data[lane_rotation_data_index]['lane_rotation']

    # We could simulate acceleration to simulate inertia, but it's not important.
    head_rotation_rate = 45         # In degrees / sec
    head_position_rate = 0.5        # In m/s

    for time_index, time_beats in enumerate(time_steps):

        notes_of_interest = notes_of_interest_at_time_steps[time_index]
        other_notes_of_interest = other_notes_of_interest_at_time_steps[time_index]
        bombs_of_interest = bombs_of_interest_at_time_steps[time_index]
        walls_of_interest = walls_of_interest_at_time_steps[time_index]

        # First calculate head position, then vision blocks
        # I need:
        # Position of area with least walls
        # Vector from middle to area with least walls
        # Vector from headpos to area with least walls
        # 
        # Apply resistive factors to headpos movement components when movement vector is away from center and sufficient distance.

        moved_past_head_beat_offset = distance_to_beats(metadata['bpm'], metadata['njs'], 1)      # Beat 0 i.e. if the note has "arrived" is 1m in front of the player. THerefore for vision checks, we need to subtract this from the beat/add to the time check
        
        walls_to_miss = []
        walls_to_avoid = []
        for wall_of_int in walls_of_interest:
            for wall in wall_of_int['objects']:                 # Wall at player
                position = wall['visbox']['pos_data']
                rotation = wall['lane_rotation']
                if time_beats + moved_past_head_beat_offset >= wall_of_int['beat'] and time_beats + moved_past_head_beat_offset < wall['beat_f']:
                    distance_beats = 0
                    distance_seconds = 0
                    time_weight = 1
                    walls_to_miss.append({'distance_beats': distance_beats, 'position': position, 'rotation': rotation, 'weight': time_weight})              # Walls must be avoided by the head for a period of time. Lets keep track of them
                else:
                    if time_beats + moved_past_head_beat_offset <= wall_of_int['beat']:        # Wall ahead of player
                        distance_beats = wall_of_int['beat'] - time_beats + moved_past_head_beat_offset     # Distance from wall to players head
                        distance_seconds = beats_to_seconds(distance_beats, metadata['bpm'])
                        time_weight = 0.05 ** distance_seconds      # A weight formula

                    else:       # Wall behind player
                        distance_beats = wall['beat_f'] - time_beats + moved_past_head_beat_offset
                        # distance_seconds = beats_to_seconds(distance_beats, metadata['bpm'])
                        time_weight = 0
                # Add each wall
                walls_to_avoid.append({'distance_beats': distance_beats, 'position': position, 'lane_rotation': rotation, 'weight': time_weight})
        
        bombs_to_avoid = []
        for bomb_of_int in bombs_of_interest:
            for bomb in bomb_of_int['objects']: 
                position = bomb['visbox']['pos_data']
                rotation = bomb['lane_rotation']
                if time_beats + moved_past_head_beat_offset > bomb_of_int['beat']:      # bomb moved past the player
                    distance_beats = bomb_of_int['beat'] - time_beats + moved_past_head_beat_offset
                    # distance_seconds = beats_to_seconds(distance_beats, metadata['bpm'])
                    time_weight = 0     
                else:     # Bomb ahead of player
                    distance_beats = bomb_of_int['beat'] - time_beats + moved_past_head_beat_offset
                    # distance_seconds = beats_to_seconds(distance_beats, metadata['bpm'])
                    time_weight = 0 
                bombs_to_avoid.append({'distance_beats': distance_beats, 'position': position, 'lane_rotation': rotation, 'weight': time_weight})
                
        # Not going to use notes to calculate head pos

        total_length = len(walls_to_miss) + len(walls_to_avoid) + len(bombs_to_avoid)

        # Head rotation controller
        if time_beats >= lane_rotation_data[lane_rotation_data_index]['beat']:
            if lane_rotation_data[lane_rotation_data_index]['inclusive_flag'] or time_beats > lane_rotation_data[lane_rotation_data_index]['beat']:
                lane_rotation_data_index += 1
                current_lane_rotation = lane_rotation_data[lane_rotation_data_index]['lane_rotation']

        if abs(current_lane_rotation - head_rotation) > time_step * head_rotation_rate:
            if current_lane_rotation - head_rotation > 0:
                head_rotation += time_step * head_rotation_rate         # seconds * degrees/s = degrees
            elif current_lane_rotation - head_rotation < 0:
                head_rotation -= time_step * head_rotation_rate
        else:
            head_rotation = current_lane_rotation

        # objects_to_avoid = sorted(walls_to_avoid + bombs_to_avoid, key=lambda d: d['distance_beats'])
        # TODO Run bombs first, then refine with walls_avoid for smooth head pathing. then check walls_miss to make sure all walls are missed
        for wall in walls_to_avoid:
            wall_middle_X = wall['position']['p0'][0] + np.sin(np.radians(wall['lane_rotation'])) * wall['position']['width'] / 2
            wall_middle_Y = (wall['position']['p1'][1] - wall['position']['p0'][1]) / 2
            wall_middle_Z = wall['position']['p0'][2] + np.cos(np.radians(wall['lane_rotation'])) * wall['position']['width'] / 2
            wall_middle = np.array([wall_middle_X, wall_middle_Y, wall_middle_Z])
            
            wall_delta = wall_middle - head_pos 
            theta_to_player = mod(np.arctan2(wall_delta[2], wall_delta[0]) - wall['lane_rotation'], 360)  # Subtract lane rotation
            
            
            if theta_to_player - head_rotation < 90 or theta_to_player - head_rotation > 270:
                head_pos[0] += np.cos(np.radians(head_rotation)) * head_position_rate * wall['weight']  # Use head_rotation to calculate the magnitude of XZ movement
                head_pos[2] += np.sin(np.radians(head_rotation)) * head_position_rate * wall['weight']
            else:
                head_pos[0] -= np.cos(np.radians(head_rotation)) * head_position_rate * wall['weight']
                head_pos[2] -= np.sin(np.radians(head_rotation)) * head_position_rate * wall['weight']

        for bomb in bombs_to_avoid: # TODO verify
            wall_middle_X = wall['position']['p0'][0] + np.cos(np.radians(wall['rotation'])) * wall['position']['width'] / 2  # Here cos and sin are swapped when optimizing mod(wall['rotation'] - 90, 360). the -90 comes from converting game rotation to convential math. I did it this way because I was lazy and adopted the game's rotation notation but reversed (counter-clockwise). TODO make the XZ plane's rotation origins start pointing East (right)
            wall_middle_Y = (wall['position']['p1'][1] - wall['position']['p0'][1]) / 2
            wall_middle_Z = wall['position']['p0'][2] + np.sin(np.radians(wall['rotation'])) * wall['position']['width'] / 2
            wall_middle = np.array([wall_middle_X, wall_middle_Y, wall_middle_Z])
            # rotated_wall_middle = rotate_y(wall_middle, np.array([0,0,0]), wall['rotation']) # rotate wall_center around the center. why lol
            
            wall_delta = wall_middle - head_pos
            theta_to_player = mod(np.arctan2(wall_delta[2], wall_delta[0]) - mod(wall['rotation'] - 90, 360), 360)  # Subtract lane rotation
            
            
            if theta_to_player - head_rotation < 90 or theta_to_player - head_rotation > 270:
                head_pos[0] += np.cos(np.radians(head_rotation)) * head_position_rate * wall['weight']  # Use head_rotation to calculate the magnitude of XZ movement
                head_pos[2] += np.sin(np.radians(head_rotation)) * head_position_rate * wall['weight']
            else:
                head_pos[0] -= np.cos(np.radians(head_rotation)) * head_position_rate * wall['weight']
                head_pos[2] -= np.sin(np.radians(head_rotation)) * head_position_rate * wall['weight']
            

        head_data_at_time_steps.append({})


        # Vision block calculations
        walls_visionblock = []
        walls_visionblock.append(wall)          # At this distance, walls will visionblock


        
        
        


    # note_path = []
    
    # for note_data_index in range(0, len(note_data)):

    #     if note_data_index == 0:
    #         start_pos = (note_data[note_data_index]['hitbox']['pos_data']['p0'] + note_data[note_data_index]['hitbox']['pos_data']['p1']) / 2
    #     else:
    #         start_pos = (note_data[note_data_index - 1]['hitbox']['pos_data']['p0'] + note_data[note_data_index - 1]['hitbox']['pos_data']['p1']) / 2
        
    #     note_path.append({})

    #     head_pos = define_head_pos()
    #     note_path[-1]['target_hit_pos'] = target_hit_data(note_data, note_data_index)                            # Find target hand position for swing



    #     note_path[-1]['basic_pos_path'] = pos_pathing(start_pos, note_path[-1]['hit_pos'], skill_set)       # Build basic path from last note to current note
    #     note_path[-1]['basic_angle_path'] = angle_pathing()

    #     note_path[-1]['path_data'] = badcut_pathing(note_path[-1], other_note_data, bomb_data)         # Adjust path to avoid bombs

    #     note_path[-1]['path_analysis'] = path_analysis(note_path[-1]['path_data'])  # Analyse scoring metrics

    # for note_path_index in range(0, len(note_path)):
    #     readibility = vision_analysis

    return accGraph


def difficulty_analysis(formatted_map_data, handedness):
    skillList = []      # positionAcceleration m/s^2, angleAcceleration °/s^2, accuracy in average acc
    # skillList.append({'positionAcceleration': 4294967295, 'angleAcceleration': 4294967295, 'accuracy': 15})
    skillList.append({'positionAcceleration': 100, 'angleAcceleration': 3600, 'accuracy': 15})

    for skillListIndex in range(0, len(skillList)):
        skillList[skillListIndex]['swingPathReturn'] = swing_path(formatted_map_data, handedness, skillList[skillListIndex])

    return skillList



# ------------------------ Function Execution ------------------------

def techOperations(B_mapData: dict, metadata: dict, isuser=True, verbose=True):
    B_LeftNoteData = split_map_data(B_mapData, 0)     # Parse mapdata into separate varables to pass into functions
    B_RightNoteData = split_map_data(B_mapData, 1)
    B_BombData = split_map_data(B_mapData, 2)
    B_WallData = split_map_data(B_mapData, 3)
    left_note_data = create_note_list(dict(B_LeftNoteData))    # Create extract object data with game mechanics
    right_note_data = create_note_list(dict(B_RightNoteData))   
    bomb_data = create_bomb_list(list(B_BombData))
    wall_data = create_wall_list(list(B_WallData))
    rotation_data = create_rotation_list(B_mapData['rotationEvents'])
    
    left_note_data = apply_rotation_data(left_note_data, B_mapData['rotationEvents'])
    right_note_data = apply_rotation_data(right_note_data, B_mapData['rotationEvents'])
    bomb_data = apply_rotation_data(bomb_data, B_mapData['rotationEvents'])
    wall_data = apply_rotation_data(wall_data, B_mapData['rotationEvents'])
    

    formatted_map_data = {}
    formatted_map_data['left_note_data'] = left_note_data
    formatted_map_data['right_note_data'] = right_note_data
    formatted_map_data['bomb_data'] = bomb_data
    formatted_map_data['wall_data'] = wall_data
    formatted_map_data['metadata'] = metadata
    formatted_map_data['rotation_events'] = rotation_data

    left_results = difficulty_analysis(formatted_map_data, 0)
    right_results = difficulty_analysis(formatted_map_data, 1)
    
    LeftSwingData = []
    RightSwingData = []

    if isuser:
        tech = 1
        print(f"Calculated Tech = {round(tech, 2)}")  # Put Breakpoint here if you want to see
        # print(f"Calculated nerf = {round(low_note_nerf, 2)}")
        # print(f"Calculated balanced tech = {round(balanced_tech, 2)}")
        # print(f"Calculated balanced pass diff = {round(balanced_pass, 2)}")
        
    return 0     # returnDict


def mapCalculation(mapData, metadata, isuser=True, verbose=True):
    t0 = time.time()
    newMapData = map_prep(mapData, metadata)
    data = techOperations(newMapData, metadata, isuser, verbose)
    t1 = time.time()
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

    # Besides start_beat_offset, the other variables could change while playing, so these values may be bound to objects, or tracked globally.
    metadata = {'bpm': infoData['_beatsPerMinute']}
    metadata['njs'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpMovementSpeed']
    metadata['start_beat_offset'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpStartBeatOffset']
    
    metadata['half_jump_duration'] = calculate_half_jump_duration(metadata['njs'], metadata['start_beat_offset'], metadata['bpm'])
    metadata['jump_distance'] = caculate_jump_distance(metadata['njs'], metadata['start_beat_offset'], metadata['bpm'])

    mapCalculation(mapData, metadata, True, True)
    print("Done")
    input()