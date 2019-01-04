import glob

class DMScraper:
    def __init__(self, fileSearchRoot, outputFile, itemStartPattern = "/obj/item/", itemEndPattern="\n/"):
        self.fileSearchRoot=fileSearchRoot
        self.outputFile = outputFile
        self.items = {}
        self.names = {}
        self.itemStartPattern = itemStartPattern
        self.itemEndPattern = itemEndPattern
    
    # WriteOutput 
    def WriteOutput(self, formatMethod, validateMethod = lambda x: True):
        
        with open(self.outputFile, mode='w') as output:
            for value in self.items.values():
                if value.valueSet and value.finalName != "" and validateMethod(value):
                    output.write(formatMethod(value)+"\n")
                    
    def Crawl(self, valuePatternsAndMethodTuples):
        for filename in glob.iglob(self.fileSearchRoot+"/**/*.dm", recursive=True):
            self.ParseFile(filename, valuePatternsAndMethodTuples)

    def ParseFile(self, fileName, valuePatternsAndMethodTuples):
        try:
            with open(fileName, "r") as f:
                text = f.read()
                self.ParseText(text, valuePatternsAndMethodTuples)
        except Exception as e:
           print("File could not be read, filename = {0}. With error: {1}".format(fileName, e))

    def ParseText(self, text, valuePatternsAndMethodTuples, patternStart = "", patternEnd = ""):
        if patternStart == "":
            patternStart = self.itemStartPattern
        if patternEnd == "":
            patternEnd = self.itemEndPattern
        endIndex = 0
        startIndex = text.find(patternStart)
        while startIndex != -1:
            text = text[startIndex:]
            endIndex = text.find(patternEnd) #Get to the start of a new one
            part = text
            if endIndex!=-1:
                part = text[:endIndex]
            self.ParseItem(part, valuePatternsAndMethodTuples)
            startIndex = text.find(patternStart, endIndex)

    def ParseItem(self, text, valuePatternsAndMethodTuples):
        itemTypeEndIndex = text.find("\n")
        itemType = text[:itemTypeEndIndex]
        commentIndex = itemType.find("//") # Single line comment
        if commentIndex == -1:
            commentIndex = itemType.find("/*") # Other type of comment
        if commentIndex != -1:
            itemType = itemType[:commentIndex] # Remove the comment from the type
        itemType = itemType.rstrip(" /\t") # Remove unneeded whitespace and /'s from the right side
        if len(itemType) == 0  or not itemType[len(itemType)-1].isalpha() or itemType.find("/proc/") != -1 or itemType.find("(") != -1 or itemType.find(")") != -1:
            return
        
        nameIndex = text.find("\n\tname")
        item = Item()
        item.itemType = itemType
        item.parent = itemType[:itemType.rfind("/")]
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
        for t in valuePatternsAndMethodTuples:
            pattern = t[0]
            matchIndex = text.find(pattern)
            if matchIndex != -1:
                value = ""
                temp1 = text[matchIndex + len(pattern):]
                while True: #Break to get out
                    endOfLineIndex = temp1.find("\n")
                    if endOfLineIndex != -1:
                        line = temp1[:endOfLineIndex]
                        temp = DMScraper.RemoveCommentsR(line) #Remove the comments and strip
                        
                        nextLineIndex = temp.find("\\")
                        if nextLineIndex == len(temp) - 1: # \ found to continue the value
                            value += temp[:nextLineIndex].strip()
                            temp1 = temp1[endOfLineIndex+1:].strip()
                        else:
                            value += temp
                            break
                    else:
                        value += temp1
                        break
                        
                value = value[1:].strip() #remove the = and whitespace
                
                item = t[1](item, value) # Expect the method to fill in the values if needed
        if (itemType in self.items and item.name == "" and self.items[itemType].name != "") or (item.name == "" and not item.valueSet): # /obj/item/organ/internal/liver/skrell is not put in the list for example since it's just 
            return
            
        if item.name != "":
            if name in self.names:
                self.names[name].append(itemType)
            else:
                self.names[name] = [itemType]
        self.items[itemType] = item
                        
    def Finalize(self):
        keys = sorted(self.items.keys())
        for key in keys:
            item = self.items[key]
            if item.parent == "/obj/item/mecha_parts/part":
                item.parent = "/obj/item/mecha_parts/part/ripley_torso" #Don't ask why. Ask the para code
            item.parent = self.FindClosestParent(item.parent)
            if not item.valueSet and not item.valueNull:
                if item.parent != "":
                    par = self.items[item.parent]
                    item.values = par.values
                    item.valueSet = len(item.values) > 0
        
        names = self.names.keys()
        for n in names:
            
            ls = self.names[n]
            i = len(ls) -1
            while i>=0:
                if ls[i] in self.items:
                    if not self.items[ls[i]].valueSet or self.items[ls[i]].valueNull:
                        del self.names[n][i]
                i-=1
        
        for key in keys: #make sure all values are set before removing unneeded ones
            item = self.items[key]
            if item.name=="":
                if item.parent == "":
                    continue
                item.finalName = self.items[item.parent].name + "(" + item.itemType[item.itemType.rfind("/")+1:] + ")"
            else:
                if len(self.names[item.name]) > 1: #dupe names
                    item.finalName = item.name + "(" + item.itemType[item.itemType.rfind("/")+1:] + ")"
                else:
                    item.finalName = item.name

    def FindClosestParent(self, parent):
        if parent in self.items:
            return parent
        index = parent.rfind("/")
        if index==-1:
            return ""
        return self.FindClosestParent(parent[:index])

    @staticmethod
    def RemoveCommentsR(text):
        return text.split("//")[0].split("/*")[0].strip() #Remove the comments and strip
    
class Item:
    def __init__(self):
        self.values = {} # Dictionary with the values possible
        self.name = "" # Used by other items if inherited without setting a name
        self.finalName = "" #After Finalise is called
        self.parent="" # Parent of the item
        self.itemType="" # Type of the item
        self.valueSet = False # If the value is set
        self.valueNull = False # If the value is null

    def set_value(self, valueType, value):
        self.values[valueType] = value
        self.valueSet = True
    
    def get_value(self, valueType, default):
        if valueType in self.values:
            return self.values[valueType]
        return default


