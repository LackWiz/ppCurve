import json
import os
import csv
import sys
sys.path.insert(0, 'Tech_Calculator/_BackendFiles')
import MapDownloader

def load_BSPath():
    try:
        f = open('Tech_Calculator/_BackendFiles/bs_path.txt', 'r')
        bsPath = f.read()
    except FileNotFoundError:
        try:
            f = open('_BackendFiles/bs_path.txt', 'r')
            bsPath = f.read()
        except:
            print('Enter Beat Saber Install Folder:')
            # TODO: validate path
            #bsPath = askdirectory()
            bsPath = input()
            if bsPath[-1] not in ['\\', '/']:  # Checks if song path is empty
                bsPath += os.sep
            try:
                f = open('Tech_Calculator/_BackendFiles/bs_path.txt', 'w')
            except:
                f = open('_BackendFiles/bs_path.txt', 'w')
            f.write(bsPath)
    finally:
        f.close()
    return bsPath

def writeToExcel(folderName,fileName,headerList,dataList):
    excelFileName = os.path.join(f"{folderName}/{fileName} export.csv")
    try:
        x = open(excelFileName, 'w', newline="", encoding='utf8')
    except FileNotFoundError:
        print(f'Making {folderName} Folder')
        os.mkdir(folderName)
        x = open(excelFileName, 'w', newline="")
    finally:
        writer = csv.writer(x)
        writer.writerow(headerList)
        writer.writerows(dataList)
        x.close()
def writeSingleToExcel(folderName,fileName,headerList,data):
    excelFileName = os.path.join(f"{folderName}/{fileName} export.csv")
    try:
        x = open(excelFileName, 'w', newline="", encoding='utf8')
    except FileNotFoundError:
        print(f'Making {folderName} Folder')
        os.mkdir(folderName)
        x = open(excelFileName, 'w', newline="")
    finally:
        writer = csv.writer(x)
        writer.writerow(headerList)
        writer.writerow(data.returnList())
        x.close()
def searchDiffNum(diffNum, diffList):
    for f in range(0, len(diffList)):
        if diffList[f]['value'] == diffNum:
            return f
def findSongPath(song_id: str, isuser=True): # Returns the song folder path by searching the custom songs folder

    if isuser:
        bsPath = load_BSPath()
        bsPath = os.path.join(bsPath, "Beat Saber_Data")
        bsPath = os.path.join(bsPath, "CustomLevels")
        # Creating the full path as we may not actually be within a
        # Beat Saber install (I'm running this from within a VM.)
        os.makedirs(bsPath, exist_ok=True)
    else:
        bsPath = "_songCache"

    bsPath += os.sep

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
def load_json_as_dict(path: str):    # Reads, then loads and returns JSON as a dictionary
    with open(path, 'rb') as json_dat:
        dat = json.loads(json_dat.read())   
        # dat = json.load(json_dat)
    return dat
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
def findCharacteristicIndex(songPath: str, characteristic: str):
    infoDat = load_json_as_dict(findInfoFile(songPath))
    characteristicIndex = findStandardCharacteristicIndex(infoDat, characteristic)
    return characteristicIndex
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
def loadInfoData(mapID: str, isuser=True):
    songPath = findSongPath(mapID, isuser)
    infoPath = findInfoFile(songPath)
    infoData = load_json_as_dict(infoPath)
    return infoData
def loadMapData(mapID: str, diffNum: int, isuser=True, index=False):
    songPath = findSongPath(mapID, isuser)
    diffList = findStandardDiffs(songPath)
    charIndex = findCharacteristicIndex(songPath, "Standard")
    if diffNum in diffList:     # Check if the song is listed in the Info.dat file, otherwise exits programs
        diffPath = diffNum_to_diffPath(songPath, diffNum)
        mapData = load_json_as_dict(diffPath)
        if index:
            return mapData, charIndex
        return mapData
    else:
        print(f"Map {mapID} Diff {diffNum} doesn't exist locally. Are you sure you have the updated version?")
        if isuser:
            print("Enter to Exit")
            input()
            exit()
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



