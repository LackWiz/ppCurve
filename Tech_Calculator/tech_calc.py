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
cut_direction_index = [90, 270, 180, 0, 135, 45, 225, 315, 270]
right_handed_angle_strain_forehand = 247.5  # Most comfortable angle to aim for right hand 270 - 45 or 247.5
left_handed_angle_strain_forehand = 292.5  # 270 + 45 or 292.5


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


def V2_to_V3(V2mapData: dict):    # Convert V2 JSON to V3
    newMapData = {'colorNotes':[], 'bombNotes':[], 'obstacles':[]}
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
    return newMapData


def splitMapData(mapData: dict, leftOrRight: int):  # False or 0 = Left, True or 1 = Right, 2 = Bombs
    if leftOrRight == 0:
        blockList = [block for block in mapData['colorNotes'] if block['c'] == 0]
    elif leftOrRight == 1:
        blockList = [block for block in mapData['colorNotes'] if block['c'] == 1]
    else:
        blockList = [bomb for bomb in mapData['bombNotes']]
    return blockList


def calculateBaseEntryExit(cBlockP, cBlockA):
    entry = [cBlockP[0] * 0.333333 - math.cos(math.radians(cBlockA)) * 0.166667 + 0.166667,
             cBlockP[1] * 0.333333 - math.sin(math.radians(cBlockA)) * 0.166667 + 0.16667]
    exit = [cBlockP[0] * 0.333333 + math.cos(math.radians(cBlockA)) * 0.166667 + 0.166667,
            cBlockP[1] * 0.333333 + math.sin(math.radians(cBlockA)) * 0.166667 + 0.16667]
    return entry, exit


def isSameDirection(pBlockA, cBlockA):
    pBlockA = mod(pBlockA, 360)
    cBlockA = mod(cBlockA, 360)
    if abs(pBlockA - cBlockA) <= 180:
        if abs(pBlockA - cBlockA) < 67.5:
            return True
    else:
        if 360 - abs(pBlockA - cBlockA) < 67.5:
            return True
    return False


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


# Try to find if placement match for slider
def isSlider(prev, next, direction, dot):
    if dot is True:
        if prev['x'] == next['x'] and prev['y'] == next['y']:
            return True
    if 67.5 < direction <= 112.5:
        if prev['y'] < next['y']:
            return True
    elif 247.5 < direction <= 292.5:
        if prev['y'] > next['y']:
            return True
    elif 157.5 < direction <= 202.5:
        if prev['x'] > next['x']:
            return True
    elif 0 <= direction <= 22.5 or 337.5 < direction < 360:
        if prev['x'] < next['x']:
            return True
    elif 112.5 < direction <= 157.5:
        if prev['y'] < next['y']:
            return True
        if prev['x'] > next['x']:
            return True
    elif 22.5 < direction <= 67.5:
        if prev['y'] < next['y']:
            return True
        if prev['x'] < next['x']:
            return True
    elif 202.5 < direction <= 247.5:
        if prev['y'] > next['y']:
            return True
        if prev['x'] > next['x']:
            return True
    elif 292.5 < direction <= 337.5:
        if prev['y'] > next['y']:
            return True
        if prev['x'] < next['x']:
            return True
    return False


# Find next angle by using last known position, next position and a guide angle






# Find pattern note if possible and then swap element for them to be in order



# Find angle in degree for each note
# Proceed to fix some possible issue afterward



# Convert notes and patterns into swing data









# Split the long list of dictionaries into smaller lists of patterns containing lists of dictionaries
def patternSplitter(swingData: list):
    
    if len(swingData) < 2:          # You need at least 3 notes before any kind of frequency calculation can be made
        return []
    
    for i in range(0, len(swingData)):  # Swing Frequency Analyzer
        if i > 0 and i + 1 < len(swingData):  # Checks done so we don't try to access data that doesn't exist
            SF = 2 / (swingData[i + 1]['time'] - swingData[i - 1]['time'])  # Swing Frequency
        else:
            SF = 0
        swingData[i]['frequency'] = SF
    SFList = [freq['frequency'] for freq in swingData]
    
    patternFound = False
    SFmargin = average(SFList) / 32     # Dymically determine margins
    patternList = []  # A list of patterns, each pattern is a list of notes.
    tempPlist = []  # Temp Pattern List
    for i in range(0, len(swingData)):
        if i > 0:
            # Tries to find Patterns within margin
            if abs((1 / (swingData[i]['time'] - swingData[i - 1]['time'])) - swingData[i]['frequency']) <= SFmargin:
                if not patternFound:  # Found a pattern and it's the first one?
                    patternFound = True
                    del tempPlist[-1]
                    if len(tempPlist) > 0:  # We only want to store lists with stuff
                        patternList.append(tempPlist)
                    tempPlist = [swingData[i - 1]]  # Store the 1st block of the pattern
                tempPlist.append(swingData[i])  # Store the block we're working on
            else:
                if len(tempPlist) > 0 and patternFound:
                    tempPlist.append(swingData[i])
                    patternList.append(tempPlist)
                    tempPlist = []
                else:
                    patternFound = False
                    tempPlist.append(swingData[i])
        else:
            tempPlist.append(swingData[0])
    return patternList


# Test parity with angle strain
# Apply best swing angle strain
# Set if the swing is a reset or is forehand


def swingCurveCalc(swingData: list, leftOrRight, isuser=True):
    if len(swingData) < 2:
        return [], []
    swingData[0]['pathStrain'] = 0  # First Note cannot really have any path strain
    swingData[0]['positionComplexity'] = 0
    swingData[0]['preDistance'] = 0
    swingData[0]['curveComplexity'] = 0
    swingData[0]['pathAngleStrain'] = 0
    testData = []
    for i in range(1, len(swingData)):
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


def techOperations(mapData, bpm, isuser=True, verbose=True):
    LeftMapData = splitMapData(mapData, 0)
    RightMapData = splitMapData(mapData, 1)
    BombData = splitMapData(mapData, 2)
    LeftSwingData = []
    RightSwingData = []


    
    if isuser:
        # print(f"Calculated Tech = {round(tech, 2)}")  # Put Breakpoint here if you want to see
        # print(f"Calculated nerf = {round(low_note_nerf, 2)}")
        # print(f"Calculated balanced tech = {round(balanced_tech, 2)}")
        # print(f"Calculated balanced pass diff = {round(balanced_pass, 2)}")
        pass
    return 0     # returnDict


def mapCalculation(mapData, bpm, isuser=True, verbose=True):
    t0 = time.time()
    newMapData = mapPrep(mapData)
    t1 = time.time()
    data = techOperations(newMapData, bpm, isuser, verbose)
    if isuser:
        print(f'Execution Time = {t1 - t0}')
    return data


if __name__ == "__main__":
    print("input map key")
    mapKey = input()
    mapKey = mapKey.replace("!bsr ", "")
    infoData = setup.loadInfoData(mapKey)
    bpm = infoData['_beatsPerMinute']
    availableDiffs = setup.findStandardDiffs(setup.findSongPath(mapKey))
    if len(availableDiffs) > 1:
        print(f'Choose Diff num: {availableDiffs}')
        diffNum = int(input())
    else:
        diffNum = availableDiffs[0]
        print(f'autoloading {diffNum}')
    mapData = setup.loadMapData(mapKey, diffNum)
    mapCalculation(mapData, bpm, True, True)
    print("Done")
    input()