
# -*- coding: utf-8 -*-


################################################################################
#                                                                              #
# Author: David Chaloupka                                                      #
# Name:   Highscores                                                           #
#                                                                              #
#                                                                              #
# Development start: 2.9.2009                                                  #
# Last modification: 4.9.2009                                                  #
#                                                                              #
# Requires: Python 3.1                                                         #
#                                                                              #
#                                                                              #
# Desription:                                                                  #
# ----------                                                                   #
# Třída pro uchovávání highscores ve hrách. Záznamy si interně ukládá do       #
# self.records jako uspořádané dvojice (hráč, skóre). Na disk je pak uládá     #
# ve formě xml dokumentu. Jako šifrování je momentálně užit jednoduchý převod  #
# xml do base64. Pro změnu šifrování stačí přepsat metody cypher, decypher.    #
#                                                                              #
################################################################################




import xml.dom.minidom
import base64




class Highscores(object):
    MAX_NAME_LENGTH = 10

    def __init__(self, maxRecords):
        # maximální počet pozic v žebříčku highscores
        self.maxRecords = maxRecords
        # záznamy ve tvaru dvojic (jméno, skóre)
        self.records = []

    
    def _decypher(self, s):
        '''
        Přijímá byty a vrací jejich dešifrovanou podobu ve formě stringu.
        '''
        return base64.b64decode(s)


    def _cypher(self, s):
        '''
        Přijímá string a vrací jeho zašifrovanou podobu ve formě bytů.
        '''
        return base64.b64encode(s)


    def importData(self, fileName="highscores.txt"):
        file = None
        try:
            file = open(fileName, "rb")
            doc = xml.dom.minidom.parseString(self._decypher(file.read()))
            recordNodes = doc.getElementsByTagName("item")

            for node in recordNodes:
                name = node.getAttribute("playerName")
                score = int(node.getAttribute("score"))
                self.addHighscore(name, score)

        except IOError:
            # soubor je otevřený ale nemůže se číst
            if file:
                print("highscores.py: can't read input xml file \"%s\"" % fileName)
                self.records = []
            # jinak soubor neexistuje, což je korektní možnost (nebyl dosud vytvořen)
        except Exception:
            print("highscores.py: input xml file \"%s\" is inconsistent" % fileName)
        finally:
            if file: file.close()


    def exportData(self, fileName="highscores.txt"):
        # vytvoření xml
        doc = xml.dom.minidom.Document()

        rootElement = doc.createElement("highscores")
        doc.appendChild(rootElement)

        for name,score in self.records:
            item = doc.createElement("item")
            # uložení dat do uzlu
            item.setAttribute("playerName", name)
            item.setAttribute("score", str(score))

            rootElement.appendChild(item)
        
        file = None
        try:
            # zápis xml do souboru
            file = open(fileName, "wb")
            file.write(self._cypher(doc.toprettyxml(indent="", newl="\n", encoding="utf-8")))
            #doc.writexml(file, indent="", addindent="   ", newl="\n", encoding="utf-8")
        except IOError:
            print("highscores.py: can't write xml to file \"%s\"" % fileName)
        finally:
            if file: file.close()


    def __str__(self):
        '''
        Vrací highscores v úhledné podobě formátované. Jména jsou zarovnána nalevo,
        highscores napravo. Doplňuje potřebný minimální počet mezer.
        Př:
        1. ek            13,460
        2. dlouhé jméno   8,320
        3. poslední         111
        '''
        ret = ""

        longestRec = self._longestRecord()
        formatName = "<" + str(self.MAX_NAME_LENGTH) + "s"
        formatScore = ">" + str(longestRec[1]) + ",d"
        
        i = 1
        for name,score in self.records:
            if ret: ret += "\n"
            ret += format(i, ">2d") + ". " + format(name, formatName) + "  " + format(score, formatScore)
            i += 1
        return ret


    def _longestRecord(self):
        '''
        Vrátí nejdelší textovou reprezentaci jména a skóre, které jsou aktuálně
        uloženy jako tuple (nameLen, scoreLen). Metoda je použávána pro __str__(self).
        '''
        nameLen = 0
        scoreLen = 0

        for name, score in self.records:
            if len(name) > nameLen: nameLen = len(name)
            if len(format(score, ",d")) > scoreLen: scoreLen = len(format(score, ",d"))
        return (nameLen, scoreLen)


    def _cmpByScore(record):
        # porovnávací funkce záznamů podle jejich skóre
        return record[1]

    
    def isNewHighscore(self, candidateScore):
        '''
        Rozhoduje, zda je dané "candidateScore" dostatečně veliké na to, aby bylo
        přidáno do žebříčku. Jestli ano, vrací True, jinak False.
        '''
        if len(self.records) < self.maxRecords:
            return True

        for name,score in self.records:
            if score < candidateScore:
                return True
        return False


    def addHighscore(self, playerName, score):        
        # ořízneme jméno na maximální povolenou délku
        playerName = playerName[:self.MAX_NAME_LENGTH]
        # přidáme záznam
        self.records.append((playerName, score))
        # záznamy seřadíme sestupně podle skóre
        self.records.sort(key=Highscores._cmpByScore, reverse=True)
        # přebytečné záznamy ořízneme
        self.records = self.records[:self.maxRecords]


