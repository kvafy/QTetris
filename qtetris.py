#!/usr/bin/env python3
# -*- coding: utf-8 -*-


################################################################################
#                                                                              #
# Author: David Chaloupka                                                      #
# Name:   QTetris                                                              #
#                                                                              #
#                                                                              #
# Development start: 1.9.2009                                                  #
# Last modification: 4.9.2009                                                  #
#                                                                              #
# Requires: Python 3                                                           #
#           PyQt4                                                              #
#                                                                              #
################################################################################



import sys
import random
import re
import time # sleep
import threading # zámek Lock
from PyQt4 import QtCore, QtGui

import highscores





class QTetris(QtGui.QMainWindow):
    '''
    Centrální třída mající celý tetris na starosti. Spravuje level, rychlost hry a skóre.
    '''

    # základní rychlost levelu 1
    BASIC_SPEED = 500
    # zrychlený pád při stisku šipky dolů
    QUICKFALL_SPEED = 50

    speed = BASIC_SPEED
    score = 0

    # počítá kolikrát hráč skóroval a od toho odvíjí level (není důležité kolik
    # zboural řad, ale kolikrát se bourání podařilo)
    scoredCount = 0
    level = 1
    # kolikrát je třeba skórovat, než se postoupí na další level
    DESTRUCTIONS_TO_LEVEL_UP = 7

    # aktuální stav hry (nabývá hodnot POSSIBLE_STATES)
    state = "neaktivní"
    # regulérní výrazy povolených stavů self.state (řetězce nesmí obsahovat "|")
    POSSIBLE_STATES = ("neaktivní", "level \\d+", "pauza", "konec hry")



    def __init__(self, parent=None):
        # widgety v okně (labely, hrací plocha)
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle("QTetris")

        self.setWindowIcon(QtGui.QIcon("images/icon.png"))

        self.scoreLabel = QtGui.QLabel(self)
        self.newScore() # nastavení skóre na nulu

        self.stateLabel = QtGui.QLabel(self)
        self.setState("neaktivní")

        self.gameBoard = GameBoard(self, self)


        # rozvržení
        # rám obsahující veškerý obsah hlavního okna
        masterFrame = QtGui.QFrame()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.scoreLabel)
        hbox.addWidget(self.stateLabel)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.gameBoard)

        masterFrame.setLayout(vbox)

        self.setCentralWidget(masterFrame)


        # menu
        # Soubor -> Nová hra
        actionNewGame = QtGui.QAction("&Nová hra", self)
        actionNewGame.setShortcut("Ctrl+N")
        self.connect(actionNewGame, QtCore.SIGNAL("triggered()"), self.newGame)
        # Soubor -> Pauza
        actionPause = QtGui.QAction(QtGui.QStyle.standardIcon(self.style(), QtGui.QStyle.SP_MediaPause), "&Pauza", self)
        actionPause.setShortcut("P")
        self.connect(actionPause, QtCore.SIGNAL("triggered()"), self.flipPause)
        # Soubor -> Konec
        actionExit = QtGui.QAction(QtGui.QStyle.standardIcon(self.style(), QtGui.QStyle.SP_DialogCloseButton), "&Konec", self)
        actionExit.setShortcut("Ctrl+Q")
        self.connect(actionExit, QtCore.SIGNAL("triggered()"), QtCore.SLOT("close()"))

        # Ostatní -> Highscore
        actionHighscore = QtGui.QAction("&Highscore", self)
        self.connect(actionHighscore, QtCore.SIGNAL("triggered()"), self.showHighscores)
        # Ostatní -> O programu
        actionAbout = QtGui.QAction(QtGui.QStyle.standardIcon(self.style(), QtGui.QStyle.SP_MessageBoxInformation), "&O programu", self)
        self.connect(actionAbout, QtCore.SIGNAL("triggered()"), self.popupAuthorInfo)

        menubar = self.menuBar()
        menuFile = menubar.addMenu("&Soubor")
        menuFile.addAction(actionNewGame)
        menuFile.addAction(actionPause)
        menuFile.addSeparator()
        menuFile.addAction(actionExit)

        menuOther = menubar.addMenu("&Ostatní")
        menuOther.addAction(actionAbout)
        menuOther.addAction(actionHighscore)


        # signály od widgetu self.gameBoard
        self.connect(self.gameBoard, QtCore.SIGNAL("scored(int)"), self.scored)
        self.connect(self.gameBoard, QtCore.SIGNAL("gameOver()"), self.gameOver)
        self.connect(self.gameBoard, QtCore.SIGNAL("tetrominoeFell()"), self.setNormalSpeed)

        self.timer = QtCore.QBasicTimer()

        # NOTE: je třeba zavolat adjustZize, jinak bude self.size() dávat blbosti
        self.adjustSize()
        self.setFixedSize(self.size())


        # DATA
        self.highscores = highscores.Highscores(10)
        self.highscores.importData()

        self.reset()


    def center(self):
        '''
        Umístí hlavní okno na střed obrazovky.
        '''
        screen = QtGui.QDesktopWidget().screenGeometry()
        win = self.geometry()
        self.move((screen.width() - win.width()) // 2, (screen.height() - win.height()) // 2)


    def reset(self):
        '''
        Resetuje interní data, jako by byla hra právě spuštěna.
        '''
        self.timer.stop()
        self.score = 0
        self.scoredCount = 0
        self.level = 1
        self.speed = self.BASIC_SPEED
        self.gameBoard.clear()

        # zobrazení v GUI
        self.newScore()


    def getSpeed(self):
        return self.speed


    def newScore(self):
        self.scoreLabel.setText("skóre: %d" % self.score)


    def handleNewHighscore(self):
        '''
        Dosáhl-li hráč nového highscore, zeptá se jej na jméno a toto uloží.
        '''
        if self.score != 0 and self.highscores.isNewHighscore(self.score):
            playerName, ok = QtGui.QInputDialog.getText(self, "Nové highscore", "Vaše jméno:")
            if ok:
                self.highscores.addHighscore(playerName, self.score)


    def setState(self, state):
        '''
        Nastavuje obsah labelu informujícím o stavu.
        '''
        if not re.match("^(" + "|".join(self.POSSIBLE_STATES) + ")$", state):
        #if state not in self.POSSIBLE_STATES and not re.match("^level \\d+$", state):
            raise Exception("warning: state \"%s\" is unknown" % state)
        self.state = state
        self.stateLabel.setText("stav: %s" % self.state)


    def flipPause(self):
        '''
        Pause/unpause v závislosti na aktuálním stavu hry.
        '''
        if re.match("^level \\d+$", self.state):
            self.pause()
        elif self.state == "pauza":
            self.unpause()

    def pause(self):
        '''
        Dovoluje-li to aktuální stav, zapauzuje hru.
        '''
        if re.match("^level \\d+$", self.state):
            self.timer.stop()
            self.setState("pauza")

    def unpause(self):
        '''
        Dovoluje-li to aktuální stav, odpauzuje hru.
        '''
        if self.state == "pauza":
            self.timer.start(self.speed, self)
            self.setState("level %d" % self.level)


    def levelUp(self):
        self.level += 1
        self.setState("level %d" % self.level)
        self.speed = int(self.speed * 0.75) # bloky padají rychleji
        self.timer.start(self.speed, self)



    # SLOTY

    def scored(self, linesCount):
        # SLOT pro signál "scored(int)"
        # přidělené skóre se liší podle počtu zbouraných řad
        additionTable = (0, 100, 300, 500, 800)

        self.scoredCount += 1
        if self.scoredCount % self.DESTRUCTIONS_TO_LEVEL_UP == 0:
            self.levelUp()

        self.score += additionTable[linesCount] * self.level
        self.newScore()


    def showHighscores(self):
        self.pause()
        msgBox = QtGui.QMessageBox(self)
        msgBox.setWindowTitle("Dosažená skóre")
        msgBox.setText(str(self.highscores))
        # řetězec s highscores je úhledně formátovaný mezerami => nutné použití písma s pevnou šířkou znaků
        msgBox.setFont(QtGui.QFont("Courier New"))
        msgBox.show()


    def popupAuthorInfo(self):
        self.pause()
        title = "O QTetrisu"
        content = "Hra QTetris byla vytvořena v rámci samostudia pro seznámení se s PyQt4." \
                "\nOvládá se pomocí šipek, případně lze hru klávesou P zapauzovat." \
                "\n\nAutor: David Chaloupka\nCopyright (c) 2009" \
                "\n\n(mojí Martince :-*)"
        QtGui.QMessageBox.information(self, title, content)



    def newGame(self):
        # SLOT pro menu -> Soubor -> Nová hra
        self.reset()
        self.setState("level %d" % self.level)
        self.timer.start(self.speed, self)


    def gameOver(self):
        # SLOT pro signál "gameOver()"
        self.timer.stop()
        self.setState("konec hry")
        self.handleNewHighscore()

    def setNormalSpeed(self):
        # SLOT pro signál "tetrominoeFell()"
        self.timer.start(self.speed, self)


    # bindování kláves

    def quickFall(self):
        if self.QUICKFALL_SPEED < self.speed:
            self.timer.start(self.QUICKFALL_SPEED, self)


    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Left:
            self.gameBoard.move(-1, 0)
        elif event.key() == QtCore.Qt.Key_Right:
            self.gameBoard.move(1, 0)
        elif event.key() == QtCore.Qt.Key_Up:
            self.gameBoard.rotate()
        elif event.key() == QtCore.Qt.Key_Down:
            self.quickFall()
        else:
            QtGui.QWidget.keyPressEvent(self, event)


    # události

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():
            self.gameBoard.step()
        else:
            QtGui.QWidget.timerEvent(self, event)


    def closeEvent(self, event):
        self.timer.stop()
        self.highscores.exportData()
        event.accept()




#############################################################################




class GameBoard(QtGui.QFrame):
    '''
        Třída představuje hrací desku, na níž padají tetromina. Zajišťuje logickou i okenní část.
    O událostech hry posílá Qt signály, které jsou napojeny na metody třídy QTetris.
    Konkrétně generuje signály: "gameOver()", "scored(int)", "tetrominoeFell()".
        Asi nejdůležitější metodou je step(); tato je volána z QTetris na popud časovače
    a při každém zavolání se aplikace pokusí nechat tetromino spadnout o jedna dolů.
    Nepodaří-li se to (tetromino narazilo na dno), tak je umístěno, případně jsou smazány
    kompletní řádky. Vstup do metody step() je výlučný a je zajištěn zámkem stepLock.

    Geometrie herní desky je následující (geometrie okna má opačně kladný směr osy y):

  y ^
    |
    |
    +--------> x

    '''

    # Zámky zajišťující výlučný vstup do metod
    stepLock = threading.Lock() # metoda step
    moveLock = threading.Lock() # metody move, rotate

    # počet pixelů, kolik má hrana tetromina (~ rozměr barevného obrázku tetromina)
    TETROMINOE_RIM_SIZE = 22
    # vnitřní padding hrací plochy od okraje widgetu
    padding = 6
    # počet tetromin kolik se vejde do hrací pole na výšku/šířku
    GAMEBOARD_WIDTH = 10
    GAMEBOARD_HEIGHT = 19

    # Slovník obsahující stavy políček (čtverečků) na hrací ploše.
    # gameBoardArray[x][y] je jedna z hodnot třídy TetrominoeShape, tedy celé číslo,
    # jehož hodnota je zároveň indexem obrázku v proměnné blockImages.
    gameBoardArray = {}
    currentTetrominoe = None
    # pozice těžiště tetromina (jeho bodu s relativními souřadnicemi (0,0))
    currentPosition = QtCore.QPoint(0, 0)
    # obrázky bloků, které lze vykreslovat na hrací plochu
    blockImages = tuple(QtGui.QImage("images/block-" + name) for name in ("empty", "azure", "blue", "green", "purple", "red", "sand", "yellow", "flash1", "flash2") )



    def __init__(self, parent, qtetris):
        QtGui.QFrame.__init__(self, parent)

        self.qtetris = qtetris

        # DATA
        self.clear()


        # GUI
        # styl okraje
        self.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        self.setLineWidth(2)

        # pevná velikost hracího pole
        self.setFixedSize(self.TETROMINOE_RIM_SIZE * self.GAMEBOARD_WIDTH + 2*self.padding,
                self.TETROMINOE_RIM_SIZE * self.GAMEBOARD_HEIGHT + 2*self.padding)



    def clear(self):
        '''
        Připraví herní desku pro novou hru.
        '''
        # inicializace gameBoardArray
        for x in range(self.GAMEBOARD_WIDTH):
            self.gameBoardArray[x] = {}
            for y in range(self.GAMEBOARD_HEIGHT):
                self.gameBoardArray[x][y] = TetrominoeShape.NoShape

        self.currentTetrominoe = None

        self.repaint()


    def markFullLines(self):
        '''
        Políčka v plných řádcích přepíše hodnotou TetrominoeShape.Flash1 a vrátí
        počet celých řádků.
        '''
        ret = 0

        for y in range(self.GAMEBOARD_HEIGHT):
            for x in range(self.GAMEBOARD_WIDTH):
                if self.gameBoardArray[x][y] == TetrominoeShape.NoShape:
                    # tento řádek není celý => pokročíme na jinou hodnotu y
                    break
            else:
                ret += 1
                # na řádku nebylo nalezeno prázdné políčko => je celý zaplněn
                for x in range(self.GAMEBOARD_WIDTH):
                    self.gameBoardArray[x][y] = TetrominoeShape.Flash1
        if ret: self.repaint()
        return ret


    def flashFullLines(self):
        '''
        V gameBoadArray změní políčka s hodnou Flash1 na hodnotu Flash2 a opačně.
        '''
        needRepaint = False
        for x in range(self.GAMEBOARD_WIDTH):
            for y in range(self.GAMEBOARD_HEIGHT):
                if self.gameBoardArray[x][y] == TetrominoeShape.Flash1:
                    needRepaint = True
                    self.gameBoardArray[x][y] = TetrominoeShape.Flash2
                elif self.gameBoardArray[x][y] == TetrominoeShape.Flash2:
                    needRepaint = True
                    self.gameBoardArray[x][y] = TetrominoeShape.Flash1
        if needRepaint: self.repaint()


    def handleFullLines(self):
        linesCount = self.markFullLines()

        # nějaký řádek je plný => bude se bourat
        if linesCount != 0:
            # zablikání bouraných řádků
            # Odečítáme 15 milisekund, abychom se pokud možno vyhli tomu
            # že časovač z QTetris zavolá gameBoard.step() dřív než bude
            # ukončeno mazání celých řádků.
            stepTime = (self.qtetris.getSpeed() - 15) / 1000 # výpočet doby probliknutí
            # kolikrát políčka celých řádků přebliknou?
            flashCount = 3
            # TODO nízký stepTime způsobí chybu
            sleepInterval = stepTime / (flashCount + 1)

            # flashCount-krát problikneme políčka
            time.sleep(sleepInterval)
            for i in range(flashCount):
                self.flashFullLines()
                time.sleep(sleepInterval)


            # smazání bouraných řádků
            line = 0
            while line < self.GAMEBOARD_HEIGHT:
                # tento řádek je plný
                if self.gameBoardArray[0][line] in (TetrominoeShape.Flash1, TetrominoeShape.Flash2):
                    # všechny vyšší řádky posuneme o jedno dolů
                    for x in range(self.GAMEBOARD_WIDTH):
                        for y in range(line, self.GAMEBOARD_HEIGHT-1):
                            self.gameBoardArray[x][y] = self.gameBoardArray[x][y+1]
                    # vrchní řádek bude prázdný
                    for x in range(self.GAMEBOARD_WIDTH):
                        self.gameBoardArray[x][self.GAMEBOARD_HEIGHT - 1] = TetrominoeShape.NoShape
                else:
                    line += 1

            # připočtení skóre
            self.emit(QtCore.SIGNAL("scored(int)"), linesCount)

            self.repaint()



    def step(self):
        '''
        Metoda volaná při signálu časovače.
        '''

        # při mazání celých řádků se užívá time.sleep() => nebezpečí předčasného
        # spuštění časovače volajícího tuto metodu
        if self.stepLock.locked_lock():
            print("warning in GameBoard.step(self): step method called while self.stepLock was locked")
            return

        self.stepLock.acquire()

        # tetromino byl v předchozím kroku napevno umístěno => je třeba vygenerovat nové
        if not self.currentTetrominoe:
            self.currentTetrominoe = Tetrominoe()
            self.currentPosition = QtCore.QPoint(self.GAMEBOARD_WIDTH // 2, self.GAMEBOARD_HEIGHT-1)

            # kontrola, zda se nově vygenerované tetromino vůbec vejde na hrací plochu
            if not self.canPlaceTetrominoe(self.currentTetrominoe, self.currentPosition, removeCurrent=False):
                self.emit(QtCore.SIGNAL("gameOver()"))
                #return není třeba

            self.placeTetrominoe()
        # tetromino padá dolů
        else:
            self.fallTetrominoe()

        self.repaint()

        self.stepLock.release()


    def fallTetrominoe(self):
        '''
        Metoda je napojena na stisk šipky dolů pro zrychlení pádu.
        '''
        if not self.move(0, -1):
            # aktuální tetromino nemůže spadnout => napevno jeho bloky umístíme
            # a zajistíme, aby se vygenerovalo nové
            self.currentTetrominoe = None
            # kvůli změnně intervalu časově když se použilo zrychlený padání bloku
            self.emit(QtCore.SIGNAL("tetrominoeFell()"))
            self.handleFullLines()


    def move(self, relX, relY):
        '''
        Podaří-li se tetromino posunout, vrací True, jinak False.
        Metoda je napojena na stisky kláves.
        '''
        self.moveLock.acquire()

        if not self.currentTetrominoe:
            ret = False
        elif self.canPlaceTetrominoe(self.currentTetrominoe, self.currentPosition, relX, relY):
            # tetromino lze posunout => vymažeme, posuneme, umístíme na novou pozici
            self.removeTetrominoe()
            self.currentPosition.setX(self.currentPosition.x() + relX)
            self.currentPosition.setY(self.currentPosition.y() + relY)
            self.placeTetrominoe()
            self.repaint()
            ret = True
        else:

            ret = False

        self.moveLock.release()

        return ret


    def rotate(self):
        '''
        Metoda je napojena na stisk šipky nahoru pro otočení padající tetromina.
        '''
        self.moveLock.acquire()

        rotatedTetrominoe = Tetrominoe(self.currentTetrominoe)
        rotatedTetrominoe.rotate()

        if self.canPlaceTetrominoe(rotatedTetrominoe, self.currentPosition):
            self.removeTetrominoe()
            self.currentTetrominoe = rotatedTetrominoe
            self.placeTetrominoe()
            self.repaint()

        self.moveLock.release()


    def canPlaceTetrominoe(self, tetrominoe, qpoint, relX=0, relY=0, removeCurrent=True):
        '''
        Otestuje je-li možné tetrominoe umístit na hrací ploše na pozici
        qpoint s relativním posunutím (relX, relY). self.currentTetrominoe
        se přitom v závislosti na removeCurrent (ne)uvažuje jako překážka
        (removeCurrent=False se používá jen když se testuje zda je možné
        umístit nově vygenerované tetromino na hrací desku).
        Vrací True, je-li to možné, jinak False.
        '''
        ret = True

        if removeCurrent and self.currentTetrominoe:
            # vymažeme současné tetromino
            self.removeTetrominoe()

        try:
            for p in tetrominoe.points:
                # je políčko prázdné?
                if self.gameBoardArray[qpoint.x()+relX + p.x()][qpoint.y()+relY + p.y()] != TetrominoeShape.NoShape:
                    ret = False
                    break
        # vylezli jsme mimo hrací plochu
        except KeyError:
            ret = False

        if removeCurrent and self.currentTetrominoe:
            # obnovíme současné tetromino
            self.placeTetrominoe()

        return ret


    def removeTetrominoe(self):
        # tetromino nahradí prázdnými políčky
        baseX = self.currentPosition.x()
        baseY = self.currentPosition.y()

        for p in self.currentTetrominoe.points:
            self.gameBoardArray[baseX + p.x()][baseY + p.y()] = TetrominoeShape.NoShape


    def placeTetrominoe(self):
        baseX = self.currentPosition.x()
        baseY = self.currentPosition.y()

        for p in self.currentTetrominoe.points:
            self.gameBoardArray[baseX + p.x()][baseY + p.y()] = self.currentTetrominoe.shape


    def paintEvent(self, event):
        # aby se vykreslil rámeček atd.
        QtGui.QFrame.paintEvent(self, event)

        # vlastní kreslení situace na hracím poli
        painter = QtGui.QPainter(self)


        for x in range(self.GAMEBOARD_WIDTH):
            for y in range(self.GAMEBOARD_HEIGHT):
                self.paintBlock(painter, self.blockImages[ self.gameBoardArray[x][y] ], x, y)


    def paintBlock(self, painter, qimage, gridX, gridY):
        # vykreslí obrázek na zadané souřadnice mřížky
        painter.drawImage(self.padding + gridX * self.TETROMINOE_RIM_SIZE,
                self.height() - (self.padding + (gridY+1) * self.TETROMINOE_RIM_SIZE),
                qimage)



#############################################################################



class TetrominoeShape:
    NoShape = 0
    OShape = 1
    TShape = 2
    SShape = 3
    ZShape = 4
    LShape = 5
    JShape = 6
    IShape = 7
    count = 7
    Flash1 = 8
    Flash2 = 9



#############################################################################



class Tetrominoe(object):
    shape = None  # TetrominoeShape integer value
    points = None # tuple 4x QPoint

    # relativní polohy čtverečků tetromin; (0,0) je těžiště kolem
    # něhož se tetromino otáčí
    pointsTable = ((None),                             # NoShape
                   ((0,0), (1,0),   (0,-1),  (1,-1)),  # OShape
                   ((0,0), (-1,0),  (1,0),   (0,-1)),  # TShape
                   ((0,0), (-1,0),  (0,-1),  (1,-1)),  # ZShape
                   ((0,0), (1,0),   (0,-1),  (-1,-1)), # SShape
                   ((0,0), (-1,-1), (-1,0),  (1,0)),   # LShape
                   ((0,0), (-1,0),  (1,0),   (1, -1)), # JShape
                   ((0,0), (-1,0),  (1,0),   (2,0)),   # IShape
                   )


    def __init__(self, tetrominoe=None):
        '''
        Generuje tetromino náhodného tvaru.
        '''
        if not tetrominoe:
            self.shape = random.randint(1, TetrominoeShape.count)
            self.points = tuple(QtCore.QPoint(x, y) for x, y in self.pointsTable[self.shape])
        else:
            self.shape = tetrominoe.shape
            self.points = tetrominoe.points



    def rotate(self):
        '''
        Provádí rotaci tetromina okolo bodu (0,0) ve směru hodinových ručiček.
        '''
        if self.shape == TetrominoeShape.OShape:
            return

        newPoints = []
        for p in self.points:
            newPoints.append( QtCore.QPoint(p.y(), -p.x()) )
        self.points = tuple(newPoints)





#############################################################################


if __name__ == "__main__":

  sys.stdout = open("stdout.txt", "w")
  sys.stderr = open("stderr.txt", "w")


  app = QtGui.QApplication(sys.argv)

  qtetris = QTetris()
  qtetris.center()
  qtetris.show()

  ret = app.exec_()

  sys.stdout.close()
  sys.stderr.close()

  sys.exit(ret)
