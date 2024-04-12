import json
import requests
import numpy as m
import os
import Tech_Calculator.tech_calc as tech_calc
import Tech_Calculator._BackendFiles.setup as setup
import math
import csv
from collections import deque
import time

playerTestList = [3225556157461414,76561198225048252, 76561198059961776, 76561198072855418, 76561198075923914,
                  76561198255595858, 76561198404774259,
                  76561198110147969, 76561198081152434, 76561198204808809, 76561198072431907,
                  76561198989311828, 76561198960449289,
                  76561199104169308, 2769016623220259, 76561198410971373, 76561198153101808, 76561197995162898,
                  2169974796454690, 76561198166289091,
                  76561198285246326, 76561198802040781, 76561198110018904, 76561198044544317, 2092178757563532,
                  76561198311143750, 76561198157672038,
                  76561199050525271, 76561198272028078, 76561198027274310, 76561198073989976, 1922350521131465,
                  165749, 76561198267730787, 76561198373858287]

GlobalRatingsWeighing = {'passWeighing':7.5, 'accWeighing':30, 'techExponential': 7.9, 'techWeighing': 0.05}


playerTestList = [76561198267730787, 76561198373858287, 2169974796454690, 76561198296328455]

# playerTestList = [76561198296328455]

def average(lst, setLen=0):  # Returns the averate of a list of integers
    if len(lst) > 0:
        if setLen == 0:
            return sum(lst) / len(lst)
        else:
            return sum(lst) / setLen
    else:
        return 0
    
def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

def searchDiffIndex(diffNum, diffList):
    for f in range(0, len(diffList)):
        if diffList[f]['value'] == diffNum:
            return f

def convertSpeed(listOfMods):
    speed = 1
    if 'FS' in listOfMods:
        speed = 1.2
    if 'SF' in listOfMods:
        speed = 1.5
    if 'SS' in listOfMods:
        speed = 0.85
    return speed

def getKey(JSON):
    key = JSON['leaderboard']['song']['id']
    key = key.replace('x', '')
    return key

def AiAccPointsList(acc):
    pointList = [[1.0, 7.424],
                 [0.999, 6.241],
                 [0.9975, 5.158],
                 [0.995, 4.010],
                 [0.9925, 3.241],
                 [0.99, 2.700],
                 [0.9875, 2.303],
                 [0.985, 2.007],
                 [0.9825, 1.786],
                 [0.98, 1.618],
                 [0.9775, 1.490],
                 [0.975, 1.392],
                 [0.9725, 1.315],
                 [0.97, 1.256],
                 [0.965, 1.167],
                 [0.96, 1.101],
                 [0.955, 1.047],
                 [0.95, 1.000],
                 [0.94, 0.919],
                 [0.93, 0.847],
                 [0.92, 0.786],
                 [0.91, 0.734],
                 [0.9, 0.692],
                 [0.875, 0.606],
                 [0.85, 0.537],
                 [0.825, 0.480],
                 [0.8, 0.429],
                 [0.75, 0.345],
                 [0.7, 0.286],
                 [0.65, 0.246],
                 [0.6, 0.217],
                 [0.0, 0.000]]
    for i in range(0, len(pointList)):
        if pointList[i][0] <= acc:
            break

    if i == 0:
        i = 1

    middle_dis = (acc - pointList[i - 1][0]) / (pointList[i][0] - pointList[i - 1][0])

    return pointList[i - 1][1] + middle_dis * (pointList[i][1] - pointList[i - 1][1])

def PlayerAccPointsList(acc):
    pointList = [[1.0, 7.424],
                 [0.999, 6.241],
                 [0.9975, 5.158],
                 [0.995, 4.010],
                 [0.9925, 3.241],
                 [0.99, 2.700],
                 [0.9875, 2.303],
                 [0.985, 2.007],
                 [0.9825, 1.786],
                 [0.98, 1.618],
                 [0.9775, 1.490],
                 [0.975, 1.392],
                 [0.9725, 1.315],
                 [0.97, 1.256],
                 [0.965, 1.167],
                 [0.96, 1.094],
                 [0.955, 1.039],
                 [0.95, 1.000],
                 [0.94, 0.931],
                 [0.93, 0.867],
                 [0.92, 0.813],
                 [0.91, 0.768],
                 [0.9, 0.729],
                 [0.875, 0.650],
                 [0.85, 0.581],
                 [0.825, 0.522],
                 [0.8, 0.473],
                 [0.75, 0.404],
                 [0.7, 0.345],
                 [0.65, 0.296],
                 [0.6, 0.256],
                 [0.0, 0.000]]
    for i in range(0, len(pointList)):
        if pointList[i][0] <= acc:
            break

    if i == 0:
        i = 1

    middle_dis = (acc - pointList[i - 1][0]) / (pointList[i][0] - pointList[i - 1][0])

    return pointList[i - 1][1] + middle_dis * (pointList[i][1] - pointList[i - 1][1])

def inflate(pp):
    return (650 * math.pow(pp, 1.3)) / math.pow(650, 1.3)

def load_Song_Stats(dataJSON, speed, key, retest=False, versionNum=-1):
    s = requests.Session()
    diffNum = dataJSON['leaderboard']['difficulty']['value']
    hash = dataJSON['leaderboard']['song']['hash'].upper()
    AiJSON = {}
    try:
        with open(f"_AIcache/{hash}/{diffNum} {speed}.json", encoding='ISO-8859-1') as score_json:      # Checkes if the result has already been calculated before
            AiJSON = json.load(score_json)
        print("Cache Hit")
        try:
            cacheVNum = AiJSON['versionNum']
        except:
            cacheVNum = -1
        finally:
            if retest and cacheVNum != versionNum:
                infoData = setup.loadInfoData(key, False)
                mapData = setup.loadMapData(key, diffNum, False)
                bpm = infoData['_beatsPerMinute'] * speed
                AiJSON['lackStats'] = tech_calc.mapCalculation(mapData, bpm, False, False)
                AiJSON['versionNum'] = versionNum
                result = s.get(
                    f"https://bs-replays-ai.azurewebsites.net/bl-reweight/{hash}/Standard/{diffNum}")
                if result.text == 'Not found':
                    AiJSON['AIstats'] = {}
                    AiJSON['AIstats']['balanced'] = 0
                    AiJSON['AIstats']['expected_acc'] = 0
                    AiJSON['AIstats']['passing_difficulty'] = 0
                else:
                    AiJSON['AIstats'] = json.loads(result.text)
                try:
                    os.mkdir(f"_AIcache/{hash}")
                except:
                    print("Existing Folder")
                with open(f"_AIcache/{hash}/{diffNum} {speed}.json", 'w') as score_json:
                    json.dump(AiJSON, score_json, indent=4)

    except:
        print("Requesting from AI and Calculator")
        retryTime = 3
        while(True):    # Loop until we get a successful request result from the API
            result = s.get(
                f"https://stage.api.beatleader.net/ppai2/{hash}/Standard/{diffNum}")
            if result.status_code == 200:
                break
            else:
                if (retryTime <= 5):
                    print(f"Unable to retrieve stats with code {result.status_code}, retrying in {retryTime} seconds upto 5 seconds")
                    time.sleep(retryTime)
                    retryTime += 2
                else:       # Breaking out and returning 0. Unable to get all required data
                    print(f"Unable to get all required data on map {key} and removing data point. Continuing in 2 seconds")
                    time.sleep(2)
                    return 0

        if result.text == 'Not found':
            AiJSON['AIstats'] = {'accrating': 0, 'predicted_acc': 0}
        else:
            AiJSON['AIstats'] = json.loads(result.text)
        infoData = setup.loadInfoData(key, False)
        mapData = setup.loadMapData(key, diffNum, False)
        bpm = infoData['_beatsPerMinute'] * speed
        if mapData != None:
            AiJSON['lackStats'] = tech_calc.mapCalculation(mapData, bpm, False, False)
        else:
            AiJSON['lackStats'] = {'balanced_tech': 0, 'balanced_pass_diff': 0}
        try:
            os.mkdir(f"_AIcache/{hash}")
        except:
            print("Existing Folder")
        with open(f"_AIcache/{hash}/{diffNum} {speed}.json", 'w') as score_json:
            json.dump(AiJSON, score_json, indent=4)

    return AiJSON

def returnScores(userID, scoreCount):
    s = requests.Session()
    playerJSON = []
    pageNumber = 1
    while scoreCount > 0:       # New API limits is 100 requests per call, so iterate through until all requestes scores are obtained
        result = s.get(
            f"https://api.beatleader.xyz/player/{userID}/scores?sortBy=pp&order=desc&page={pageNumber}&count={100}")
        if result.status_code == 200:
            playerJSON += json.loads(result.text)['data']
            scoreCount -= 100
            pageNumber += 1
        else:
            print(f"Failed with code {result.status_code}, Retrying.")
    return playerJSON

def returnAllScores(userID):
    s = requests.Session()
    playerJSON = []
    pageNumber = 1
    scoreCount = 100

    while scoreCount >= 100:       # New API limits is 100 requests per call, so iterate through until all requestes scores are obtained
        result = s.get(
            f"https://api.beatleader.xyz/player/{userID}/scores?sortBy=pp&order=desc&page={pageNumber}&count={100}")
        if result.status_code == 200:
            playerJSON += json.loads(result.text)['data']
            scoreCount = len(json.loads(result.text)['data'])       # Stores number of scores retrieved during this request
            pageNumber += 1
        else:
            print(f"Failed with code {result.status_code}, Retrying.")
            time.sleep(3)
    return playerJSON

def getPlayerName(userID):
    s = requests.Session()
    result = s.get(f"https://api.beatleader.xyz/player/{userID}/")
    return json.loads(result.text)['name']

def calculatePP(acc, starRatings, ratingsWeighing={'passWeighing':15, 'accWeighing':30, 'techExponential': 8, 'techWeighing': 0.01}):
    passPP = ratingsWeighing['passWeighing'] * math.exp(math.pow(starRatings['passRating'], 1 / 2.62)) - 30
    if passPP < 0:
        passPP = 0

    playerTechPP = math.exp(ratingsWeighing['techExponential'] * acc) * starRatings['techRating'] * ratingsWeighing['techWeighing']
    playerAccPP = PlayerAccPointsList(acc) * starRatings['accRating'] * ratingsWeighing['accWeighing']

    return passPP, playerAccPP, playerTechPP

def writePpTestResultsToFile(playerName, Data):
    Data = sorted(Data, key=lambda x: x.get('playerPP', 0), reverse=True)
    playerName = playerName.replace("|", "")
    filePath = f'_PlayerStats/{playerName}'

    try:
        with open(f'{filePath}/dataNewPlayerPP.json', 'w') as data_json:
            json.dump(Data, data_json, indent=4)
    except FileNotFoundError:
        os.mkdir(str(f'{filePath}'))
        with open(f'{filePath}/dataNewPlayerPP.json', 'w') as data_json:
            json.dump(Data, data_json, indent=4)

    Data = sorted(Data, key=lambda x: x.get('passRating', 0), reverse=True)
    with open(f'{filePath}/dataStar.json', 'w') as data_json:
        json.dump(Data, data_json, indent=4)

    Data = sorted(Data, key=lambda x: x.get('acc', 0), reverse=True)
    with open(f'{filePath}/dataAcc.json', 'w') as data_json:
        json.dump(Data, data_json, indent=4)

    Data = sorted(Data, key=lambda x: x.get('tech', 0), reverse=True)
    with open(f'{filePath}/dataTech.json', 'w') as data_json:
        json.dump(Data, data_json, indent=4)

    Data = sorted(Data, key=lambda x: x.get('oldPP', 0), reverse=True)
    with open(f'{filePath}/dataOldPP.json', 'w') as data_json:
        json.dump(Data, data_json, indent=4)

    
    
    Data = sorted(Data, key=lambda x: x.get('playerPP', 0), reverse=True)
    excelFileName = os.path.join(f"{filePath}/{playerName}_export.csv")
    try:
        x = open(excelFileName, 'w', newline="", encoding='utf8')
    except:
        print(f'File write failed. Close any applications using {excelFileName} then press Enter')
        input()
        try:
            x = open(excelFileName, 'w', newline="", encoding='utf8')
        except:
            print('Failed again. Exiting....')
            input()
    finally:
        dict_writer = csv.DictWriter(x, Data[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(Data)
        x.close()

def newPlayerStats(userID, retest=False, versionNum=-1):
    songStats = {}
    newStats = []

    playerJSON = returnAllScores(userID)
    playerName = getPlayerName(userID)

    if retest:
        print("Will recalulate and update tech data")
    for i in range(0, len(playerJSON)):
        if playerJSON[i]['pp'] != 0:
            key = getKey(playerJSON[i])
            if playerJSON[i]['leaderboard']['difficulty']['status'] == 3:              # Checks if the difficulty is ranked. discords qualified maps
                if playerJSON[i]['leaderboard']['difficulty']['modeName'] == 'Standard':  # Filters out only standard maps/difficulties
                # if [i for i in ['Standard', 'OneSaber'] if i in playerJSON[i]['leaderboard']['difficulty']['modeName']]:
                    speed = convertSpeed(playerJSON[i]['modifiers'].split(','))
                    
                    songStats = load_Song_Stats(playerJSON[i], speed, key, retest, versionNum)
                    if songStats == 0:
                        continue    # Song status failed to get the remaining required data, so skipping.
                    
                    modifier = playerJSON[i]['modifiers']
                    if "FS" in modifier:
                        modifier = "FS"
                    elif "SFS" in modifier:
                        modifier = "SFS"
                    elif "SS" in modifier:
                        modifier = "SS"
                    else:
                        modifier = "none"
                    AIacc = songStats['AIstats'][modifier]['predicted_acc']
                    playerACC = playerJSON[i]['accuracy']
                    passRating = songStats['lackStats']['balanced_pass_diff']
                    techRating = songStats['lackStats']['balanced_tech']
                    
                    if AIacc != 0:  # Estimate AI stars if none exists.
                        accRating = 15 / AiAccPointsList(AIacc)
                    else:
                        tinyTech = 0.0208 * techRating + 1.1284  # https://www.desmos.com/calculator/yaqyyomsp9
                        accRating = (-math.pow(tinyTech, -passRating) + 1) * 8 + 2 + 0.01 * techRating * passRating

                    starRatings = {'passRating': passRating, 'accRating': accRating, 'techRating': techRating}
                    
                    passPP, playerAccPP, playerTechPP = calculatePP(playerACC, starRatings, GlobalRatingsWeighing)
                    playerPP = passPP + playerAccPP + playerTechPP
                    
                    newStats.append({})
                    newStats[-1]['name'] = playerJSON[i]['leaderboard']['song']['name']
                    newStats[-1]['diff'] = playerJSON[i]['leaderboard']['difficulty']['difficultyName']
                    newStats[-1]['Pass Rating'] = passRating
                    newStats[-1]['Acc Rating'] = accRating
                    newStats[-1]['Tech Rating'] = techRating
                    newStats[-1]['BL 95% Star'] = playerJSON[i]['leaderboard']['difficulty']['stars']
                    newStats[-1]['Modifiers'] = playerJSON[i]['modifiers']
                    newStats[-1]['acc'] = playerACC
                    newStats[-1]['oldPP'] = playerJSON[i]['pp']
                    newStats[-1]['passPP'] = passPP
                    newStats[-1]['techPP'] = playerTechPP
                    newStats[-1]['accPP'] = playerAccPP
                    newStats[-1]['playerPP'] = playerPP

    newStats = sorted(newStats, key=lambda x: x.get('Pass Rating', 0), reverse=True)
    rollingSumWindowBase = 16       # Numbers of averaging buckets per number (8 = averaging sections within one star rating)
    rollingSumWindow = rollingSumWindowBase
    rollingSum = deque()
    DeviationList = []
    for i in range(0, len(newStats)):
        if i > 0:
            # Max 0 to prevent negative numbers appearing in the list index
            rollingSumWindow = rollingSumWindowBase / (newStats[max(i - int(rollingSumWindowBase / 2), 0)]['Pass Rating'] - newStats[i]['Pass Rating'])
            rollingSumWindow = clamp(rollingSumWindow, 4, 128)
        else:
            rollingSumWindow = 1

        if len(rollingSum) >= rollingSumWindow:
            rollingSum.popleft()
        if len(rollingSum) < rollingSumWindow:
            rollingSum.append(newStats[i]['playerPP'])
        ppAverage = average(rollingSum)

        newStats[i]['Moving Average'] = ppAverage
        Deviation = abs(ppAverage - newStats[i]['playerPP'])
        newStats[i]['Deviation from Moving Average'] = Deviation
        DeviationList.append(Deviation)

    writePpTestResultsToFile(playerName, newStats)
    return average(DeviationList), len(DeviationList)

def techVersionHandler(retest=False):
    if retest:
        try:
            f = open('Tech_Calculator/_BackendFiles/techversion.txt', 'r')  # Use This to try and find an existing file
            versionNum = int(f.read()) + 1
            f = open('Tech_Calculator/_BackendFiles/techversion.txt', 'w')
            f.write(str(versionNum))
            f.close()
        except FileNotFoundError:
            try:
                f = open('_BackendFiles/techversion.txt', 'r')  # Use This to try and find an existing file
                versionNum = int(f.read()) + 1
                f = open('Tech_Calculator/_BackendFiles/techversion.txt', 'w')
                f.write(str(versionNum))
                f.close()
            except FileNotFoundError:
                try:
                    f = open('Tech_Calculator/_BackendFiles/techversion.txt', 'w')
                except:
                    f = open('_BackendFiles/techversion.txt', 'w')
                f.write(str(0))
                versionNum = 0
        finally:
            f.close()
    else:
        versionNum = -1
    
    return versionNum

def deviationTester(playerTestList: list, retest, versionNum):
    weightedDeviationSum = 0
    TestDetails = []
    for i in range(0, len(playerTestList)):
        averageDeviation, numOfScores = newPlayerStats(playerTestList[i], retest, versionNum)
        TestDetails.append({'ID': playerTestList[i], 'Average Deviation': averageDeviation, 'Number of scores': numOfScores})
        weightedDeviationSum += averageDeviation * numOfScores          # More scores means the average deviation is more accurate
        print(f"Finished {playerTestList[i]}")
    
    weightedDeviation = weightedDeviationSum / sum([i["Number of scores"] for i in TestDetails])      # Strip out the number of scores to get a weighted deviation based on scores set
    return TestDetails, weightedDeviation

if __name__ == "__main__":
    print("Re-test tech calculator? y/n")
    retest = input()
    if retest.lower() == 'y':
        retest = True
    else:
        retest = False
    
    versionNum = techVersionHandler(retest)

    TestDetails, weightedDeviation = deviationTester(playerTestList, retest, versionNum)

    print(f"Tested Players: {TestDetails}")
    print(f"Weighted deviation: {weightedDeviation}")

    try:
        with open(f'deviationResults/deviation.json', 'w') as data_json:
            json.dump(TestDetails, data_json, indent=4)
    except FileNotFoundError:
        os.mkdir(str(f'deviationResults'))
        with open(f'deviationResults/deviation.json', 'w') as data_json:
            json.dump(TestDetails, data_json, indent=4)

    print("done")
    print("Press Enter to Exit")
    input()
