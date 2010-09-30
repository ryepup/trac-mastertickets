#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
import os

from setuptools import setup

setup(
    name = 'TracMasterTickets',
    version = '3.0.2',
    packages = ['mastertickets'],
    package_data = { 'mastertickets': ['templates/*.html', 'htdocs/*.js', 'htdocs/*.css' ] },

    author = 'Noah Kantrowitz',
    author_email = 'noah@coderanger.net',
    description = 'Provides support for ticket dependencies and master tickets.',
    long_description = open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    license = 'BSD',
    keywords = 'trac plugin ticket dependencies master',
    url = 'http://github.com/coderanger/trac-mastertickets',
    classifiers = [
        'Framework :: Trac',
        #'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    
    install_requires = ['Trac>=0.12'],

    entry_points = {
        'trac.plugins': [
            'mastertickets.web_ui = mastertickets.web_ui',
            'mastertickets.api = mastertickets.api',
        ]
    }
)
