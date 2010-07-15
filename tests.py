"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

__test__ = {"doctest": """
>>> from cushion.models import Specimen
>>> d = {"genus": "Autographa", "species": "ampla", "latitude": "45.0", "longitude": 112.0}
>>> s = Specimen(**d)
>>> s["latitude"]
45.0
>>> d = {"genus": "Autographa", "species": "ampla", "latitude": "abc", "longitude": 112.0}
>>> try:
...     s = Specimen(**d)
... except ValueError:
...     print "ValueError"
...     
ValueError
>>>
"""}

