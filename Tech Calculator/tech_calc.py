from asyncio.windows_events import NULL
import os
import json
import math
import _BackendFiles.MapDownloader as MapDownloader
import _BackendFiles.setup as setup
from packaging.version import parse
import numpy as np
from scipy.special import comb
import time
from collections import deque
import copy

# Works for both V2 and V3
# Easy = 1, Normal = 3, Hard = 5, Expert = 7, Expert+ = 9
# b = time, x and y = grid location from bottom left, a = angle offset, c = left or right respectively, d = cur direction
cut_direction_index = [90, 270, 180, 0, 135, 45, 225, 315, 270] #UP, DOWN, LEFT, RIGHT, TOPLEFT, TOPRIGHT, BOTTOMLEFT, BOTTOMRIGHT, DOT
right_handed_angle_strain_forehand = 247.5      # Most comfortable angle to aim for right hand (BOTTOM LEFT) 270 - 45 or 247.5
left_handed_angle_strain_forehand = 292.5       # 270 + 45 or 292.5
# 
# 
# 

class swing:
    __slots__ = 'time', 'angle', 'frequency', 'forehand', 'strain', 'reset'
    def __init__(self, iTime, iAngle):
        self.time = iTime
        self.angle = iAngle
        self.frequency = 0
        self.forehand = NULL
        self.strain = 0
        self.reset = NULL  

def average(lst):   # Returns the averate of a list of integers
    return sum(lst) / len(lst)
def bernstein_poly(i, n, t):    # For later
    """
     The Bernstein polynomial of n, i as a function of t
    """
    return comb(n, i) * ( t**(n-i) ) * (1 - t)**i
def bezier_curve(points, nTimes=100):   # For later
    """
       Given a set of control points, return the
       bezier curve defined by the control points.

       points should be a list of lists, or list of tuples
       such as [ [1,1], 
                 [2,3], 
                 [4,5], ..[Xn, Yn] ]
        nTimes is the number of time steps, defaults to 1000

        See http://processingjs.nihongoresources.com/bezierinfo/
    """

    nPoints = len(points)
    xPoints = np.array([p[0] for p in points])
    yPoints = np.array([p[1] for p in points])

    t = np.linspace(0.0, 1.0, nTimes)

    polynomial_array = np.array([ bernstein_poly(i, nPoints-1, t) for i in range(0, nPoints)   ])

    xvals = np.dot(xPoints, polynomial_array)
    yvals = np.dot(yPoints, polynomial_array)

    return xvals, yvals
def load_json_as_dict(path: str):    # Reads, then loads and returns JSON as a dictionary
    with open(path, 'rb') as json_dat:
        dat = json.loads(json_dat.read())   
        # dat = json.load(json_dat)
    return dat
def findSongPath(song_id: str, isuser=True): # Returns the song folder path by searching the custom songs folder
    bsPath = f"{setup.load_BSPath()}Beat Saber_Data\CustomLevels/"
    song_options = os.listdir(bsPath)
    songFound = False
    for song in song_options:
        if song.startswith(song_id+" "):
            songFolder = song
            songFound = True
            break
    if not songFound:
        # TODO: download from scoresaber if map missing
        if isuser:
            print(song_id + " Not Downloaded or wrong song code!")
            print("Would you like to download this song? (Y/N)")
            if(response := input().capitalize() == "Y"):
                if not (songFolder := MapDownloader.downloadSong(song_id, bsPath)):
                    print(f"Download of {song_id} failed. Exiting...")
                    input()
                    exit()
            else:
                exit()
        else:
            print(f'Downloading Missing song {song_id}')
            if not (songFolder := MapDownloader.downloadSong(song_id, bsPath)):
                print(f"Download of {song_id} failed. Exiting...")
                input()
                exit()
    return f"{bsPath}/{songFolder}"
def findStandardCharacteristicIndex(infoDat: str, characteristicName: str):
    for f in range(0, len(infoDat["_difficultyBeatmapSets"])):
        if infoDat["_difficultyBeatmapSets"][f]['_beatmapCharacteristicName'] == characteristicName:
            return f
def findStandardDiffs(songPath: str):    # Returns a list of all avilable song difficulties from the info.dat file by difficulty number
    infoDat = load_json_as_dict(findInfoFile(songPath)) #Load infoDat file for convience
    characteristicIndex = findStandardCharacteristicIndex(infoDat, "Standard")  
    difflist = []
    for f in range(0, len(infoDat["_difficultyBeatmapSets"][characteristicIndex]["_difficultyBeatmaps"])):
        difflist.append(infoDat["_difficultyBeatmapSets"][characteristicIndex]["_difficultyBeatmaps"][f]["_difficultyRank"]) #Store all avilable difficulties
    return difflist
def diffNum_to_diffPath(songPath: str, diffNum: int):     #Returns the File Path of whichever difficulty under test based on the difficulty Number
    files = os.listdir(songPath)
    match diffNum:
        case 9:
            fileName = files[findMatchingDiffIndex(files, ['expertplus', 'expertplusstandard'])]
        case 7:
            fileName = files[findMatchingDiffIndex(files, ['expert', 'expertstandard'])]
        case 5:
            fileName = files[findMatchingDiffIndex(files, ['hard', 'hardstandard'])]
        case 3:
            fileName = files[findMatchingDiffIndex(files, ['normal', 'normalstandard'])]
        case 1:
            fileName = files[findMatchingDiffIndex(files, ['easy', 'easystandard'])]
    if fileName == False:
        return False
    return f"{songPath}/{fileName}"
def findMatchingDiffIndex(diff_options: list, diff_Names: list):
    diff_options = [x.lower() for x in diff_options]    # Make everything lowercase for easier searching
    for f in range(0, len(diff_options)):   #Find the correct index and therefore file name of the desired difficulty
        fileSplit = diff_options[f].split('.')  #Split to separate
        if any(x in fileSplit for x in diff_Names): # Parses through the new list of names, really only needs to check the first thing in the list though. I made this unnecessarly complicated I guess
            return f
    print("Diff not found")
    return False
def findInfoFile(songPath: str):
    files = os.listdir(songPath)
    files_lowercase = [x.lower() for x in files]
    for f in range(0, len(files)):   #Find the correct index and therefore file name of the desired difficulty
        fileSplit = files_lowercase[f].split('.')  #Split to separate
        if any(x in fileSplit for x in ['info']): # List just in case info file changes name for future
            return f"{songPath}/{files[f]}"
    print("Info not found")
    return False
def V2_to_V3(V2mapData: dict):    # Convert V2 JSON to V3
    newMapData = {'colorNotes':[], 'bombNotes':[], 'obstacles':[]}  # I have to initialize this before hand or python gets grumpy
    for i in range(0, len(V2mapData['_notes'])):
        if V2mapData['_notes'][i]['_type'] in [0, 1]:   # In V2, Bombs and Notes were stored in the same _type key. The "if" just separates them
            newMapData['colorNotes'].append({'b': V2mapData['_notes'][i]['_time']})     # Append to make a new entry into the list to store the dictionary
            newMapData['colorNotes'][-1]['x'] = V2mapData['_notes'][i]['_lineIndex']
            newMapData['colorNotes'][-1]['y'] = V2mapData['_notes'][i]['_lineLayer']
            newMapData['colorNotes'][-1]['a'] = 0                                       # Angle offset didn't exist in V2. will always be 0
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
def splitMapData(mapData: dict, type: int):    # False or 0 = Left, True or 1 = Right, 2 = Bombs
    if type == 0:
        bloqList = [block for block in mapData['colorNotes'] if block['c'] == 0]  #Right handed blocks
    elif type == 1:
        bloqList = [block for block in mapData['colorNotes'] if block['c'] == 1]  #Left handed blocks
    else:
        bloqList = [bomb for bomb in mapData['bombNotes']]
    return bloqList
def swingProcesser(mapSplitData: list):    # Returns a list of dictionaries for all swings returning swing angles and timestamps
    swingData: list[swing] = []
    for i in range(0, len(mapSplitData)):
        isSlider = False
        cBlockB = mapSplitData[i]['b']      # Current Block Position in Time in unit [Beats]        
        cBlockA = cut_direction_index[mapSplitData[i]['d']] + mapSplitData[i]['a']      # Current Block Angle in degrees
        cBlockP = [mapSplitData[i]['x'], mapSplitData[i]['y']]
        if i > 0:
            pBlockB = mapSplitData[i-1]['b']    # Pre-cache data for neater code
            pBlockA = swingData[-1].angle # Previous Block Angle in degrees
            pBlockP = [mapSplitData[i-1]['x'], mapSplitData[i-1]['y']]
            if mapSplitData[i]['d'] == 8:   #Dot note? Just assume opposite angle. If it's a slider, the program will handle it
                pBlockA = swingData[-1].angle
                if cBlockB - pBlockB <= 0.03125:
                    cBlockA = pBlockA
                else:
                    if pBlockA >= 180:
                        cBlockA = pBlockA - 180
                    else:
                        cBlockA = pBlockA + 180
            # All Pre-caching Done
            if cBlockB - pBlockB >= 0.03125: # = 1/32 Just a check if notes are unreasonable close, just assume they're apart of the same swing
                if cBlockB - pBlockB > 0.125: # = 1/8 The upper bound of normal slider precision commonly used
                    if cBlockB - pBlockB > 0.5:    # = 1/2 About the limit of whats reasonable to expect from a slider
                        swingData.append(swing(cBlockB, cBlockA))
                    else: # 1/2 Check (just to weed out obvious non-sliders) More complicated methods need to be used
                        if abs(cBlockA - pBlockA) < 112.5:  # 90 + 22.5 JUST IN CASE. not the full 90 + 45 since that would be one hell of a slider or dot note
                            try:
                                testAnglefromPosition = math.degrees(math.atan((pBlockP[1]-cBlockP[1])/(pBlockP[0]-cBlockP[0]))) % 360 # Replaces angle swing from block angle to slider angle
                            except ZeroDivisionError:       # Often we get a divide by zero error which is actually 90 or 270 degrees. Try putting a super large number into atan in your calculator ;)
                                if cBlockP[1] > pBlockP[1]:
                                    testAnglefromPosition = 90
                                else:
                                    testAnglefromPosition = 270
                            averageAngleOfBlocks = (cBlockA + pBlockA) / 2
                            if abs(testAnglefromPosition - averageAngleOfBlocks) <= 56.25:  # = 112.5 / 2 = 56.25
                                sliderTime = cBlockB - pBlockB
                                isSlider = True
                            else:
                                swingData.append(swing(cBlockB, cBlockA))
                        else:
                            swingData.append(swing(cBlockB, cBlockA))
                else: # 1/8 Check
                    if mapSplitData[i]['d'] == 8 or abs(cBlockA - pBlockA) < 90: # 90 degree check since 90 degrees is what most would consider the maximum angle for a slider or dot note
                        sliderTime = 0.125
                        isSlider = True
                    else:
                        swingData.append(swing(cBlockB, cBlockA))
            else:   # 1/32 Check
                sliderTime = 0.03125
                isSlider = True
            if isSlider:
                for f in range(1, len(mapSplitData)):   # We clearly know the last block is a slider with the current block under test. Skip to the one before the last block. Should realistically never search more than 5 blocks deep
                    blockIndex = i - f              # Index of the previous block to start comparisons with
                    if (mapSplitData[blockIndex]['b'] - mapSplitData[blockIndex - 1]['b'] > 2 * sliderTime):       # use 2x slider time to account for any "irregularities" / margin of error. We are only comparing pairs of blocks
                        pBlockB = mapSplitData[blockIndex]['b']                                             # Essentially finds then caches first block in the slider group
                        pBlockA = mapSplitData[blockIndex]['a']
                        pBlockP = [mapSplitData[blockIndex]['x'], mapSplitData[blockIndex]['y']]
                        break
                try:
                    swingData[-1].angle = math.degrees(math.atan((pBlockP[1]-cBlockP[1])/(pBlockP[0]-cBlockP[0]))) % 360 # Replaces angle swing from block angle to slider angle
                except ZeroDivisionError:       # Often we get a divide by zero error which is actually 90 or 270 degrees. Try putting a super large number into atan in your calculator ;)
                    if cBlockP[1] > pBlockP[1]:
                        swingData[-1].angle = 90
                    else:
                        swingData[-1].angle = 270
                guideAngle = 1150           # A random test value to check later
                for f in range(1, len(mapSplitData)):       # Checker that will try to find a guiding block (arrow block) for the slider angle prediction.
                    blockIndex = i - f
                    if mapSplitData[blockIndex]['b'] < pBlockB:     # Limits check to a little after the first slider block in the group
                        break
                    if mapSplitData[blockIndex]['d'] != 8:          # Breaks out of loop when it finds an arrow block
                        guideAngle = cut_direction_index[mapSplitData[blockIndex]['d']]
                        break
                if guideAngle != 1150:      # A test to see if guideAngle was actually changed
                    if abs(swingData[-1].angle - guideAngle) > 90:       # If this is true, the predicted angle is wrong, likely by 180 degrees wrong
                        if swingData[-1].angle >= 180:
                            swingData[-1].angle -= 180               # Apply Fix
                        else:
                            swingData[-1].angle += 180             
        else:
            swingData.append(swing(cBlockB, cBlockA))    # First Note Exception. will never be a slider or need to undergo any test
    return swingData
def swingStrainCalc(swingData: list[swing], leftOrRight): # False or 0 = Left, True or 1 = Right
    strainAmount = 0
    #TODO calculate strain from angle based on left or right hand
    for i in range(0, len(swingData)):
        if swingData[i].forehand:     #The Formula firse calculates by first normalizing the angle difference (/180) then using
            if leftOrRight:
                strainAmount += 2 * (((180 - abs(abs(right_handed_angle_strain_forehand - swingData[i].angle) - 180)) / 180)**2)          # Right Handed Forehand
            else:
                strainAmount += 2 * (((180 - abs(abs(left_handed_angle_strain_forehand - swingData[i].angle) - 180)) / 180)**2)           # Left Handed Forehand
        else:
            if leftOrRight:
                strainAmount += 2 * (((180 - abs(abs(right_handed_angle_strain_forehand - 180 - swingData[i].angle) - 180))/180)**2)           # Right Handed Backhand
            else:
                strainAmount += 2 * (((180 - abs(abs(left_handed_angle_strain_forehand - 180 - swingData[i].angle) - 180))/180)**2)           # Left Handed Backhand
    return strainAmount
def patternSplitter(swingData: list[swing]):    # Does swing speed analysis to split the long list of dictionaries into smaller lists of patterns containing lists of dictionaries
    for i in range(0, len(swingData)):   # Swing Frequency Analyzer
        if i > 0 and i+1 < len(swingData):    # Checks done so we don't try to access data that doesn't exist
            SF = 2/(swingData[i+1].time - swingData[i-1].time)    # Swing Frequency
        else:
            SF = 0
        swingData[i].frequency = SF
    patternFound = False
    SFList = [freq.frequency for freq in swingData]
    SFmargin = average(SFList) / 32
    patternList = []            # Pattern List
    tempPlist = []              # Temp Pattern List
    for i in range(0, len(swingData)):
        if i > 0:
            if (1 / (swingData[i].time - swingData[i-1].time)) - swingData[i].frequency <= SFmargin:    # Tries to find Patterns within margin
                if not patternFound:    # Found a pattern and it's the first one?
                    patternFound = True
                    del tempPlist[-1]
                    if len(tempPlist) > 0:  # We only want to store lists with stuff
                        patternList.append(tempPlist)
                    tempPlist = [swingData[i-1]]    #Store the 1st block of the pattern
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
def parityPredictor(patternData: list[list[swing]], bombData: list, leftOrRight):    # Parses through a List of Lists of Dictionaries to calculate the most likely parity for each pattern
    newPatternData = []
    for p in range(0, len(patternData)):
        testData1 = patternData[p]
        testData2 = copy.deepcopy(patternData[p])
        for i in range(0, len(testData1)):  # Build Forehand TestData Build
            if i > 0:
                testData1[i].forehand = not testData1[i-1].forehand     
            else:
                testData1[0].forehand = True
        forehandTest = swingStrainCalc(testData1, leftOrRight)    # Test data
        for i in range(0, len(testData2)):  # Build Banckhand Test Data
            if i > 0:
                testData2[i].forehand = not testData2[i-1].forehand     
            else:
                testData2[0].forehand = False
        backhandTest = swingStrainCalc(testData2, leftOrRight)    # Test data
        if forehandTest <= backhandTest:    #Prefer forehand starts over backhand if equal
            newPatternData += testData1      # Forehand gave a lower stress value, therefore is the best option in terms of hand placement for the pattern
        elif forehandTest > backhandTest:
            newPatternData += testData2
    for i in range(0, len(newPatternData)):
        newPatternData[i].strain = swingStrainCalc([newPatternData[i]], leftOrRight)  # Assigns individual strain values to each swing. Done like this in square brackets because the function expects a list.
        if i > 0:
            if newPatternData[i].forehand == newPatternData[i-1].forehand:
                newPatternData[i].reset = True
            else:
                newPatternData[i].reset = False
    return newPatternData
def staminaCalc(swingData: list):
    staminaList: list = []
    #TODO calculate strain from stamina drain


    return staminaList
def swingCurveCalc(swingData: list):
    curveList: list = []
    # TODO calculate swing curve between blocks based on their angels and positions (alwayd forwards looking at last block)
    # TODO calculate angle from position
    # calculate bezier points using bezier curve function
    # calculate bezier angles from points
    # subtract position angle from all bezier angles
    # take the deritive of the new bezier angles
    # peak of 2nd deritive is difficulty of the curve, or known angle change acceleration since no deritive = position, 1st = velocity, 2nd = accleration
    # Split the peak curve difficulty into their respective swing in swingdata
    for i in range(0, len(swingData)):
        if i < 0:
            pBlockPos = 0



            peakCurveDeritive = True
            curveList.append()
        else:
            curveList[i] = 0
    return curveList
def combineAndSortList(array1, array2, key):
    combinedArray: list[swing] = array1 + array2
    # combinedArray = sorted(combinedArray, key=lambda x: x[f'{key}'])  # once combined, sort by time       # DEPRECIATED
    combinedArray.sort(key=lambda x: x.time)
    return combinedArray
def loadInfoData(mapID: str):
    songPath = findSongPath(mapID)
    infoPath = findInfoFile(songPath)
    infoData = load_json_as_dict(infoPath)
    return infoData
def loadMapData(mapID: str, diffNum: int):
    songPath = findSongPath(mapID)
    diffList = findStandardDiffs(songPath)
    if diffNum in diffList:     # Check if the song is listed in the Info.dat file, otherwise exits programs
        diffPath = diffNum_to_diffPath(songPath, diffNum)
        mapData = load_json_as_dict(diffPath)
        return mapData
    else:
        print("Map doesn't exist locally. Are you sure you have the updated version?")
        print("Enter to Exit")
        input()
        exit()
def calculateTech(mapData):
    LeftMapData = splitMapData(mapData, 0)
    RightMapData = splitMapData(mapData, 1)
    bombData = splitMapData(mapData, 2)
    LeftSwingData = swingProcesser(LeftMapData)
    RightSwingData = swingProcesser(RightMapData)
    LeftPatternData = patternSplitter(LeftSwingData)
    RightPatternData = patternSplitter(RightSwingData)
    
    LeftSwingData = parityPredictor(LeftPatternData, bombData, False)
    RightSwingData = parityPredictor(RightPatternData, bombData, True)
    
    SwingData = combineAndSortList(LeftSwingData, RightSwingData, 'time')
    StrainList = [strain.strain for strain in SwingData]
    tech = average(StrainList)
    
    
    print(f"Calculacted Tech = {tech}")        # Put Breakpoint here if you want to see
    return tech

#'forehand': mostLikelyParityChecker(swingData, max(5, len(swingData)))
print("input map key")
mapKey = input()
mapKey = mapKey.replace("!bsr ", "")
infoData = loadInfoData(mapKey)
print(f'Choose Diff num: {findStandardDiffs(findSongPath(mapKey))}')
diffNum = int(input())
mapData = loadMapData(mapKey, diffNum)
t0 = time.time()
try:
    mapVersion = parse(mapData['version'])
except KeyError:
    mapVersion = parse(mapData['_version'])
if mapVersion < parse('3.0.0'):     # Try to figure out if the map is the V2 or V3 format
    maptype = 2
    mapData = V2_to_V3(mapData)
else:
    maptype = 3

calculateTech(mapData)
t1 = time.time()
print(f'Execution Time = {t1-t0}')









print("Done")
input()