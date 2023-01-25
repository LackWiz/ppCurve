from tkinter.filedialog import askopenfile
import json
import os
import matplotlib.pyplot as plt
from matplotlib.ticker import (FormatStrFormatter)
import numpy as np

jsonPath = askopenfile(mode ='r', filetypes =[('newPPJSON', '*.json')])
JSON_Path = jsonPath.name
with open(JSON_Path, encoding='ISO-8859-1') as playlist_json:
    PPJSON = json.load(playlist_json)

xPair = []
y1Pair = []
y2Pair = []

print("xKey to use")
xKey = input()
print("y1Key to use")
y1Key = input()
print("y2Key to use (type NULL or leave blank if only need one plot)")
y2Key = input()
if y2Key == '':
    y2Key = 'null'

for i, score in enumerate(PPJSON):
    try:
        xPair.append(PPJSON[i][f'{xKey}'])
        y1Pair.append(PPJSON[i][f'{y1Key}'])
        if y2Key.lower() != 'null':
            y2Pair.append(PPJSON[i][f'{y2Key}'])
    except:
        pass
    finally:
        print(i)
        

fig, ax = plt.subplots(figsize = (15, 8))

ax.xaxis.set_major_formatter(FormatStrFormatter('% 1.1f'))

ax.set_title("Graph")
ax.set_xlabel(xKey, fontsize=12)
ax.set_ylabel(y1Key, fontsize=12)

#ax.set_xticks(np.linspace(0,20,21))
#ax.set_yticks(np.linspace(0,20,21))
#ax.set_yticks(np.linspace(0,1000,21))

ax.plot(xPair, y1Pair, 'o', label = y1Key)
if y2Key.lower() != 'null':
    ax.plot(xPair, y2Pair, 'o', label = y2Key)

plt.xlim(0,20)
plt.ylim(0,1000)
plt.grid(visible=True,which='major',axis='both')

ax.legend(fontsize=10, fancybox=False, edgecolor='black', bbox_to_anchor=(1.1,1))
fig.tight_layout()
plt.show()

print("done")
print("Press Enter to Exit")
input()