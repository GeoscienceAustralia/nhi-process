library('climatol') # Most functions
source("C:/WorkSpace/climatol/R/depurdat.R") # Bug-fix for daily2climatol

sourcedir <- "X:/georisk/HaRIA_B_Wind/data/raw/from_bom/2019/Daily/"
outputdir <- "X:/georisk/HaRIA_B_Wind/data/derived/obs/daily_max_wind/climatol/"

stfile <- paste(sourcedir, "stations.txt", sep="")
stcol <- 1:6
datcol <- 3:6
varcli <- "wspd"
mindat <- 365
sep <- ","
na.strings <- "     "
header <- TRUE

setwd(outputdir)
cat("Preparing data\n")
#daily2climatol(stfile, stcol=1:6, datcol=3:6, varcli, anyi=NA, anyf=NA,
#               mindat=365, sep=sep, dec='.', na.strings=na.strings,
#               header=header)

cat("Starting the homogenisation process\n")
homogen(varcli, 1939, 2019, std = 2, ini='1939-04-01', dz.max = 20)
