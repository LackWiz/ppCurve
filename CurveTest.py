import json
import requests
import numpy as m
import os
import Tech_Calculator.tech_calc as tech_calc
import Tech_Calculator._BackendFiles.setup as setup
import math

playerTestList = [3225556157461414,76561198225048252, 76561198059961776, 76561198072855418, 76561198075923914,
                  76561198255595858, 76561198404774259,
                  76561198110147969, 76561198081152434, 76561198204808809, 76561198072431907,
                  76561198989311828, 76561198960449289,
                  76561199104169308, 2769016623220259, 76561198410971373, 76561198153101808, 76561197995162898,
                  2169974796454690, 76561198166289091,
                  76561198285246326, 76561198802040781, 76561198110018904, 76561198044544317, 2092178757563532,
                  76561198311143750, 76561198157672038,
                  76561199050525271, 76561198272028078, 76561198027274310, 76561198073989976]


# playerTestList = [76561198073989976]

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


def pointList1(acc):
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


def pointList2(acc):
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
                    # AiJSON['expected_acc'] = 1
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
        result = s.get(
            f"https://stage.api.beatleader.net/ppai2/{hash}/Standard/{diffNum}")
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


def newPlayerStats(userID, scoreCount, retest=False, versionNum=-1):
    s = requests.Session()
    songStats = {}
    newStats = []
    pageNumber = 0
    playerJSON = {'data': []}
    
    while scoreCount > 0:       # New API limits is 100 requests per call, so iterate through until all requestes scores are obtained
        pageNumber += 1
        result = s.get(
            f"https://api.beatleader.xyz/player/{userID}/scores?sortBy=pp&order=desc&page={pageNumber}&count={100}")
        playerJSON['data'] += json.loads(result.text)['data']
        scoreCount -= 100

    result = s.get(f"https://api.beatleader.xyz/player/{userID}/")
    playerName = json.loads(result.text)['name']
    if retest:
        print("Will recalulate and update tech data")
    for i in range(0, len(playerJSON['data'])):
        if playerJSON['data'][i]['pp'] != 0:
            key = getKey(playerJSON['data'][i])
            if playerJSON['data'][i]['leaderboard']['difficulty']['status'] == 3:              # Checks if the difficulty is ranked. discords qualified maps
                if playerJSON['data'][i]['leaderboard']['difficulty']['modeName'] == 'Standard':  # Filters out only standard maps/difficulties
                # if [i for i in ['Standard', 'OneSaber'] if i in playerJSON['data'][i]['leaderboard']['difficulty']['modeName']]:
                    speed = convertSpeed(playerJSON['data'][i]['modifiers'].split(','))
                    songStats = load_Song_Stats(playerJSON['data'][i], speed, key, retest, versionNum)
                    modifier = playerJSON['data'][i]['modifiers']
                    if "FS" in modifier:
                        modifier = "FS"
                    elif "SFS" in modifier:
                        modifier = "SFS"
                    elif "SS" in modifier:
                        modifier = "SS"
                    else:
                        modifier = "none"
                    AIacc = songStats['AIstats'][modifier]['predicted_acc']
                    playerACC = playerJSON['data'][i]['accuracy']
                    passRating = songStats['lackStats']['balanced_pass_diff']
                    tech = songStats['lackStats']['balanced_tech']

                    passPP = 15.2 * math.exp(math.pow(passRating, 1 / 2.62)) - 30

                    if passPP < 0:
                        passPP = 0

                    if AIacc != 0:
                        AI600Star = 15 / pointList1(AIacc + 0.0022)
                    else:
                        tinyTech = 0.0208 * tech + 1.1284  # https://www.desmos.com/calculator/yaqyyomsp9
                        AI600Star = (-math.pow(tinyTech, -passRating) + 1) * 8 + 2 + 0.01 * tech * passRating

                    playerTechPP = math.exp(1.9 * playerACC) * 1.08 * tech
                    playerAccPP = pointList2(playerACC) * AI600Star * 34
                    playerPP = inflate(passPP + playerAccPP + playerTechPP)

                    newStats.append({})
                    newStats[-1]['name'] = playerJSON['data'][i]['leaderboard']['song']['name']
                    newStats[-1]['diff'] = playerJSON['data'][i]['leaderboard']['difficulty']['difficultyName']
                    newStats[-1]['Pass'] = passRating
                    newStats[-1]['Acc'] = AI600Star
                    newStats[-1]['Tech'] = tech
                    newStats[-1]['Modifiers'] = playerJSON['data'][i]['modifiers']
                    newStats[-1]['acc'] = playerACC
                    newStats[-1]['oldPP'] = playerJSON['data'][i]['pp']
                    newStats[-1]['passPP'] = passPP
                    newStats[-1]['techPP'] = playerTechPP
                    newStats[-1]['accPP'] = playerAccPP
                    newStats[-1]['playerPP'] = playerPP


    newStats = sorted(newStats, key=lambda x: x.get('playerPP', 0), reverse=True)
    playerName = playerName.replace("|", "")

    filePath = f'_PlayerStats/{playerName}'

    try:
        with open(f'{filePath}/dataNewPlayerPP.json', 'w') as data_json:
            json.dump(newStats, data_json, indent=4)
    except FileNotFoundError:
        os.mkdir(str(f'{filePath}'))
        with open(f'{filePath}/dataNewPlayerPP.json', 'w') as data_json:
            json.dump(newStats, data_json, indent=4)

    newStats = sorted(newStats, key=lambda x: x.get('passRating', 0), reverse=True)
    with open(f'{filePath}/dataStar.json', 'w') as data_json:
        json.dump(newStats, data_json, indent=4)

    newStats = sorted(newStats, key=lambda x: x.get('acc', 0), reverse=True)
    with open(f'{filePath}/dataAcc.json', 'w') as data_json:
        json.dump(newStats, data_json, indent=4)

    newStats = sorted(newStats, key=lambda x: x.get('tech', 0), reverse=True)
    with open(f'{filePath}/dataTech.json', 'w') as data_json:
        json.dump(newStats, data_json, indent=4)

    newStats = sorted(newStats, key=lambda x: x.get('oldPP', 0), reverse=True)
    with open(f'{filePath}/dataOldPP.json', 'w') as data_json:
        json.dump(newStats, data_json, indent=4)


if __name__ == "__main__":
    print("Re-test tech calculator? y/n")
    retest = input()
    if retest.lower() == 'y':
        retest = True
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
        retest = False
        versionNum = -1

    for i in range(0, len(playerTestList)):
        newPlayerStats(playerTestList[i], 1000, retest, versionNum)
        print(f"Finished {playerTestList[i]}")
    print("done")
    print("Press Enter to Exit")
    input()
