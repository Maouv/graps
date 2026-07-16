this document is issue included Issues that violate the plan/bugs/refactors

read [Experimental Graps Early plan](graps/plan/experimental-graps.md) its early plan that violated by ai and user 'maou' dont relaiz it.

### bug issue
bug found this time

## function/file klil behavior
1. when user klik function or file it didnt summon tabs on workspace like other IDE, its was mentioj in Experimemntak plan early but its bugging

## dir-panel and ai panel not resposifve and resizable
2. the panel didnt responsive and didnt resizable when i swipe left or right. it doesnt work like in the earlyer plan.


### violated the plan
violated earlyer plan

## tree structure file
the problem its to verbose 
cureent 
```
For example i use graps/cli.py for easy explaination

graps.cli   <- its path and its wrong
   cli.py   <- file
      _is_exculeded_file <- function

same but diffrent file

graps.ai.provider  <- path
   provider.py     <- file
      chat         <- function

its violated the plan cus the plan says tree structure like this (the right behavior)

graps/     <- folder
   ai/     <- folder
     __init__.py <- file
     cache.py
     provider.py
        chat <- function
     validator.py
   public/
   scanner/
   server/
   __init.py
   cli.py
   storage.py

thats the right person, its very diffrent right? now use full path not lazy load, its make it very verbose.

## layout

i tell you to read experimental plan ealry right, you must see current layout is wrong

current
```
+----------------------+--------------------------------------+----------------------------+
|    explorer          |                 untuk nmbh tab->  +  |         Ai                 |
|----------------------|--------------------------------------|----------------------------|
|                      |                                      | enricht                    |  <- we dont need this, also deleted parts ai enrichment on/off delete the green dot to
|                      |                                      |----------------------------|
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |  ------------------------  |
|                      |                                      |  | input bar             | |
|                      |                                      |  ------------------------  |
|                      |                                      |                            |
+----------------------+--------------------------------------+----------------------------+

```

earlyer plan says the layoyt like this
```
+----------------------+--------------------------------------+----------------------------+
|  make it empty first |          make it empty first         |                            | <- we miss this parts panel header
|                      |                                      | (-split-kiri) (split kanan)|  
+----------------------+--------------------------------------+----------------------------+
|    explorer          |                 untuk nmbh tab->  +  |         Ai                 |
|----------------------|--------------------------------------|----------------------------|
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|    dir-panel         |                                      |    kosongin                |
|                      |        Workspace                     |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |  ------------------------  |
|                      |                                      |  | input bar             | |
|                      |                                      |  ------------------------  |
|                      |                                      |                            |
+----------------------+--------------------------------------+----------------------------+

```

you can read the source code first to more understand whats mame like this

### missing split icon that i costum not from codeicons microsoft

the missing icon is split-horizontal-right-select.svg and unselect, the name descibe the beheavior, the one with selelct uts meean the icon is klik by the user same with unselect.

the function off icon its for open/close dir panel and ai panel.
the icon i give to you its only on represent right side its mean only for ai panel use not for dir panel use.
for the dir panel u can try to filp it horizontal to represent the opposite direction, after you flip it its make to left so ita represent dir panel in left side 

## colours in tree structure
now the file structure use pink fot path and green for function, its clear that violated the plan, plan says whatever the teks use what for hex code read read the early plan

### refactor

## icon refactor
even thought its refactor onlt refactor icon its veey important cus its still connected to violated plan tree structure file, you must done that first than to it this

i link the icon & fyi i clone the repo in your container its in /workspace/vscode-codeicons

[icon for folder](src/icons/folder.svg)
[icon for file](src/icons/file.svg)
for function use ƒ

## refactor frontend file
right now the frontend file its in public folder right? its bad for development maybe smart move if we put it in the new folder frontend/

## Note
your must planning it seqeuntall start with the high value planning it till its done, then next plan. your must be stick to the plan, dont improve. your must be very caution, balance rigor, very depth thinking, and balance candor. if you found and crucial issue regarding on this plan/early plan/your plan, starts asking the user its batter than think by yourself. if you find any deviation between source code and plan ask the user.


good luck!!!


