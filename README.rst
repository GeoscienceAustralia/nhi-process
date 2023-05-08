Processing and analysis scripts for Natural Hazard Impacts
==========================================================

A collection of scripts for processing and analysing various datasets used
in the Natural Hazard Impacts section. Predominatly, these are for the
Atmospheric Hazards team.

Used in conjunction with the `nhi-pylib` codes.


Instructions
------------

Clone this repo to your local machine. I have previously installed this to a
`bin` folder in a workspace folder, but can be anywhere as long as you have
write permissions::

    git clone https://github.com/GeoscienceAustralia/nhi-processing bin

Install the corresponding `nhi-pylib` repo::

    git clone https://github.com/GeoscienceAustralia/nhi-pylib lib

Add the `nhi-pylib` path to your `PYTHONPATH` environment variable::

    set PYTHONPATH=C:\Workspace\lib\python

(I have the repos cloned to my `C:\Workspace` folder)

Create the conda environment from the `processenv.yml` file::

    conda env create -f processenv.yml

Activate the environment::

    conda activate process

