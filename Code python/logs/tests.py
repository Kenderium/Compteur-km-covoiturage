'''
File: tests.py
Project: logs
Created Date: Mo Jan 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Mon Jan 17 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Mon Jan 17 2022   	By Julien Dagnelie & Loïc Tumelaire	Comments
----------	---	---------------------------------------------------------
'''

with open("logs.txt", "r") as file:

    r=0
    for i in range(len(file)):
        if r != 1:
            for elements in file[i]:
                pass
            for elements in file[i+1]:
                pass
            
            r += 1
        else:
            r = 0