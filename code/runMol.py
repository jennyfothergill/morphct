from hoomd_script import *
import numpy as np
import modeler_hoomd as mh
import copy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
import helperFunctions
import sys
            

def getAAIDsByMolecule(CGtoAAIDs):
    moleculeAAIDs = []
    for moleculeID, CGtoAAIDDict in enumerate(CGtoAAIDs):
        moleculeAAIDs.append([])
        for dictionaryValue in CGtoAAIDs[moleculeID].values():
            moleculeAAIDs[-1] += dictionaryValue[1]
        moleculeAAIDs[-1].sort()
    return moleculeAAIDs


def getsScale(outputDir, morphologyName):
    morphologyFiles = os.listdir(outputDir+'/morphology')
    for fileName in morphologyFiles:
        if 'scaled' in fileName:
            scaledXMLName = fileName
            break
    underscoreLocs = helperFunctions.findIndex(scaledXMLName, '_')
    inverseScaleFactor = scaledXMLName[underscoreLocs[-2]+1:underscoreLocs[-1]]
    return float(inverseScaleFactor)


def execute(morphologyFile, AAfileName, inputCGMoleculeDict, inputAAMorphologyDict, CGtoAAIDs, boxSize):
    morphologyName = morphologyFile[helperFunctions.findIndex(morphologyFile,'/')[-1]+1:]
    outputDir = './outputFiles'
    morphologyList = os.listdir(outputDir)
    for allMorphologies in morphologyList:
        if morphologyName in allMorphologies:
            outputDir += '/'+morphologyName
            break
    fileList = os.listdir(outputDir+'/morphology')
    secondDirList = os.listdir(outputDir)
    if 'molecules' not in secondDirList:
        os.makedirs(outputDir+'/molecules')
    # GET sSCALE FROM SOMEWHERE ELSE RATHER THAN HARDCODING IT IN HERE!
    inverseSScale = getsScale(outputDir, morphologyName)
    
    slashList = helperFunctions.findIndex(AAfileName, '/')
    inputFileName = AAfileName[:slashList[-1]+1]+'relaxed_'+AAfileName[slashList[-1]+1:]
    print "Loading morphology data..."
    AAMorphologyDict = helperFunctions.loadMorphologyXML(inputFileName)

    # Unwrap positions
    AAMorphologyDict = helperFunctions.addUnwrappedPositions(AAMorphologyDict)

    moleculeAAIDs = getAAIDsByMolecule(CGtoAAIDs)

    for moleculeNo, AAIDs in enumerate(moleculeAAIDs):
    # moleculeNo = 63
    # AAIDs = moleculeAAIDs[63]
    # Now make the DFT input files
        atomIDOffset = -np.min(AAIDs)
        minimumIndex = np.min(AAIDs)
        maximumIndex = np.max(AAIDs)
        moleculeDictionary = {'position':[], 'type':[], 'bond':[]}
        for bond in AAMorphologyDict['bond']:
            # Can reduce the number of calculations by assuming that the fine-grainer always builds molecules sequentially so the atom IDs go from minimumIndex -> maximumIndex with no breaks
            if ((bond[1] >= minimumIndex) and (bond[1] <= maximumIndex)) or ((bond[2] >= minimumIndex) and (bond[2] <= maximumIndex)):
                moleculeDictionary['bond'].append([bond[0], bond[1]+atomIDOffset, bond[2]+atomIDOffset])
        molID = str(moleculeNo)
        while len(molID) < 3:
            molID = '0'+molID
        poscarName = outputDir+'/molecules/mol'+molID+'.POSCAR'
        nAtoms = 0
        for AAID in AAIDs:
            moleculeDictionary['position'].append(AAMorphologyDict['unwrapped_position'][AAID])
            moleculeDictionary['type'].append(AAMorphologyDict['type'][AAID])
            nAtoms += 1
        for key in ['lx', 'ly', 'lz']:
            moleculeDictionary[key] = AAMorphologyDict[key]
        moleculeDictionary['natoms'] = nAtoms
        moleculeDictionary = helperFunctions.addMasses(moleculeDictionary)
        moleculeCOM = helperFunctions.calcCOM(moleculeDictionary['position'], moleculeDictionary['mass'])
        moleculeDictionary = helperFunctions.centre(moleculeDictionary, moleculeCOM)
        moleculeDictionary = helperFunctions.scale(moleculeDictionary, inverseSScale)
        moleculeDictionary = helperFunctions.alignMolecule(moleculeDictionary, [0,1,0]) # Align along y-axis
        helperFunctions.writePOSCARFile(moleculeDictionary, poscarName)
    return morphologyFile, AAfileName, inputCGMoleculeDict, inputAAMorphologyDict, CGtoAAIDs, boxSize
    


if __name__ == '__main__':
    morphologyFile = sys.argv[1]
    morphologyName = morphologyFile[helperFunctions.findIndex(morphologyFile,'/')[-1]+1:]
    outputDir = './outputFiles'
    morphologyList = os.listdir(outputDir)
    for allMorphologies in morphologyList:
        if morphologyName in allMorphologies:
            outputDir += '/'+morphologyName
            break
    fileList = os.listdir(outputDir+'/morphology')
    pickleFound = False
    for fileName in fileList:
        if fileName == morphologyName+'.pickle':
            pickleLoc = outputDir+'/morphology/'+fileName
            pickleFound = True
    if pickleFound == False:
        print "Pickle file not found. Please run morphCT.py again to create the required HOOMD inputs."
        exit()
    print "Pickle found at", str(pickleLoc)+"."
    print "Loading atom data..."
    with open(pickleLoc, 'r') as pickleFile:
        (AAfileName, inputCGMoleculeDict, inputAAMorphologyDict, CGtoAAIDs, boxSize) = pickle.load(pickleFile)
    execute(morphologyFile, AAfileName, inputCGMoleculeDict, inputAAMorphologyDict, CGtoAAIDs, boxSize)
