"""
A simple demo of accessing the WFS services to examine the data in the NHIRS
services and create a map of the data published through the service.

We access the NHIRS ACCESS-IM data, and plot the spatial extent of the ACCESS-C
domains. We retrieve the exposure report layer, and can access the attributes in
the layer via the columns of the `data` `GeoDtaFrame`.
"""

from owslib.wfs import WebFeatureService
import geopandas as gpd
from requests import Request
from datetime import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

url = "https://nhirs.ga.gov.au/geoserver/access/ows"
wfs = WebFeatureService(url=url)

layer = 'access:access_exposure_report'
params = dict(service='WFS',
              version='1.0.0',
              request='GetFeature',
              typeName=layer,
              outputFormat='json')
q = Request("GET", url, params=params).prepare().url
data = gpd.read_file(q)

figsize=(10, 8)
prj = ccrs.PlateCarree()
borders = cfeature.NaturalEarthFeature(
    category='cultural',
    name='admin_1_states_provinces_lines',
    scale='10m',
    facecolor='none')

fig, ax = plt.subplots(1, 1, figsize=figsize, subplot_kw={'projection':prj})

data.plot(ax=ax, facecolor="white", edgecolor='r', alpha=0.5, zorder=100)

for idx, row in data.iterrows():
    plt.annotate(text=row['event_id'], xy=row.geometry.centroid.coords[0],
                 ha='center', color='r', fontsize='small', zorder=1000)

ax.add_feature(cfeature.LAND, edgecolor=None)
ax.coastlines(resolution='10m')
ax.add_feature(borders, edgecolor='k', linewidth=0.5)
gl = ax.gridlines(draw_labels=True, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xformatter = LONGITUDE_FORMATTER
gl.yformatter = LATITUDE_FORMATTER
gl.xlabel_style = {'size': 'x-small'}
gl.ylabel_style = {'size': 'x-small'}

plt.text(-0.05, -0.1, f"Source: {url}",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.tight_layout()
plt.savefig("C:/outgoing/process/access/access_domains.png",
            bbox_inches='tight')
