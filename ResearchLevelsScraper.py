#Copyright 2018 Farie82
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#Known issues:
#

import glob
import sys

class ResearchScraper:
    def __init__(self, fileSearchRoot, outputFile):
        self.fileSearchRoot=fileSearchRoot
        self.outputFile = outputFile
        self.research = {}
        self.names = {}
    
    def WriteOutput(self):
        with open(self.outputFile, mode='w') as output:
            for key, value in self.research.items():
                if value.valueSet and value.finalName != "":
                    output.write(self.FormatOutput(value)+"\n")

    def FormatOutput(self, item):
        return r"{{DA Item | name="+item.finalName+" | m="+item.materials+" | e="+item.engineering +" | pl="+item.plasma+" | pow="+item.power+" | bs="+item.blueSpace+" | bio="+item.biological+" | c="+item.combat+" | em="+item.electro+" | dt="+item.data+" | i="+item.illegal+r"}}"

    def Crawl(self):
        for filename in glob.iglob(self.fileSearchRoot+"/**/*.dm", recursive=True):
            self.ParseFile(filename)

    def ParseFile(self, fileName):
        try:
            with open(fileName, "r") as f:
                text = f.read()
                self.ParseText(text)
        except:
           print("File could not be read, filename = " + fileName)
    
    def ParseText(self, text):
        endIndex = 0
        startIndex = text.find("/obj/item/")
        while startIndex != -1:
            text = text[startIndex:]
            endIndex = text.find("\n/") #Get to the start of a new one
            part = text
            if endIndex!=-1:
                part = text[:endIndex]
            self.ParseItem(part)
            startIndex = text.find("/obj/item/", endIndex)

    def ParseItem(self, text):
        itemTypeEndIndex = text.find("\n")
        itemType = text[:itemTypeEndIndex]
        spaceIndex = itemType.find(" ")
        if spaceIndex != -1:
            itemType = itemType[:spaceIndex]
        if len(itemType) == 0  or not itemType[len(itemType)-1].isalpha() or itemType.find("/proc/") != -1 or itemType.find("(") != -1 or itemType.find(")") != -1:
            return
        
        nameIndex = text.find("\n\tname")
        item = ResearchItem()
        
        if nameIndex != -1:
            
            name = text[nameIndex+6:]
            name = name[:name.find("\n")].strip()[1:]
            
            res = name.split("\"") #See if it actually has a value behind it... fucking doesn't always
            if len(res)<2:
                return
            name = res[1]
            name = name.replace("\\improper ","") #fuck off with the \improper
            if len(name) > 0 and not name[len(name)-1].isalpha():
                return
            item.name = name
        
        item.itemType = itemType
        item.parent = itemType[:itemType.rfind("/")]
        originIndex = text.find("\n\torigin_tech")
        if originIndex != -1: #It has it defined in the item itself
            origin_tech = text[originIndex+13:] # remove the origin_tech part of the text
            
            origin_tech = origin_tech[:origin_tech.find("\n")].strip()[1:] # remove the whole text behind the line and strip it from whitespace
            
            if origin_tech.find("\"") != -1:
                res = origin_tech.split("\"") # remove the shit behind the value, comments for instance
                origin_tech = res[1]
                if origin_tech != "": # origin_tech = ""  fucking hell man
                    techs = origin_tech.split(";")
                    for t in techs:
                        item.set_value(t)
            else:
                if origin_tech.strip() == "null":
                    item.valueNull = True
        
        if (itemType in self.research and item.name == "" and self.research[itemType].name != "") or (item.name == "" and not item.valueSet): # /obj/item/organ/internal/liver/skrell is not put in the list for example since it's just 
            return
        
        if item.name != "":
            if name in self.names:
                self.names[name].append(itemType)
            else:
                self.names[name] = [itemType]
        self.research[itemType] = item

    def Finalize(self):
        keys = sorted(self.research.keys())
        for key in keys:
            item = self.research[key]
            if item.parent == "/obj/item/mecha_parts/part":
                item.parent = "/obj/item/mecha_parts/part/ripley_torso" #Don't ask why. Ask the para code
            item.parent = self.FindClosestParent(item.parent)
            if not item.valueSet and not item.valueNull:
                if item.parent != "":
                    par = self.research[item.parent]
                    item.materials = par.materials
                    item.engineering = par.engineering
                    item.plasma = par.plasma
                    item.power = par.power
                    item.blueSpace = par.blueSpace
                    item.biological = par.biological
                    item.combat = par.combat
                    item.electro = par.electro
                    item.data = par.data
                    item.illegal = par.illegal
                    item.abductor = par.abductor
                    item.valueSet = item.materials != "0" or item.engineering != "0" or item.plasma != "0" or item.power != "0" or item.blueSpace != "0" or item.biological != "0" or item.combat != "0" or item.electro != "0" or item.data != "0" or item.illegal != "0"
        
        names = self.names.keys()
        for n in names:
            
            ls = self.names[n]
            i = len(ls) -1
            while i>=0:
                if ls[i] in self.research:
                    if not self.research[ls[i]].valueSet or self.research[ls[i]].valueNull:
                        del self.names[n][i]
                i-=1
        
        for key in keys: #make sure all values are set before removing unneeded ones
            item = self.research[key]
            if item.name=="":
                if item.parent == "":
                    continue
                item.finalName = self.research[item.parent].name + "(" + item.itemType[item.itemType.rfind("/")+1:] + ")"
            else:
                if len(self.names[item.name]) > 1: #dupe names
                    item.finalName = item.name + "(" + item.itemType[item.itemType.rfind("/")+1:] + ")"
                else:
                    item.finalName = item.name

    def FindClosestParent(self, parent):
        if parent in self.research:
            return parent
        index = parent.rfind("/")
        if index==-1:
            return ""
        return self.FindClosestParent(parent[:index])

class ResearchItem:
    name=""
    finalName=""
    materials="0"
    engineering="0"
    plasma="0"
    power="0"
    blueSpace="0"
    biological="0"
    combat="0"
    electro="0"
    data="0"
    illegal="0"
    abductor="0"
    parent=""
    itemType=""
    valueSet = False
    valueNull = False
    def set_value(self, tech):
        self.valueSet = True
        vals = tech.split("=")
        if vals[0] == "materials":
            self.materials = vals[1]
            return
        if vals[0] == "engineering":
            self.engineering = vals[1]
            return
        if vals[0] == "plasmatech":
            self.plasma = vals[1]
            return
        if vals[0] == "powerstorage":
            self.power = vals[1]
            return
        if vals[0] == "bluespace":
            self.blueSpace = vals[1]
            return
        if vals[0] == "biotech":
            self.biological = vals[1]
            return
        if vals[0] == "combat":
            self.combat = vals[1]
            return
        if vals[0] == "magnets":
            self.electro = vals[1]
            return
        if vals[0] == "programming":
            self.data = vals[1]
            return
        if vals[0] == "syndicate":
            self.illegal = vals[1]
            return
        if vals[0] == "abductor":
            self.abductor = vals[1]
            return
root = ""
outputFile = ""
if len(sys.argv) > 1:
    root = sys.argv[1]
    if len(sys.argv) > 2:
        outputFile = sys.argv[2]
else:
    print("Fast usage from commandline: py ./ResearchLevelsScraper.py codeRoot outputFile")
    root = input("Root directory of the codebase? (C:/paradiseDirectory/code for example)")
    outputFile = input("Output file path? (C:/output.txt for example, defaults to output.txt)")

if outputFile == "":
    outputFile = "output.txt"
while root == "":
    root = input("Root directory of the codebase? (C:/paradiseDirectory/code for example) Can't be empty")

scraper = ResearchScraper(root, outputFile)
scraper.Crawl()
scraper.Finalize()
scraper.WriteOutput()