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
xGridDistance = 0.43636   # In meters
yGridDistance = 0.525   # In meters, averaged 0.55m between bottom and middle row, 0.5m between middle and top row.
#Bombs are roughly equal in size to note badcut hitboxes @ 0.36m
bombOffset = [[xGridDistance / 2 - 0.18, yGridDistance / 2 - 0.18, 1 - 0.18], [xGridDistance / 2 + 0.18, yGridDistance / 2 + 0.18, 1 + 0.18]]     
saberHitDistance = 0.5        # The z position where the hitbox will hit the saber. 0 = hilting, 0.5 = mid, 1 = tipping

# ------------------------ Base functions ------------------------

def average(lst, setLen=0):  # Returns the averate of a list of integers
    if len(lst) > 0:
        if setLen == 0:
            return sum(lst) / len(lst)
        else:
            return sum(lst) / setLen
    else:
        return 0

def reverseCutDirection(angle):
    if angle >= 180:
        return angle - 180
    else:
        return angle + 180

def swapPositions(lis: list, pos1, pos2):
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

# Not the correct way to define function input type, but it'll help someone.
def PointOnQuadBezier(p0: np.array, p1: np.array, p2: np.array, t):
    return (math.pow(1 - t, 2) * p0) + (2 * (1 - t) * t * p1) + (math.pow(t, 2) * p2)

def AngleOnQuadBezier(p0: np.array, p1: np.array, p2: np.array, t):
    derivative = list((2 * (1 - t) * (p1 - p0)) + (2 * t * (p2 - p1)))      # Pretty sure can remove "list()" but will do later. Not important
    return mod(math.degrees(math.atan2(derivative[1], derivative[0])), 360)

def PointOnCubicBezier(p0: np.array, p1: np.array, p2: np.array, p3: np.array, t):
    return (math.pow(1 - t, 3) * p0) + (3 * math.pow(1 - t, 2) * t * p1) + (3 * (1 - t) * math.pow(t, 2) * p2) + (math.pow(t, 3) * p3)

def AngleOnCubicBezier(p0: np.array, p1: np.array, p2: np.array, p3: np.array, t):
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
def rotatePoint(p0, center, pitch, yaw, roll):
    pitch = np.deg2rad(pitch)
    yaw = np.deg2rad(yaw)
    roll = np.deg2rad(roll)

    new_p0 = rotate_x(p0, center, pitch)
    new_p0 = rotate_y(new_p0, center, -yaw)
    new_p0 = rotate_z(new_p0, center, roll)
    return new_p0

def combineAndSortList(array1, array2, key):
    combinedArray = array1 + array2
    combinedArray = sorted(combinedArray, key=lambda x: x[f'{key}'])  # once combined, sort by time
    return combinedArray

# ------------------------ Map parsing and information extraction functions ------------------------

def V2_to_V3(V2mapData: dict):    # Convert V2 JSON to V3
    newMapData = {'colorNotes':[], 'bombNotes':[], 'obstacles':[], 'sliders':[], 'burstSliders':[]}
    for i in range(0, len(V2mapData['_notes'])):
        if V2mapData['_notes'][i]['_type'] in [0, 1]:
            newMapData['colorNotes'].append({'b': V2mapData['_notes'][i]['_time']})
            newMapData['colorNotes'][-1]['x'] = V2mapData['_notes'][i]['_lineIndex']
            newMapData['colorNotes'][-1]['y'] = V2mapData['_notes'][i]['_lineLayer']
            newMapData['colorNotes'][-1]['a'] = 0
            newMapData['colorNotes'][-1]['c'] = V2mapData['_notes'][i]['_type']
            newMapData['colorNotes'][-1]['d'] = V2mapData['_notes'][i]['_cutDirection']
        elif V2mapData['_notes'][i]['_type'] == 3:      # Bombs
            newMapData['bombNotes'].append({'b': V2mapData['_notes'][i]['_time']})
            newMapData['bombNotes'][-1]['x'] = V2mapData['_notes'][i]['_lineIndex']
            newMapData['bombNotes'][-1]['y'] = V2mapData['_notes'][i]['_lineLayer']
    for i in range (0, len(V2mapData['_obstacles'])):
        newMapData['obstacles'].append({'b': V2mapData['_obstacles'][i]['_time']})
        newMapData['obstacles'][-1]['x'] = V2mapData['_obstacles'][i]['_lineIndex']
        if V2mapData['_obstacles'][i]['_type']:  # V2 wall type defines crouch or full walls
            newMapData['obstacles'][-1]['y'] = 2
            newMapData['obstacles'][-1]['h'] = 3
        else:
            newMapData['obstacles'][-1]['y'] = 0
            newMapData['obstacles'][-1]['h'] = 5
        newMapData['obstacles'][-1]['d'] = V2mapData['_obstacles'][i]['_duration']
        newMapData['obstacles'][-1]['w'] = V2mapData['_obstacles'][i]['_width']


    return newMapData

def V3_3_0_to_V3(V3_0_0mapData: dict):
    newMapData = copy.deepcopy(V3_0_0mapData)
    for i in range(0, len(newMapData['bpmEvents'])):
        newMapData['bpmEvents'][i]['b'] = newMapData['bpmEvents'][i].get('b', 0)
        newMapData['bpmEvents'][i]['m'] = newMapData['bpmEvents'][i].get('m', 0)

    # for i in range(0, len(newMapData['rotationEvents'])): Used for lighting
    #     newMapData['rotationEvents'][i]['b'] = newMapData['rotationEvents'][i].get('b', 0)
    #     newMapData['rotationEvents'][i]['e'] = newMapData['rotationEvents'][i].get('e', 0)
    #     newMapData['rotationEvents'][i]['r'] = newMapData['rotationEvents'][i].get('r', 0)

    for i in range(0, len(newMapData['colorNotes'])):
        newMapData['colorNotes'][i]['b'] = newMapData['colorNotes'][i].get('b', 0)
        newMapData['colorNotes'][i]['x'] = newMapData['colorNotes'][i].get('x', 0)
        newMapData['colorNotes'][i]['y'] = newMapData['colorNotes'][i].get('y', 0)
        newMapData['colorNotes'][i]['a'] = newMapData['colorNotes'][i].get('a', 0)
        newMapData['colorNotes'][i]['c'] = newMapData['colorNotes'][i].get('c', 0)
        newMapData['colorNotes'][i]['d'] = newMapData['colorNotes'][i].get('d', 0)
    
    for i in range(0, len(newMapData['bombNotes'])):
        newMapData['bombNotes'][i]['b'] = newMapData['bombNotes'][i].get('b', 0)
        newMapData['bombNotes'][i]['x'] = newMapData['bombNotes'][i].get('x', 0)
        newMapData['bombNotes'][i]['y'] = newMapData['bombNotes'][i].get('y', 0)
    
    for i in range(0, len(newMapData['obstacles'])):
        newMapData['obstacles'][i]['b'] = newMapData['obstacles'][i].get('b', 0)
        newMapData['obstacles'][i]['x'] = newMapData['obstacles'][i].get('x', 0)
        newMapData['obstacles'][i]['y'] = newMapData['obstacles'][i].get('y', 0)
        newMapData['obstacles'][i]['d'] = newMapData['obstacles'][i].get('d', 0)
        newMapData['obstacles'][i]['w'] = newMapData['obstacles'][i].get('w', 0)
        newMapData['obstacles'][i]['h'] = newMapData['obstacles'][i].get('h', 0)

    for i in range(0, len(newMapData['sliders'])):   # Arcs not implemented in the also, so just leave it out.
        newMapData['sliders'][i]['b'] = newMapData['sliders'][i].get('b', 0)
        newMapData['sliders'][i]['c'] = newMapData['sliders'][i].get('c', 0)
        newMapData['sliders'][i]['x'] = newMapData['sliders'][i].get('x', 0)
        newMapData['sliders'][i]['y'] = newMapData['sliders'][i].get('y', 0)
        newMapData['sliders'][i]['d'] = newMapData['sliders'][i].get('d', 0)
        newMapData['sliders'][i]['mu'] = newMapData['sliders'][i].get('mu', 0)
        newMapData['sliders'][i]['tb'] = newMapData['sliders'][i].get('tb', 0)
        newMapData['sliders'][i]['tx'] = newMapData['sliders'][i].get('tx', 0)
        newMapData['sliders'][i]['ty'] = newMapData['sliders'][i].get('ty', 0)
        newMapData['sliders'][i]['tc'] = newMapData['sliders'][i].get('tc', 0)
        newMapData['sliders'][i]['tmu'] = newMapData['sliders'][i].get('tmu', 0)
        newMapData['sliders'][i]['m'] = newMapData['sliders'][i].get('m', 0)

    for i in range(0, len(newMapData['burstSliders'])):
        newMapData['burstSliders'][i]['b'] = newMapData['burstSliders'][i].get('b', 0)
        newMapData['burstSliders'][i]['c'] = newMapData['burstSliders'][i].get('c', 0)
        newMapData['burstSliders'][i]['x'] = newMapData['burstSliders'][i].get('x', 0)
        newMapData['burstSliders'][i]['y'] = newMapData['burstSliders'][i].get('y', 0)
        newMapData['burstSliders'][i]['d'] = newMapData['burstSliders'][i].get('d', 0)
        newMapData['burstSliders'][i]['tb'] = newMapData['burstSliders'][i].get('tb', 0)
        newMapData['burstSliders'][i]['tx'] = newMapData['burstSliders'][i].get('tx', 0)
        newMapData['burstSliders'][i]['ty'] = newMapData['burstSliders'][i].get('ty', 0)
        newMapData['burstSliders'][i]['sc'] = newMapData['burstSliders'][i].get('sc', 8)
        newMapData['burstSliders'][i]['s'] = newMapData['burstSliders'][i].get('s', 1)

    return newMapData
    
def mapPrep(mapData):
    try:
        mapVersion = parse(mapData['version'])
    except KeyError:
        try:
            mapVersion = parse(mapData['_version'])
        except KeyError:
            try:
                mapData['_notes']
                mapVersion = parse('2.0.0')
            except KeyError:
                try:
                    mapData['colorNotes']
                    mapVersion = parse('3.0.0')
                except KeyError:
                    print("Unknown Map Type. Exiting")
                    exit()
    if mapVersion < parse('3.0.0'):  # Try to figure out if the map is the V2 or V3 format
        newMapData = V2_to_V3(mapData)  # Convert to V3
    elif mapVersion < parse('3.3.0'):
        newMapData = mapData
    else:       # New 3.3.0 spec omits default values, so we need to fill them in
        newMapData = V3_3_0_to_V3(mapData)
    
    newMapData['colorNotes'] = sorted(newMapData['colorNotes'], key=lambda d: d['b'])   # Sort data by time (beats).
    newMapData['bombNotes'] = sorted(newMapData['bombNotes'], key=lambda d: d['b']) # bombs
    newMapData['obstacles'] = sorted(newMapData['obstacles'], key=lambda d: d['b']) # walls
    newMapData['sliders'] = sorted(newMapData['sliders'], key=lambda d: d['b'])     # arcs
    newMapData['brustSliders'] = sorted(newMapData['burstSliders'], key=lambda d: d['b'])   #chains

    return newMapData

def splitMapData(mapData: dict, leftOrRight):  # False or 0 = Left, True or 1 = Right, 2 = Bombs, 3 = Walls
    match leftOrRight:
        case 0:
            blockList = {}
            blockList['notes'] = [block for block in mapData['colorNotes'] if block['c'] == 0]
            blockList['arcs'] = [arcs for arcs in mapData['sliders'] if arcs['c'] == 0]
            blockList['chains'] = [chains for chains in mapData['burstSliders'] if chains['c'] == 0]
        case 1:
            blockList = {}
            blockList['notes'] = [block for block in mapData['colorNotes'] if block['c'] == 1]
            blockList['arcs'] = [arcs for arcs in mapData['sliders'] if arcs['c'] == 1]
            blockList['chains'] = [chains for chains in mapData['burstSliders'] if chains['c'] == 1]
        case 2:
            blockList = [bomb for bomb in mapData['bombNotes']]
        case 3:
            blockList = [wall for wall in mapData['obstacles']]
    return blockList

def calculateJD(bpm, njs, offset):
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

def distanceToBeats(bpm, njs, distance):
    time = distance / njs
    beats = time * bpm / 60

    return beats

def beatsToSeconds(beats, bpm):
    seconds = beats * 60 / bpm
    return seconds

def swingXangle(blockPos, handPos):
    return math.degrees(math.asin(handPos[0] - blockPos[0]))

def bindArcsToNotes(noteData, arcData): # Edits noteData
    noteData_index = 0
    noteData_index_t = 0

    for i in range(0, len(noteData)):
        noteData[i]['preArc'] = False              # Initialize dict key
        noteData[i]['postArc'] = False

    for i in range(0, len(arcData)):
        # Index preparation while loops
        while noteData[noteData_index]['b'] < arcData[i]['b'] and noteData_index + 1 < len(noteData):      # Increase index until right below correct note (time)
            noteData_index += 1

        while noteData[noteData_index_t]['b'] < arcData[i]['tb'] and noteData_index_t + 1 < len(noteData):      # Increase index until right below correct note (time)
            noteData_index_t += 1

        sameTimeList = []   # Reset list
        found = False

        # Arc matcher while loops
        while True: # Arc beginning note check
            if noteData[noteData_index]['b'] == arcData[i]['b']:
                sameTimeList.append({'data': noteData[noteData_index], 'index': noteData_index})

                if noteData_index + 1 < len(noteData):
                    if noteData[noteData_index + 1]['b'] == arcData[i]['b']:
                        temp_index = noteData_index
                        while noteData[temp_index + 1]['b'] == arcData[i]['b'] and temp_index + 1 < len(noteData):
                            temp_index += 1
                            sameTimeList.append({'data': noteData[temp_index], 'index': temp_index})
                
                for j in range(0, len(sameTimeList)):
                    if (sameTimeList[j]['data']['x'] == arcData[i]['x']) and (sameTimeList[j]['data']['y'] == arcData[i]['y']) and ((sameTimeList[j]['data']['d'] == arcData[i]['d']) or (sameTimeList[j]['data']['d'] == 8)):
                        noteData[sameTimeList[j]['index']]['postArc'] = True
                        found = True
                        break
            else:
                if noteData[noteData_index]['b'] > arcData[i]['b']:
                    break   # If the note index is greater than arc time, then there was no pre
                
                if noteData_index + 1 >= len(noteData):
                    break

                noteData_index += 1
            
            if found:
                break

        sameTimeList = []   # Reset list
        found = False

        while True: # Arc ending note check
            if noteData[noteData_index_t]['b'] == arcData[i]['tb']:
                sameTimeList.append({'data': noteData[noteData_index_t], 'index': noteData_index_t})

                if noteData_index_t + 1 < len(noteData):
                    if noteData[noteData_index_t + 1]['b'] == arcData[i]['tb']:
                        temp_index = noteData_index_t
                        while noteData[temp_index + 1]['b'] == arcData[i]['tb'] and temp_index + 1 < len(noteData):
                            temp_index += 1
                            sameTimeList.append({'data': noteData[temp_index], 'index': temp_index})
                
                for j in range(0, len(sameTimeList)):
                    if (sameTimeList[j]['data']['x'] == arcData[i]['tx']) and (sameTimeList[j]['data']['y'] == arcData[i]['ty']) and ((sameTimeList[j]['data']['d'] == arcData[i]['tc']) or (sameTimeList[j]['data']['d'] == 8)):
                        noteData[sameTimeList[j]['index']]['preArc'] = True
                        found = True
                        break
            else:
                if noteData[noteData_index_t]['b'] > arcData[i]['b']:
                    break   # If the note index is greater than arc time, then there was no post
                
                if noteData_index_t + 1 >= len(noteData):
                    break

                noteData_index_t += 1

            if found:
                break

    return

def bindChainsToNotes(noteData, chainData):
    noteData_index = 0

    for i in range(0, len(noteData)):
        noteData[i]['hasChain'] = False              # Initialize dict key

    for i in range(0, len(chainData)):
        # Index preparation while loops
        while noteData[noteData_index]['b'] < chainData[i]['b'] and noteData_index + 1 < len(noteData):      # Increase index until right below correct note (time)
            noteData_index += 1

        sameTimeList = []   # Reset list
        found = False

        # Chain matcher while loops
        while True: # Chain beginning note check
            if noteData[noteData_index]['b'] == chainData[i]['b']:
                sameTimeList.append({'data': noteData[noteData_index], 'index': noteData_index})

                if noteData_index + 1 < len(noteData):
                    if noteData[noteData_index + 1]['b'] == chainData[i]['b']:
                        temp_index = noteData_index
                        while noteData[noteData_index + 1]['b'] == chainData[i]['b'] and noteData_index + 1 < len(noteData):
                            temp_index += 1
                            sameTimeList.append({'data': noteData[temp_index], 'index': temp_index})
                
                for j in range(0, len(sameTimeList)):
                    if (sameTimeList[j]['data']['x'] == chainData[i]['x']) and (sameTimeList[j]['data']['y'] == chainData[i]['y']) and ((sameTimeList[j]['data']['d'] == chainData[i]['d']) or (sameTimeList[j]['data']['d'] == 8)):
                        noteData[sameTimeList[j]['index']]['chainData'] = chainData[i]
                        noteData[sameTimeList[j]['index']]['hasChain'] = True
                        found = True
                        break
            else:
                if noteData[noteData_index]['b'] > chainData[i]['b']:
                    break   # If the note index is greater than arc time, then there was no pre
                
                if noteData_index + 1 >= len(noteData):
                    break

                noteData_index += 1
            
            if found:
                break

    return
# Base block calculations

# Calculates the entry point of a swing given block position, block angle, and swing angle.
def calcNoteHitbox(cBlockPosition, cBlockAngle, swingAngle = -1):
    # Block good hitbox X = 0.8m, Y = 0.5m, Z = 1m
    # Hitbox is Z = -0.15m offset from block position 
    # Distance between 2 blocks on the X axis is 0.436m. /2 equals X middle point of the block hitbox.
    # baseXPosition = 0.21818
    
    # Distance between 2 blocks on the Y axis is average 0.525m. /2 equals Y middle point of the block hitbox.
    # baseYPosition = 0.2625

    hitbox = {'p0': {}, 'p1': {}}
    strikePos = []
    noteAngle = []

    xNoteRelativeCenter = (cBlockPosition[0] + 0.5 - 2) * xGridDistance        # Calculate the xCoordinates relative to the middle of the world.

    xAng = 0            # Pitch, Yaw, Roll
    yAng = np.arccos(xNoteRelativeCenter / (saberHitDistance + 0.85))    #  saber length + 0.85 forward z hitbox. 0° is straight forwards, +angle is CC, -angle is clockwise.
    zAng = cBlockAngle

    # Initialize point positions for hitbox caluclations in world space
    p0 = np.array([0, 0, 0.15])         # front left corner 
    p1 = np.array([0.8, 0.5, 1.15])     # back right corner
    center = np.array([0.4, 0.25, 1])   # center of cube 
    
    # Apply rotation transformes
    rotated_p0 = rotatePoint(p0, center, xAng, yAng, zAng)
    rotated_p1 = rotatePoint(p1, center, xAng, yAng, zAng)
    
    # Apply grid positioning
    x0Pos = cBlockPosition[0] * xGridDistance + rotated_p0[0]
    x1Pos = cBlockPosition[0] * xGridDistance + rotated_p1[0]
    y0Pos = cBlockPosition[1] * yGridDistance + rotated_p0[1]
    y1Pos = cBlockPosition[1] * yGridDistance + rotated_p1[1]
    z0Pos = rotated_p0[2]
    z1Pos = rotated_p1[2]

    #Save data
    # hitbox['p0'] = {'x': x0Pos, 'y': y0Pos, 'z': z0Pos}
    # hitbox['p1'] = {'x': x1Pos, 'y': y1Pos, 'z': z1Pos}
    # angle = {'x': xAng, 'y': yAng, 'z': zAng}
    # strikePos = {'x': rotated_strikePos[0], 'y': rotated_strikePos[1], 'z': rotated_strikePos[2]}
    
    hitbox['p0'] = np.array([x0Pos, y0Pos, z0Pos])
    hitbox['p1'] = np.array([x1Pos, y1Pos, z1Pos])
    angle = np.array([xAng, yAng, zAng])
    
    blockData = {'posData' : hitbox, 'angle': angle, 'strikePos': strikePos}

    return blockData

def calculateBombHitbox(bPos: list):
    hitboxX1 = bPos[0] * xGridDistance + bombOffset[0][0]
    hitboxY1 = bPos[1] * yGridDistance + bombOffset[0][1]
    hitboxZ1 = bombOffset[0][2]
    hitboxX2 = bPos[0] * xGridDistance + bombOffset[1][0]
    hitboxY2 = bPos[1] * yGridDistance + bombOffset[1][1]
    hitboxZ2 = bombOffset[1][2]

    hitbox = {'p0': np.array([hitboxX1, hitboxY1, hitboxZ1]), 'p1': np.array([hitboxX2, hitboxY2, hitboxZ2])}
    return hitbox

def calculateWallHitbox(xPos, yPos, width, distance, height):
    hitboxX1 = xPos * xGridDistance
    hitboxY1 = yPos * yGridDistance
    # hitboxZ1 = -0.25                          # Need to verify: Subtract 0.25 to make front face of wall line up with front face of note (walls just built like that) (cred: arcViewer)
    hitboxZ1 = 1                                
    hitboxX2 = (xPos + width) * xGridDistance
    hitboxY2 = (yPos + height) * yGridDistance
    hitboxZ2 = distance * metadata['njs'] + 1

    hitboxPos = {'p0': np.array([hitboxX1, hitboxY1, hitboxZ1]), 'p1': np.array([hitboxX2, hitboxY2, hitboxZ2])}
    return hitboxPos

def createNoteList(objectData: dict):
    # Purpose of the function is to prepare and condition note data

    # Note data structure
    # beat: float The time of the swing
    # beatF: float The end of the swing
    # isDot: bool If the note is a dot note
    # LRhand: bool Left or Right hand
    # hitboxData: Array of hitbox data
    # noteAngle: float The angle of the note
    # preAngleDisabled: bool If 100° pre swing angle is required (disabled for arcs)
    # postAngleDisabled: bool If 60° post swing angle is required (disabled for arcs)
    
    notes = objectData['notes']
    arcs = objectData['arcs']
    chains = objectData['chains']
    bindArcsToNotes(notes, arcs)        # Assigns pre/post angle required bool values to every note/chain
    bindChainsToNotes(notes, chains)
    swingData = []

    for i in range(0, len(notes)):
        cNote = notes[i]
        isDot = False
        blockAngle = cut_direction_index[cNote['d']] + cNote['a']       # Get block angle, including precision angle
        if cNote['d'] == 8:
            isDot = True
           
        hitboxPosData = calcNoteHitbox([cNote['x'], cNote['y']], blockAngle)     

        swingBeginning = cNote['b']
        
        if not cNote['hasChain']:
            swingEnd = swingBeginning
            
        else:
            distance = math.sqrt(math.pow((cNote['chainData']['x'] - cNote['chainData']['tx']), 2) + math.pow((cNote['chainData']['y'] - cNote['chainData']['ty']), 2))
            chainStartPos = np.array([cNote['chainData']['x'], cNote['chainData']['y']])
            chainEndPos = np.array([cNote['chainData']['tx'], cNote['chainData']['ty']])
            midOffset = np.array([math.cos(math.radians(cut_direction_index[cNote['chainData']['d']])), math.sin(math.radians(cut_direction_index[cNote['chainData']['d']]))]) * distance / 2
            midPoint = chainStartPos + midOffset
            swingEnd = cNote['chainData']['tb']
            linkNum = cNote['chainData']['sc'] - 1

            linkPos = []
            linkAngle = []

            for j in range(1, cNote['chainData']['sc']):
                timeProgress = j / (cNote['chainData']['sc'] - 1)

                t = timeProgress * cNote['chainData']['s']

                linkPos.append(PointOnQuadBezier(chainStartPos, midPoint, chainEndPos, t))  # Save block position on the grid for conversion
                linkAngle.append(AngleOnQuadBezier(chainStartPos, midPoint, chainEndPos, t))
                # Calculate block swing strike position in meters and save.
                linkPos[-1] = calcNoteHitbox(linkPos[-1], linkAngle[-1])

        swingData.append({})
        # swingData[-1]['LRhand'] = handedness                            #Bool
        swingData[-1]['isDot'] = isDot                                  #Bool
        swingData[-1]['beat'] = swingBeginning                          #Float
        swingData[-1]['beatF'] = swingEnd                               #Float
        swingData[-1]['hitbox'] = hitboxPosData                         #Array of Vector3
        swingData[-1]['noteAngle'] = blockAngle                         #Vector3
        swingData[-1]['preAngleDisabled'] = cNote['preArc']             #Bool
        swingData[-1]['postAngleDisabled'] = cNote['postArc']           #Bool
        swingData[-1]['hasChain'] = cNote['hasChain']                   #Bool
        if cNote['hasChain']:
            swingData[-1]['chainData'] = {'linkNum': linkNum, 'linkPos': linkPos, 'linkAngle': linkAngle}

    swingData = sorted(swingData, key=lambda d: d['beat'])  # Sort by time
    return swingData

def createBombList(bombs: list):
    bombData = []
    bombIndex = 0
    while bombIndex < len(bombs):
        sameTime = []
        sameTime.append(bombs[bombIndex])

        # Consolidate bombs on the same beat.

        if bombIndex + 1 < len(bombs) - 1:  # Check if array access is valid
            while (bombs[bombIndex]['b'] == bombs[bombIndex + 1]['b']) and (bombIndex + 1 < len(bombs) - 1):
                bombIndex += 1
                sameTime.append(bombs[bombIndex])

        bombData.append({})
        bombData[-1]['beat'] = sameTime[0]['b']

        bombData[-1]['hitbox'] = {'posData': []}        
        for j in range(0, len(sameTime)):
            bombPos = [sameTime[j]['x'], sameTime[j]['y']]
            bombData[-1]['hitbox']['posData'].append(calculateBombHitbox(bombPos))     # We will approximate bombs to be cubes.

        bombIndex += 1
    
    return bombData

def createWallList(walls: list):
    wallData = []
    wallIndex = 0
    
    while wallIndex < len(walls):
        sameTime = []
        sameTime.append(walls[wallIndex])

        # Consolidate walls on the same beat.
        if wallIndex + 1 < len(walls) - 1:          # Check if array access is valid
            while (walls[wallIndex]['b'] == walls[wallIndex + 1]['b']) and (wallIndex + 2 < len(walls)):
                sameTime.append(walls[wallIndex])
                wallIndex += 1
        
        wallData.append({})     # Initialize new entry
        wallData[-1]['beat'] = sameTime[0]['b']
        wallData[-1]['hitbox'] = {'posData': []}      # We will approximate bombs to be cubes instead of sphears for speed.
        
        for j in range(0, len(sameTime)):
            wallData[-1]['hitbox']['posData'].append(calculateWallHitbox(sameTime[j]['x'], sameTime[j]['y'], sameTime[j]['w'], sameTime[j]['d'], sameTime[j]['h']))
            wallData[-1]['hitbox']['posData'][-1]['lengthSeconds'] = beatsToSeconds(sameTime[j]['d'], metadata['bpm'])

        wallIndex += 1
    
    return wallData
    
def applyRotationData(objectData, rotationData=[]):
    if len(rotationData) == 0:
        return objectData
    
    rotation = 0        # Current platform rotation (yaw)
    rotationIndex = 0   # Index of future incoming rotation event
    InclusiveFlag = not rotationData[rotationIndex]['e']
    # test_rotationChangelog = []
    if isinstance(objectData[0]['hitbox']['posData'], list):
        positionDataIsList = True
    else:
        positionDataIsList = False

    for i in range(0, len(objectData)):
        if rotationIndex < len(rotationData):
            
            if InclusiveFlag:
                while objectData[i]['beat'] >= rotationData[rotationIndex]['b']:    # While loop to handle cases where there are multiple rotation events between objects
                    rotation += rotationData[rotationIndex]['r']
                    # test_rotationChangelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                    if rotationIndex + 1 < len(rotationData):
                        rotationIndex += 1
                        InclusiveFlag = not rotationData[rotationIndex]['e']
                    else:
                        break
            else:
                while objectData[i]['beat'] > rotationData[rotationIndex]['b']:     # While loop to handle cases where there are multiple rotation events between objects
                    rotation += rotationData[rotationIndex]['r']
                    # test_rotationChangelog.append({'rotation': rotation, 'beat': rotationData[rotationIndex]['b']})
                    if rotationIndex + 1 < len(rotationData):
                        rotationIndex += 1
                        InclusiveFlag = not rotationData[rotationIndex]['e']
                    else:
                        break

        # p0 = np.array([objectData[i]['hitbox']['p0']['x'],objectData[i]['hitbox']['p0']['y'],objectData[i]['hitbox']['p0']['z']])
        # p1 = np.array([objectData[i]['hitbox']['p1']['x'],objectData[i]['hitbox']['p1']['y'],objectData[i]['hitbox']['p1']['z']])
        if positionDataIsList:
            for posIndex in range(0, len(objectData[i]['hitbox']['posData'])):
                p0 = objectData[i]['hitbox']['posData'][posIndex]['p0']
                p1 = objectData[i]['hitbox']['posData'][posIndex]['p1']
                center = np.array([xGridDistance * 2, 0, 0])
                # Rotation must be inverted to convert between mathimatical and beatsaber rotation orientation
                objectData[i]['hitbox']['posData'][posIndex]['p0'] = rotatePoint(p0, center, 0, -rotation, 0)
                objectData[i]['hitbox']['posData'][posIndex]['p1'] = rotatePoint(p1, center, 0, -rotation, 0)
        else:
            p0 = objectData[i]['hitbox']['posData']['p0']
            p1 = objectData[i]['hitbox']['posData']['p1']
            center = np.array([0,0,0])
            objectData[i]['hitbox']['posData']['p0'] = rotatePoint(p0, center, 0, -rotation, 0)
            objectData[i]['hitbox']['posData']['p1'] = rotatePoint(p1, center, 0, -rotation, 0)
    
    return objectData

# ------------------------ Algo specific functions ------------------------
# TODO: Finish
# hitboxPos: Vector3 (touple of floats)
# hitboxAngle: Angle3 (touple of floats)
# strikeAngle: float
def calculate115(hitboxPos, hitboxAngle, strikeAngle):
    #0.4 = (x) middle of width of hitbox, (y) 0.5 = top of hitbox, (z) length of hitbox
    strikePos = [0.4, 0.5, hitboxPos['p0'][2] + saberHitDistance]    # Initializa strike position.
    
    if strikeAngle != -1:        # If given a swingAngle, calculate exact point on the hitbox to strike for 15 acc
        xDistance = 0.4 * math.sin(math.radians(strikeAngle - hitboxAngle))
        xOffset = xDistance * math.sin(math.radians(hitboxAngle - 180))
        yOffset = xDistance * math.cos(math.radians(hitboxAngle - 180))
    else:
        xOffset = 0
        yOffset = 0

    strikePos[0] += xOffset
    strikePos[1] += yOffset
    # rotated_strikePos = rotatePoint(initStrikePos, center, hitboxAngle[0], hitboxAngle[1], hitboxAngle[2])
    return strikePos


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
def primarySwingPath(noteData, bombData, wallData, handedness, accelMax, rotationData = []):

    # Setup numpy arrays for faster vector arithmatic.
    if handedness == 0:                                                 # X, Y, and Z coordinates in meters
        hPos = np.array([1.5 * xGridDistance, 1.5 * yGridDistance, -saberHitDistance])     # Left 
    else:
        hPos = np.array([2.5 * xGridDistance, 1.5 * yGridDistance, -saberHitDistance])     # Right
    
    # hAng = np.array([0, 0, 270])         # X (pitch), Y (yaw), and Z (roll) think of an airplane. TODO change to check angle from either note or bomb, whichever is first
    # hAngVel = np.array([0, 0, 0])          # Angular velocity in degrees/sec
    # hAngAcc = np.array([0, 0, 0])          # Angular acceleration in degrees/sec^2
    
    duration = noteData[0]['beat']

    pathData = [{'swingDataIndex': 0, 'path': {'pos': [], 'posVel': [], 'posAccel': [], 'ang': [], 'angVel': [], 'angAccel': []}}]

    for i in range(0, len(noteData)):
        cSwing = noteData[i]   # Cache indexed data used for referencing








        # from matplotlib import pyplot as plt        #   Test
        #     fig, ax = plt.subplots(figsize = (15, 8))
        #     xvals = [x[0] for x in pathData[-1]['path']['pos']]
        #     yvals = [x[1] for x in pathData[-1]['path']['pos']]
        #     ax.plot(xvals, yvals, label='curve path')
        #     xpoints = [p[0] for p in [p0, p1, p2, p3]]
        #     ypoints = [p[1] for p in [p0, p1, p2, p3]]
        #     ax.plot(xvals, yvals, label='curve path')
        #     ax.plot(xpoints, ypoints, "ro")
        #     pName = ['p0','p1','p2','p3']
        #     for p, txt in enumerate(pName):
        #         ax.annotate(txt, (xpoints[p], ypoints[p]))
        #     ax.set_xticks(np.linspace(0,xGridDistance * 4,5))
        #     ax.set_yticks(np.linspace(0,yGridDistance * 3,4))
        #     #plt.xlim(0,1.3333333)
        #     #plt.ylim(0,1)
        #     plt.legend()
        #     plt.show()
     

# def swingPathSmoothing(pathData, metaData):
    
#     # Code for later
#     njs = metaData['njs']
#     bpm = metaData['bpm']
#     offset = metaData['offset']
#     jumpDistance = calculateJD(bpm, njs, offset)
#     lookAhead = distanceToBeats(bpm, njs, jumpDistance / 2)
#     RT = lookAhead / bpm * 60

#     hPosVel = np.array([0, 0])          # Positional velocity in m/s
#     hPosAcc = np.array([0, 0])          # Positional acceleration in m/s^2

#     resolution = 20                         # Minimum 10 points to get useful data
#     bPos = np.array(cSwing['handPos'])
#     distance = bPos - hPos
#     duration = cSwing['beat'] - swingData[i - 1]['beat']
#     timeSlice = duration / resolution / bpm * 60


#     hPosVel = pathData[-1]['path']['posVel'][-1]

#     if np.min(np.minimum(hPosVel, 0)) == 0 and np.max(np.maximum(hPosVel, 0)) == 0:            # This is cleaner
#         p1 = hPos + p1Offset
#     else:
#         p1 = hPos + hPosVel * np.minimum(np.linalg.norm(hPosVel), np.linalg.norm(distance) / np.linalg.norm(hPosVel))     

#     if j > 0:
#         pathData[-1]['path']['posVel'].append((pathData[-1]['path']['pos'][-1] - pathData[-1]['path']['pos'][-2]) / timeSlice)
#     else:
#         pathData[-1]['path']['posVel'].append(np.array([0,0]))

#     if j > 0:
#         pathData[-1]['path']['posAccel'].append((pathData[-1]['path']['posVel'][-1] - pathData[-1]['path']['posVel'][-2]) / timeSlice)
#     else:
#         pathData[-1]['path']['posAccel'].append(np.array([0,0]))
            


# ------------------------ Function Execution ------------------------

def techOperations(B_mapData: dict, metadata: dict, isuser=True, verbose=True):
    B_LeftNoteData = splitMapData(B_mapData, 0)     # Parse mapdata into separate varables to pass into functions
    B_RightNoteData = splitMapData(B_mapData, 1)
    B_BombData = splitMapData(B_mapData, 2)
    B_WallData = splitMapData(B_mapData, 3)
    LeftNoteData = createNoteList(B_LeftNoteData, 0)    # Create extract object data with game mechanics
    RightNoteData = createNoteList(B_RightNoteData, 1)
    BombData = createBombList(B_BombData)
    WallData = createWallList(B_WallData)
    if len(B_mapData['rotationEvents']) > 0:                # Apple rotation data if available
        LeftNoteData = applyRotationData(LeftNoteData, B_mapData['rotationEvents'])
        RightNoteData = applyRotationData(RightNoteData, B_mapData['rotationEvents'])
        BombData = applyRotationData(BombData, B_mapData['rotationEvents'])
        WallData = applyRotationData(WallData, B_mapData['rotationEvents'])

    LeftSwingPath = primarySwingPath(LeftNoteData, BombData, WallData, 0, B_mapData['rotationEvents'])
    RightSwingPath = primarySwingPath(RightNoteData, BombData, WallData, 1, B_mapData['rotationEvents'])
    
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
    newMapData = mapPrep(mapData)
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