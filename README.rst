.. role:: bash(code)
    :language: bash

.. role:: python(code)
    :language: python

Processing and analysis scripts for Natural Hazard Impacts
==========================================================

A collection of scripts for processing and analysing various datasets used
in the Natural Hazard Impacts section. Predominatly, these are for the
Atmospheric Hazards team.

Used in conjunction with the `nhi-pylib <https://github.com/GeoscienceAustralia/nhi-pylib>`_ codes.


Instructions
------------

Clone this repo to your local machine. I have previously installed this to a
_bin_ folder in a workspace folder, but can be anywhere as long as you have
write permissions::

    git clone https://github.com/GeoscienceAustralia/nhi-processing bin

Install the corresponding :bash:`nhi-pylib` repo::

    git clone https://github.com/GeoscienceAustralia/nhi-pylib lib

Add the :bash:`nhi-pylib` path to your :bash:`PYTHONPATH` user environment variable. This is done by going to the Windows Settings and searching for "Edit environment variables for your account". Add or edit the :bash:`PYTHONPATH` variable to include the location of the :bash:`nhi-pylib` directory. **Make sure to append :bash:`python` to the end of the path.** If you have installed the :bash:`nhi-pylib` repo at :bash:`C:\Users\uname\nhi-pylib`, the environment variable must be set to :bash:`C:\Users\uname\nhi-pylib\python`.

Create the conda environment from the :bash:`processenv.yml` file::

    cd bin
    conda env create -f processenv.yml

Activate the environment::

    conda activate process

For the scripts that use ArcGIS Pro Geoprocessing functions, there's a separate environment that you need to build (:bash:`arcgispro-py3`). By default, if a GA machine has ArcGIS Pro and Anaconda installed (via the Software Center), there will be an **arcgispro-py3** environment already available. You can use the :bash:`arcgispro-py3.yml` environment file to update the conda environment::

    conda activate arcgispro-py3
    conda env update --file arcgispro-py3.yml --prune

See `Updating an Environment <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html?highlight=prune#updating-an-environment>`_ for further details on updating an environment. This may not be everything, so take care the first time using this environment. The only place it's used at present (May 2023) is in the NHIRS fetch scripts, since they write to an ESRI Geodatabase. If you do encounter errors, please submit an issue with the missing packages listed.

The Windows batch scripts will activate the appropriate environment automatically when you run them.


What's inside
-------------

There's a mix of python scripts, Jupyter notebooks, Windows batch scripts (\*.cmd) and corresponding configuration files. Some of the scripts are intended to run on a continuous cycle (some of the TC fetch processes), others are intended for ad-hoc execution, others are just there to run an analysis whenever you feel the need. Some can be set up to automatically archive processed input files when done with them, others are purely for archiving files from one location to another (but in a semi-logical way).

The fetch scripts are typically "smart" - especially those that are intended to run continuously or repeatedly - in that they record the name, path, modification date and MD5 sum of the file in a simple text file when retrieved. Next time through the script will check if the details have changed and if they have not changed, no action is taken. All can be switched on and off in the relevant configuration file.

There's no test suite for this codebase. Errors may not be well handled. No guarantee that it will work out of the box. Use at your own risk.
