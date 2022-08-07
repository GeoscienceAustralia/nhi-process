import os
import pathlib
from os.path import join as pjoin
from prov.model import ProvDocument
from datetime import datetime
from prov.dot import prov_to_dot

DATEFMT = "%Y-%m-%d %H:%M:%S %Z"

prov = ProvDocument()
prov.set_default_namespace("")
prov.add_namespace('prov', 'http://www.w3.org/ns/prov#')
prov.add_namespace('foaf', 'http://xmlns.com/foaf/0.1/')
prov.add_namespace('void', 'http://vocab.deri.ie/void#')
prov.add_namespace('dcterms', 'http://purl.org/dc/terms/')
prov.add_namespace('gaprod', 'http://pid.geoscience.gov.au/dataset/ga/')
prov.add_namespace('ga', 'http://www.ga.gov.au')
prov.add_namespace('analysis', 'http://www.ga.gov.au')

sourcePath = "C:/WorkSpace/data/exposure"
analysisShpFile = pathlib.Path(pjoin(sourcePath, "LGA_wind_hazard_zones_vuln.shp"))
analysisXlsFile = pathlib.Path(pjoin(sourcePath, "LGA_wind_hazard_zones_vuln.xlsx"))
analysisJsonFile = pathlib.Path(pjoin(sourcePath, "LGA_wind_hazard_zones_vuln.json"))

analysisShpDateTime = datetime.fromtimestamp(analysisShpFile.stat().st_mtime).strftime(DATEFMT)
analysisXlsDateTime = datetime.fromtimestamp(analysisXlsFile.stat().st_mtime).strftime(DATEFMT)
analysisJsonDateTime = datetime.fromtimestamp(analysisJsonFile.stat().st_mtime).strftime(DATEFMT)

# Component products:
windzone = prov.entity('gaprod:127759',
                       {'prov:label':"AS1170.2 Wind loading regions shapefile",
                        'prov:type':'void:dataset',
                        'prov:url': 'http://pid.geoscience.gov.au/dataset/ga/127759',
                        'prov:generatedAtTime': '2015-06-19 00:00',
                        'dcterms:format':'ESRI shape file'
                       }
                      )

aeiplga = prov.entity('gaprod:135459',
                      {'prov:label':'AEIP LGA exposure information',
                       'prov:type':'void:dataset',
                       'prov:url': 'http://pid.geoscience.gov.au/dataset/ga/135459',
                       'prov:generatedAtTime': '2020-04-20 00:00',
                       'dcterms:format':'ESRI shape file'
                      }
                     )

tchahazard = prov.entity('gaprod:123412',
                         {'prov:label':'2018 National Tropical Cyclone Hazard Assessment',
                          'prov:type':'void:dataset',
                          'prov:url': 'http://pid.geoscience.gov.au/dataset/ga/123412',
                          'prov:generatedAtTime': '2018-10-31 00:00',
                          'dcterms:format':'GeoTIFF raster'
                         }
                        )

# Agents:
agent = prov.agent('ga:u12161',
                   {'prov:type':'prov:Person',
                    'foaf:givenName':'Craig Arthur',
                    'foaf:mbox': 'craig.arthur@ga.gov.au',
                   }
                  )

org = prov.agent('ga:GeoscienceAustralia',
                 {'prov:type':'prov:Organisation',
                  'foaf:name':'Geoscience Australia',
                  'foaf:mbox':'clientservices@ga.gov.au'
                 }
                )

# Products:
prod1 = prov.entity('gaprod:LGA_wind_zones_vuln.shp',
                    {'prov:label':'Tropical cyclone wind hazard zones and vulnerability',
                     'prov:type':'void:dataset',
                     'dcterms:format':'ESRI shape file'
                    }
                   )

prod2 = prov.entity('gaprod:LGA_wind_zones_vuln.xlsx',
                    {'prov:label':'Tropical cyclone wind hazard zones and vulnerability',
                     'prov:type':'void:dataset',
                     'dcterms:format':'Microsoft Office Excel Spreadsheet'
                    }
                   )

prod3 = prov.entity('gaprod:LGA_wind_zones_vuln.json',
                    {'prov:label':'Tropical cyclone wind hazard zones and vulnerability',
                     'prov:type':'void:dataset',
                     'dcterms:format':'GeoJSON'
                    }
                   )

analysis = prov.activity('analysis:Ranking',
                         analysisShpDateTime,
                         None,
                         {"dcterms:title": 'Wind hazard and vulnerability analysis',
                          "prov:type": "void:Analysis"}
                        )

zonal_stats = prov.activity('analysis:ZonalStats',
                            analysisShpDateTime,
                            None,
                            {'dcterms:title': "Zonal Statistics - 90th percentile",
                             'prov:type': "void:Analysis"})

vuln_calc = prov.activity('analysis:VulnerabilityCalculation',
                            analysisShpDateTime,
                            None,
                            {'dcterms:title':'Calculation of proportion of pre-1980s buildings',
                             'prov:type':'void:Analysis'
                            }
                           )
vuln_rating = prov.activity("analysis:VulnerabilityRating",
                            analysisShpDateTime,
                            None,
                            {'dcterms:title': "Rating of proportion of pre-1980s buildings",
                             'prov:type': 'void:Analysis',
                             'analysis':'Quantiles:5'}
                        )
conversion = prov.activity('analysis:Conversion',
                           analysisShpDateTime,
                           None,
                           {'dcterms:title':'Conversion from m/s to km/h',
                            'prov:type':'void:conversion'
                           }
                          )
hazard_rating = prov.activity("analysis:HazardRating",
                            analysisShpDateTime,
                            None,
                            {'dcterms:title': "Rating of hazard values",
                             'prov:type': 'void:Analysis',
                             'analysis':'Quantiles:5'}
                        )

spatialjoin = prov.activity('analysis:SpatialJoin',
                            analysisShpDateTime,
                            None,
                            {'dcterms:title':'Spatial join of wind zones and LGA boundaries',
                             'prov:type':'void:SpatialJoin'
                            }
                           )

prov.actedOnBehalfOf(agent, org)
prov.used(zonal_stats, aeiplga)
prov.used(zonal_stats, tchahazard)
prov.used(vuln_calc, aeiplga)
prov.used(vuln_rating, vuln_calc)

prov.used(conversion, zonal_stats)
prov.used(hazard_rating, conversion)
prov.used(analysis, hazard_rating)
prov.used(analysis, vuln_rating)
prov.used(spatialjoin, windzone)
prov.used(spatialjoin, analysis)

prov.wasGeneratedBy(prod1, spatialjoin, time=analysisShpDateTime)
prov.wasGeneratedBy(prod3, spatialjoin, time=analysisJsonDateTime)

prov.wasDerivedFrom(prod2, prod1)
prov.wasAttributedTo(analysis, agent)

dot = prov_to_dot(prov, direction='TB')
dot.write_png(pjoin(sourcePath, "LGA_wind_hazard_provenance.png"))

prov.serialize(pjoin(sourcePath, "LGA_wind_hazard_provenance.xml"), format='xml')
