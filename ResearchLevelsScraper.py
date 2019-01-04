import Scraper
import sys

def ParseResearchLevels(item, value):
    if value.find("\"") != -1:
        
        res = value.split("\"") # remove the shit behind the value, comments for instance
        value = res[1]
        if value != "": # origin_tech = ""  fucking hell man
            techs = value.split(";")
            for t in techs:
                vals = t.split("=") # Split on = sign
                item.set_value(vals[0],vals[1])
    else:
        if value == "null":
            item.valueNull = True
    return item

def FormatOutput(item):
    return r"{{DA Item | name="+item.finalName+" | m="+item.get_value("materials", "0")+" | e="+item.get_value("engineering", "0") +" | pl="+item.get_value("plasmatech", "0")+" | pow="+item.get_value("powerstorage", "0")+" | bs="+item.get_value("bluespace", "0")+" | bio="+item.get_value("biotech", "0")+" | c="+item.get_value("combat", "0")+" | em="+item.get_value("magnets", "0")+" | dt="+item.get_value("programming", "0")+" | i="+item.get_value("syndicate", "0")+r"}}"

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

scraper = Scraper.DMScraper(root,outputFile)
t = [("\n\torigin_tech", ParseResearchLevels)]
scraper.Crawl(t)
scraper.Finalize()
scraper.WriteOutput(FormatOutput)