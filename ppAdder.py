from tkinter.filedialog import askopenfile
import json
import os


jsonPath = askopenfile(mode ='r', filetypes =[('newPPJSON', '*.json')])
JSON_Path = jsonPath.name
with open(JSON_Path, encoding='ISO-8859-1') as playlist_json:
    newPPJSON = json.load(playlist_json)

jsonPath = askopenfile(mode ='r', filetypes =[('oldPPJSON', '*.json')])
JSON_Path = jsonPath.name
with open(JSON_Path, encoding='ISO-8859-1') as playlist_json:
    oldPPJSON = json.load(playlist_json)

oldPPTotal = 0
newPPTotal = 0

for i, score in enumerate(newPPJSON):
    try:
        newPPTotal += newPPJSON[i]['playerPP'] * (0.965 ** i)
    except:
        print("New PP done")
for i, score in enumerate(oldPPJSON):
    try:
        oldPPTotal += oldPPJSON[i]['oldPP'] * (0.965 ** i)
    except:
        print("Old PP done")
print(f"Old PP from plays in list is {oldPPTotal}")
print(f"New PP from plays in list is {newPPTotal}")
print("Press Enter to Exit")
input()
