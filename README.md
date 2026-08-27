ttwr 
====
[![Build Status](https://travis-ci.org/Brown-University-Library/ttwr.svg?branch=master)](https://travis-ci.org/Brown-University-Library/ttwr)

This is the django app that runs the Theater That Was Rome project website.

#### Install and Run

NOTE: These instructions are outdated and no longer work

- mkdir rome\_project
- cd rome\_project
- python3 -m venv env
- set environment variables in env/bin/activate and env/bin/activate_this.py
- git clone git@github.com:Brown-University-Library/ttwr.git (use https://github.com/Brown-University-Library/ttwr.git if you're not using SSH key)
- source env/bin/activate
- pip install --upgrade pip
- pip install -r ttwr/requirements.txt
- python run\_tests.py
- python manage.py migrate
- python manage.py collectstatic
- python manage.py runserver
