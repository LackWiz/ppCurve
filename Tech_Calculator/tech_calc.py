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


# Works for both V2 and V3
# Easy = 1, Normal = 3, Hard = 5, Expert = 7, Expert+ = 9
# b = time, x and y = grid location from bottom left, a = angle offset, c = left or right respectively, d = direction
cut_direction_index = [90, 270, 180, 0, 135, 45, 225, 315, 270]     # mathamatical 0°, direction of cut
right_handed_angle_strain_forehand = 247.5  # Most comfortable angle to aim for right hand 270 - 45 or 247.5
left_handed_angle_strain_forehand = 292.5  # 270 + 45 or 292.5
xGridDistance = 0.43636   # In meters
yGridDistance = 0.525   # In meters, averaged 0.55m between bottom and middle row, 0.5m between middle and top row. This will also be scaled according to users height 
bombCenterOffset = [[xGridDistance / 2 - 0.18, yGridDistance / 2 - 0.18], [xGridDistance / 2 + 0.18, yGridDistance / 2 + 0.18]]     #Bombs are roughly equal in size to note badcut hitboxes @ 0.36m
# GLobal base functions

def average(lst, setLen=0):  # Returns the averate of a list of integers
    if len(lst) > 0:
        if setLen == 0:
            return sum(lst) / len(lst)
        else:
            return sum(lst) / setLen
    else:
        return 0

def bernstein_poly(i, n, t):
    return comb(n, i) * (t ** (n - i)) * (1 - t) ** i

def bezier_curve(points, nTimes=1000):
    nPoints = len(points)
    xPoints = np.array([p[0] for p in points])
    yPoints = np.array([p[1] for p in points])
    t = np.linspace(0.0, 1.0, nTimes)
    polynomial_array = np.array([bernstein_poly(i, nPoints - 1, t) for i in range(0, nPoints)])
    return list(np.dot(xPoints, polynomial_array)), list(np.dot(yPoints, polynomial_array))

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

#Not the correct way to define function input type, but it'll help someone.
def PointOnQuadBezier(p0: np.array, p1: np.array, p2: np.array, t):
    return list((math.pow(1 - t, 2) * p0) + (2 * (1 - t) * t * p1) + (math.pow(t, 2) * p2))

def AngleOnQuadBezier(p0: np.array, p1: np.array, p2: np.array, t):
    derivative = list((2 * (1 - t) * (p1 - p0)) + (2 * t * (p2 - p1)))
    return mod(math.degrees(math.atan2(derivative[1], derivative[0])), 360)

# Map preparation functions

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

def swingXangle(blockPos, handPos):
    return math.degrees(math.asin(handPos[0] - blockPos[0]))

def bindArcsToNotes(noteData, arcData):
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
def calculateSwingEntry(cBlockP: list, cBlockA, swingA = -1):
    # Block good hitbox X = 0.8m, Y = 0.5m, Z = 1m
    # Hitbox is Z = -0.15m offset from block position 
    # Distance between 2 blocks on the X axis is 0.436m. /2 equals X middle point of the block hitbox.
    # baseXPosition = 0.21818
    
    # Distance between 2 blocks on the Y axis is average 0.525m. /2 equals Y middle point of the block hitbox.
    # baseYPosition = 0.2625
    
    middlePoint = [cBlockP[0] * xGridDistance + 0.21818, 
                   cBlockP[1] * yGridDistance  + 0.2625]
    
    topPoint = [middlePoint[0] - math.cos(math.radians(cBlockA)) * 0.4, 
                middlePoint[1] - math.sin(math.radians(cBlockA)) * 0.25]
    
    if swingA != -1:
        xDistance = 0.4 * math.sin(math.radians(swingA - cBlockA))
        xOffset = xDistance * math.sin(math.radians(cBlockA - 180))
        yOffset = xDistance * math.cos(math.radians(cBlockA - 180))
    else:
        xOffset = 0
        yOffset = 0

    swingPoint = [topPoint[0] + xOffset, 
                  topPoint[1] - yOffset]

    return swingPoint

def calculateBombHitbox(bPos: list):
    hitboxX1 = bPos[0] * xGridDistance + bombCenterOffset[0][0]
    hitboxY1 = bPos[1] * yGridDistance + bombCenterOffset[0][1]
    hitboxX2 = bPos[0] * xGridDistance + bombCenterOffset[1][0]
    hitboxY2 = bPos[1] * yGridDistance + bombCenterOffset[1][1]

    hitboxPos = [[hitboxX1, hitboxY1], [hitboxX2, hitboxY2]]

    return hitboxPos

def primarySwings(objectData: dict, bombs: list, handedness: int):    # handedness: 0 = left, 1 = right
    # Purpose of the function is to turn notes into swings. All notes, including those included in sliders will get their own swing.
    # Later swing smoothing will combine individual swing data into a smooth swing path for calculation

    notes = objectData['notes']
    arcs = objectData['arcs']
    chains = objectData['chains']

    # Note data structure
    # beat: float The time of the swing
    # beatF: float The end of the swing
    # isBomb: bool If the swing exists because of a bomb
    # LRhand: bool Left or Right hand
    # handPos: [float x, float y] Position of hand to swing
    # swingAngle: float The angle of the swing [y, z]. y is yaw, z is roll. Saber travels in the path of the roll
    # noteAngle: float The angle of the note
    # angleRequirement: float Angle strictness
    # swingAngleMargin: list [float margin counterclockwise, float margin clockwise] Available angle margin, 
    # preAngleEnabled: bool If 100° pre swing angle is required (disabled for arcs)
    # postAngleEnabled: bool If 60° post swing angle is required (disabled for arcs)
    # freePoints: float How many points were given for free (only applys for chain links)
    # totalPoints: float Total points earnable from the swing
    

    swingData = []

    bindArcsToNotes(notes, arcs)        # Assigns pre/post angle required bool values to every note/chain
    bindChainsToNotes(notes, chains)

    for i in range(0, len(notes)):
        cNote = notes[i]

        blockAngle = cut_direction_index[cNote['d']] + cNote['a']       # Get block angle, including precision angle
        hitboxStrikePos = calculateSwingEntry([cNote['x'], cNote['y']], blockAngle)     
        swingBeginning = cNote['b']
        
        # if i == 0:
        #     hitboxStrikePos = calculateSwingEntry([notes[i]['x'], notes[i]['y']], blockAngle)
        # else:
        #     temp = calculateSwingEntry([notes[i]['x'], notes[i]['y']], blockAngle)
        #     hitboxStrikePos = [(swingData[-2]['handPos'][0] + temp[0]) / 2, (swingData[-2]['handPos'][1] + temp[1]) / 2]

        if cNote['hasChain']:
            distance = math.sqrt(math.pow((cNote['chainData']['x'] - cNote['chainData']['tx']), 2) + math.pow((cNote['chainData']['y'] - cNote['chainData']['ty']), 2))
            chainStartPos = np.array([cNote['chainData']['x'], cNote['chainData']['y']])
            chainEndPos = np.array([cNote['chainData']['tx'], cNote['chainData']['ty']])
            midOffset = np.array([math.cos(math.radians(cut_direction_index[cNote['chainData']['d']])), math.sin(math.radians(cut_direction_index[cNote['chainData']['d']]))]) * distance / 2
            midPoint = chainStartPos + midOffset
            swingEnd = cNote['chainData']['tb']

            linkPos = []
            linkAngle = []

            for j in range(1, cNote['chainData']['sc']):
                timeProgress = j / (cNote['chainData']['sc'] - 1)

                t = timeProgress * cNote['chainData']['s']

                linkPos.append(PointOnQuadBezier(chainStartPos, midPoint, chainEndPos, t))  # Save block position on the grid for conversion
                linkAngle.append(AngleOnQuadBezier(chainStartPos, midPoint, chainEndPos, t))
                # Calculate block swing strike position in meters and save.
                linkPos[-1] = calculateSwingEntry(linkPos[-1], linkAngle[-1])

            notes[i]['chainData']['linkPos'] = linkPos
            notes[i]['chainData']['linkAngle'] = linkAngle



            freePoints = max(0, (cNote['chainData']['sc'] - 1) * 20)
            totalPoints = 70 + freePoints
            swingAngle = math.degrees(math.atan2(cNote['chainData']['ty'] - cNote['y'], cNote['chainData']['tx'] - cNote['x']))

        else:
            swingEnd = swingBeginning
            freePoints = 0
            totalPoints = 115
            swingAngle = blockAngle

        swingData.append({})
        swingData[-1]['beat'] = swingBeginning
        swingData[-1]['beatF'] = swingEnd
        swingData[-1]['isBomb'] = False
        swingData[-1]['LRhand'] = handedness
        swingData[-1]['handPos'] = hitboxStrikePos
        swingData[-1]['swingAngle'] = [0, swingAngle]
        swingData[-1]['noteAngle'] = blockAngle
        swingData[-1]['angleRequirement'] = 120
        swingData[-1]['swingAngleMargin'] = [60, 60]
        swingData[-1]['preAngleDisabled'] = cNote['preArc']
        swingData[-1]['postAngleDisabled'] = cNote['postArc']
        swingData[-1]['hasChain'] = cNote['hasChain']
        swingData[-1]['freePoints'] = freePoints
        swingData[-1]['totalPoints'] = totalPoints
        if cNote['hasChain']:
            swingData[-1]['chainData'] = {'linkPos': linkPos, 'linkAngle': linkAngle}
        
    for i in range(0, len(bombs)):
        sameTime = []
        sameTime.append(bombs[i])

        # In many cases, there are many bombs on the same beat. Therefore we need to find the best/preferred saber swing position along with acceptable saber positions.
        if i < len(bombs) - 1:
            if(bombs[i]['b'] == bombs[i + 1]['b']):
                while (bombs[i]['b'] == bombs[i + 1]['b']) and (i < len(bombs) + 1):
                    sameTime.append(bombs[i])
                    i += 1
        
        accumulatedX = 0
        accumulatedY = 0

        for j in range(0, len(sameTime)):
            accumulatedX += (sameTime[j]['x'] - 1.5) * xGridDistance    # Set origin to the center of the grid for recommend swing angle calculations
            accumulatedY += (sameTime[j]['y'] - 1) * yGridDistance    # Scaled to reflect differing scaling of the axis

        averagedPosition = [accumulatedX / len(sameTime), accumulatedY / len(sameTime)]
        recommendedSwingAngle = math.degrees(math.atan2(averagedPosition[1], averagedPosition[0]))
        recommendedSwingAngle = mod(recommendedSwingAngle + 180, 360)   # Recommended swing angle should be *away* from the bombs.

        swingData.append({})
        swingData[-1]['beat'] = sameTime[0]['b']
        swingData[-1]['isBomb'] = True
        swingData[-1]['recommendedSA'] = recommendedSwingAngle

        swingData[-1]['hitBoxList'] = []        # We will approximate bombs to be cubes instead of sphears for speed.
        for j in range(0, len(sameTime)):
            bombPos = [sameTime[j]['x'], sameTime[j]['x']]
            swingData[-1]['hitBoxList'].append(calculateBombHitbox(bombPos))

    swingData = sorted(swingData, key=lambda d: d['beat'])

    return swingData

def generateSwingPath(swingData, metaData, handedness):
    njs = metadata['njs']
    bpm = metadata['bpm']
    offset = metadata['offset']
    jumpDistance = calculateJD(bpm, njs, offset)
    lookAhead = distanceToBeats(bpm, njs, jumpDistance / 2)
    RT = lookAhead / bpm * 60

    # Setup numpy arrays for faster vector arithmatic.
    if handedness == 0:                                             # X and Y coordinates in meters
        hPos = np.array([1.5 * xGridDistance, 1.5 * yGridDistance])  # Left 
    else:
        hPos = np.array([2.5 * xGridDistance, 1.5 * yGridDistance])  # Right
    hPosVel = np.array([0, 0])          # Positional velocity in m/s
    hPosAcc = np.array([0, 0])          # Positional acceleration in m/s^2
    
    hAng = np.array([0, 0, 270])         # X (pitch), Y (yaw), and Z (roll) think of an airplane. Convention dictatates that palm down is the correct starting position
    hAngVel = np.array([0, 0, 0])          # Angular velocity in degrees/sec
    hAngAcc = np.array([0, 0, 0])          # Angular acceleration in degrees/sec^2
    
    duration = 0
    
    pTime = 0

    timeBase = 0.010    #Seconds
    timeEnd = swingData[-1]['beatF'] / bpm * 60     # Time of last swing in seconds

    for i in range(0, len(swingData)):
        cSwing = swingData[i]   # Cache indexed data used for referencing
        
        if i > 0:
            duration = cSwing['beat'] - cSwing['beat']

        if not cSwing['isBomb']:
            bPos = np.array(cSwing['handPos'])
            distance = bPos - hPos
            timeSlice = duration / 10
            
            for s in range(0, 10):
                




                pass


# Try to find if placement match for slider

def swingCurveCalc(swingData: list, leftOrRight, isuser=True):
    if len(swingData) < 2:
        return [], []
    testData = []
    for i in range(1, len(swingData)):  ## Generates the list of points for the curve.
        point0 = swingData[i - 1]['exitPos']  # Curve Beginning
        point1x = point0[0] + 1 * math.cos(math.radians(swingData[i - 1]['angle']))
        point1y = point0[1] + 1 * math.sin(math.radians(swingData[i - 1]['angle']))
        point1 = [point1x, point1y]  # Curve Control Point
        point3 = swingData[i]['entryPos']  # Curve Ending
        point2x = point3[0] - 1 * math.cos(math.radians(swingData[i]['angle']))
        point2y = point3[1] - 1 * math.sin(math.radians(swingData[i]['angle']))
        point2 = [point2x, point2y]  # Curve Control Point
        points = [point0, point1, point2, point3]
        xvals, yvals = bezier_curve(points, nTimes=25)
        xvals.reverse()
        yvals.reverse()

def combineAndSortList(array1, array2, key):
    combinedArray = array1 + array2
    combinedArray = sorted(combinedArray, key=lambda x: x[f'{key}'])  # once combined, sort by time
    return combinedArray

def techOperations(mapData: dict, metadata: dict, isuser=True, verbose=True):
    LeftMapData = splitMapData(mapData, 0)
    RightMapData = splitMapData(mapData, 1)
    BombData = splitMapData(mapData, 2)
    WallData = splitMapData(mapData, 3)
    LeftBaseSwingData = primarySwings(LeftMapData, BombData, 0)
    RightBaseSwingData = primarySwings(RightMapData, BombData, 1)
    LeftSwingPath = generateSwingPath(LeftBaseSwingData, metadata, 0)
    RightSwingPath = generateSwingPath(RightBaseSwingData, metadata, 1)
    



    LeftSwingData = []
    RightSwingData = []


    
    if isuser:
        # print(f"Calculated Tech = {round(tech, 2)}")  # Put Breakpoint here if you want to see
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
    mapKey = input()
    mapKey = mapKey.replace("!bsr ", "")
    infoData = setup.loadInfoData(mapKey)
    metadata = {'bpm': infoData['_beatsPerMinute']}

    availableDiffs = setup.findStandardDiffs(setup.findSongPath(mapKey))
    if len(availableDiffs) > 1:
        print(f'Choose Diff num: {availableDiffs}')
        diffNum = int(input())
    else:
        diffNum = availableDiffs[0]
        print(f'autoloading {diffNum}')
    mapData = setup.loadMapData(mapKey, diffNum)

    for i, d in enumerate(infoData['_difficultyBeatmapSets']):
        if d.get('_beatmapCharacteristicName') == 'Standard':
            charIndex = i
            break
    for i, d in enumerate(infoData['_difficultyBeatmapSets'][i]['_difficultyBeatmaps']):
        if d.get('_difficultyRank') == diffNum:
            diffIndex = i
            break
    metadata['njs'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpMovementSpeed']
    metadata['offset'] = infoData['_difficultyBeatmapSets'][charIndex]['_difficultyBeatmaps'][diffIndex]['_noteJumpStartBeatOffset']

    mapCalculation(mapData, metadata, True, True)
    print("Done")
    input()