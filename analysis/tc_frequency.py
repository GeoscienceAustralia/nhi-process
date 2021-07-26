"""
tc_frequency.py - plot the annual frequency of TCs based on best available data
from BoM.

Source: http://www.bom.gov.au/clim_data/IDCKMSTM0S.csv

NOTE:: A number of minor edits are required to ensure the data is correctly
read. The original source file contains some carriage return characters in the
"COMMENTS" field which throws out the normal `pandas.read_csv` function. If it's
possible to programmatically remove those issues, then we may look to fully
automate this script to read directly from the URL.

"""
from os.path import join as pjoin
from datetime import datetime

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

mpl.rcParams['grid.linestyle'] = ':'
mpl.rcParams['grid.linewidth'] = 0.5
mpl.rcParams['savefig.dpi'] = 600
locator = mdates.AutoDateLocator(minticks=10, maxticks=20)
formatter = mdates.ConciseDateFormatter(locator)

def season(year, month):
    """
    Determine the southern hemisphere TC season based on the year and month value.
    If the month is earlier than June, we assign the season to be the preceding year.

    :params int year: Year
    :params int month: Month

    """
    s = year
    if month < 6:
        s = year - 1
    return int(s)

# Start with the default TC best track database:
inputPath = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\tc"
dataFile = pjoin(inputPath, r"IDCKMSTM0S - 20210722.csv")
outputPath = r"X:\georisk\HaRIA_B_Wind\data\derived\tc\tcfrequency"
usecols = [0, 1, 2, 7, 8, 16, 49, 53]
colnames = ['NAME', 'DISTURBANCE_ID', 'TM', 'LAT', 'LON',
            'CENTRAL_PRES', 'MAX_WIND_SPD', 'MAX_WIND_GUST']
dtypes = [str, str, str, float, float, float, float, float]
df = pd.read_csv(dataFile, skiprows=4, usecols=usecols,
                 dtype=dict(zip(colnames, dtypes)), na_values=[' '])



df['TM'] = pd.to_datetime(df.TM, format="%Y-%m-%d %H:%M", errors='coerce')
df['year'] = pd.DatetimeIndex(df['TM']).year
df['month'] = pd.DatetimeIndex(df['TM']).month
df['season'] = df[['year', 'month']].apply(lambda x: season(*x), axis=1)


# Determine season based on the coded disturbance identifier:
# This is of the form "AU201617_<ID>". The first four digits represent the first
# year of the season, the last two the second year of the season
# (which runs November - April)

new = df['DISTURBANCE_ID'].str.split("_", expand=True)
df['ID'] = new[1]
df['IDSEAS'] = new[0].str[:6].str.strip('AU').astype(int)
# Calculate the number of unique values in each season:
sc = df.groupby(['IDSEAS']).nunique()

# Determine the number of severe TCs. 
# take the number of TCs with maximum wind speed > 32 m/s
xc = df.groupby([ 'DISTURBANCE_ID',]).agg({
    'CENTRAL_PRES': np.min,
    'MAX_WIND_GUST': np.max,
    'MAX_WIND_SPD': np.max,
    'ID':np.max, 'IDSEAS': 'max'})
ns = xc[xc['MAX_WIND_SPD'] > 32].groupby('IDSEAS').nunique()['ID']


idx = sc.index >= 1970
idx2 = sc.index >= 1985
nsidx = ns.index >= 1970
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.bar(sc.index[idx], sc.ID[idx], label="All TCs")
ax.bar(ns.index[nsidx], ns.values[nsidx], color='orange', label="Severe TCs")
ax.grid(True)
ax.set_yticks(np.arange(0, 21, 2))
ax.set_xlabel("Season")
ax.set_ylabel("Count")
ax.legend(fontsize='small')
plt.text(0.0, -0.1, "Source: http://www.bom.gov.au/clim_data/IDCKMSTM0S.csv",
         transform=ax.transAxes, fontsize='x-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='x-small', ha='right')
plt.savefig(pjoin(outputPath, "TC_frequency.png"), bbox_inches='tight')

# Add regression lines - one for all years >= 1970, another for all years >= 1985
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.bar(sc.index[idx], sc.ID[idx], label="All TCs")
ax.bar(ns.index[nsidx], ns.values[nsidx], color='orange', label="Severe TCs")
sns.regplot(x=sc.index[idx], y=sc.ID[idx], ax=ax, color='0.5', scatter=False, label='1970-2020 trend')
sns.regplot(x=sc.index[idx2], y=sc.ID[idx2], ax=ax, color='r', scatter=False, label='1985-2020 trend')
ax.grid(True)

ax.set_yticks(np.arange(0, 21, 2))

ax.set_xlabel("Season")
ax.set_ylabel("Count")
ax.legend(fontsize='small')
plt.text(0.0, -0.1, "Source: http://www.bom.gov.au/clim_data/IDCKMSTM0S.csv",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "TC_frequency_reg.png"), bbox_inches='tight')
xlim = ax.get_xlim()


ns.to_csv(pjoin(outputPath, "severe_tcs.csv"))
sc.to_csv(pjoin(outputPath, "all_tcs.csv"))






dataFile = pjoin(inputPath, r"Objective Tropical Cyclone Reanalysis - QC.csv")
usecols = [0, 1, 2, 7, 8, 11, 12]
colnames = ['NAME', 'DISTURBANCE_ID', 'TM', 'LAT', 'LON',
            'adj. ADT Vm (kn)', 'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)']
dtypes = [str, str, str, float, float, float, float]
otcrdf = pd.read_csv(dataFile, usecols=usecols,
                     dtype=dict(zip(colnames, dtypes)), na_values=[' '], nrows=13743)
colrenames = {'adj. ADT Vm (kn)':'MAX_WIND_SPD',
              'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)': 'CENTRAL_PRES'}
otcrdf.rename(colrenames, axis=1, inplace=True)
otcrdf['TM'] = pd.to_datetime(otcrdf.TM, format="%Y-%m-%d %H:%M", errors='coerce')
otcrdf['year'] = pd.DatetimeIndex(otcrdf['TM']).year
otcrdf['month'] = pd.DatetimeIndex(otcrdf['TM']).month
otcrdf['season'] = otcrdf[['year', 'month']].apply(lambda x: season(*x), axis=1)

new = otcrdf['DISTURBANCE_ID'].str.split("_", expand=True)
otcrdf['ID'] = new[1]
otcrdf['IDSEAS'] = new[0].str[:6].str.strip('AU').astype(int)
# Calculate the number of unique values in each season:
otcrsc = otcrdf.groupby(['IDSEAS']).nunique()

# Determine the number of severe TCs. 
# take the number of TCs with maximum wind speed > 63 kts
# NOTE: The OTCR data uses knots, not metres/second!
otcrxc = otcrdf.groupby(['DISTURBANCE_ID',]).agg({
    'CENTRAL_PRES': np.min,
    'MAX_WIND_SPD': np.max,
    'ID':np.max, 'IDSEAS': 'max'})

otcrns = otcrxc[otcrxc['MAX_WIND_SPD'] > 63].groupby('IDSEAS').nunique()['ID']
idx = otcrsc.index >= 1980
idx2 = otcrsc.index >= 1985
nsidx = otcrns.index >= 1980
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.bar(otcrsc.index[idx], otcrsc.ID[idx], label="All TCs")
ax.bar(otcrns.index[nsidx], otcrns.values[nsidx], color='orange', label="Severe TCs")
ax.grid(True)
ax.set_yticks(np.arange(0, 21, 2))
ax.set_xlim(xlim)
ax.set_xlabel("Season")
ax.set_ylabel("Count")
ax.legend(fontsize='small')
plt.text(0.0, -0.1, "Source: http://www.bom.gov.au/cyclone/history/database/OTCR_alldata_final_external.csv",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "TC_frequency_otcr.png"), bbox_inches='tight')

# Add regression lines - one for all years >= 1970, another for all years >= 1985
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.bar(otcrsc.index[idx], otcrsc.ID[idx], label="All TCs")
ax.bar(otcrns.index[nsidx], otcrns.values[nsidx], color='orange', label="Severe TCs")
sns.regplot(x=otcrsc.index[idx], y=otcrsc.ID[idx], ax=ax, color='0.5', scatter=False, label='1970-2020 trend')
sns.regplot(x=otcrsc.index[idx2], y=otcrsc.ID[idx2], ax=ax, color='r', scatter=False, label='1985-2020 trend')
ax.grid(True)

ax.set_yticks(np.arange(0, 21, 2))
ax.set_xlim(xlim)
ax.set_xlabel("Season")
ax.set_ylabel("Count")
ax.legend(fontsize='small')
plt.text(0.0, -0.1, "Source: http://www.bom.gov.au/cyclone/history/database/OTCR_alldata_final_external.csv",
         transform=ax.transAxes, fontsize='x-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='x-small', ha='right')
plt.savefig(pjoin(outputPath, "TC_frequency_reg_otcr.png"), bbox_inches='tight')


otcrns.to_csv(pjoin(outputPath, "severe_tcs_otcr.csv"))
otcrsc.to_csv(pjoin(outputPath, "all_tcs_otcr.csv"))
