# app directory

This directory contains the Flask application code.

The code has been organized into the following sub-directories:

## commands
Contains cli_commands.py that has the scripts which can be run from the command line with flask <command_nam>. The environmnet varible FLASK_APP should point to this file

## databases
contains sql files for creating the various tables, main_database.py which is responsible for connecting to PostGresql and provides methods for interaction. user_models.py conatins the SQLAlchemy object for the user table

## modules
Contains individual folders which house each module

##ngs
Contains python modules for genomes,genes,tracks,thumbnails. Also view.py contains ways of inteacrting with viewsets i.e. list of genomic locations. project.py conatins GenericObject, from which all Project classes should inherit.

##static
Contains all the JavaScript,CSS and images

##templates
Contians the generic Jinja templates

## Zegami
Contains utility classes for interaction with Zegami

## jobs
Contains 3 files

**jobs.py** Contains the base classes BaseJob and LocalJob, which new Job clasees should extend from as well a generic jobs that are applicable to most projects

**celery_tasks** Only conatins two methods, one which runs project methods asynchronosly and the other which runs the process method of LocalJobs asynchronously

**email.py** Contains untility methods for sending emails

## main
Contains views.py which house the main view functions for rendering the HTML (Jinja) templates.

## meths
Contains the views which are the main api methods for communicating with the app. The main method in project_api, execute_project_action allows the remote execution of a project's method



