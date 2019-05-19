# satisfactory-save-checker
A simple python script for checking objects stored within Satisfactory save games.

Based on @bitowls and @S4XXX work with https://github.com/bitowl/satisfactory-save-format, so all the credits for the hard work goes to them, I've just added some check routines and removed json export. Oh, and renamed save2json which was the hardest part of all :laughing:

Usage is as simple as:
```
checksav.py <Name of save file>
```

Based on the outcome, you will either be presented:
```
NO errors found at all.
```
which is, as stated, perfect ... or some errors similar to
```
- Object pathName='Persistent_Level:PersistentLevel.Char_CaveStinger_Child_C_8'
        -> Invalid scale: 9.807989511238917e-38 | 9.807989511238917e-38 | 9.807989511238917e-38
- Object pathName='Persistent_Level:PersistentLevel.Char_CaveStinger_Child_C_5'
        -> Invalid scale: 9.807989511238917e-38 | 9.807989511238917e-38 | 9.807989511238917e-38
- Object pathName='Persistent_Level:PersistentLevel.Char_CaveStinger_Child_C_6'
        -> Invalid scale: 9.807989511238917e-38 | 9.807989511238917e-38 | 9.807989511238917e-38

Inspected a total of 90669 objects.
A total of 3 errors were found!
```
Use can then use your favourite save editor and just erase those using the pathName(s) given, or try to fix the issue(s).
I personally do prefer https://github.com/Goz3rr/SatisfactorySaveEditor for doing such.
