"""
Update the station details with the data start and end years. 

This field has been filled in previous data retrievals from BoM, but was not filled in the 2019 retrieval.

Author:
Craig Arthur
2022-08-24
"""

import os
import pandas as pd

dataPath = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\2019\Daily"
stnFile = os.path.join(dataPath, "DC02D_StnDet_999999999632559.txt")

stndf = pd.read_csv(stnFile)
stndf.set_index('Bureau of Meteorology Station Number', drop=False, inplace=True)
for stnNum in stndf['Bureau of Meteorology Station Number']:
    obsfile = os.path.join(dataPath, f"DC02D_Data_{stnNum:06d}_999999999632559.txt")
    obsdf = pd.read_csv(obsfile)
    startYear = obsdf.Year.min()
    endYear = obsdf.Year.max()
    stndf.loc[stnNum, 'First year of data supplied in data file'] = startYear
    stndf.loc[stnNum, 'Last year of data supplied in data file'] = endYear

stndf.reset_index(drop=True, inplace=True)

stnFile = os.path.join(dataPath, "DC02D_StnDet_999999999632559_updated.txt")
stndf.to_csv(stnFile, index=False)