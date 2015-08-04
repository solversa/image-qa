import sys
import os

import h5py
import numpy as np
import nn

def extractWeightsVISBLSTM(modelSpecFile, weights, outFile):
    model = nn.load(modelSpecFile)
    model.deserializeWeights(weights)
    imgMapFirst = model.stageDict['imgMapFirst']
    imgMapLast = model.stageDict['imgMapLast']
    txtDict = model.stageDict['txtDict']
    lstmF = model.stageDict['lstmF']
    lstmB = model.stageDict['lstmB']
    softmax = model.stageDict['softmax'] \
        if model.stageDict.has_key('softmax') \
        else model.stageDict['answer']
    h5file = h5py.File(outFile, 'w')
    h5file['imgMapFirst'] = imgMapFirst.getWeights()
    h5file['imgMapLast'] = imgMapLast.getWeights()
    h5file['txtDict'] = txtDict.getWeights()
    h5file['lstmF'] = lstmF.getWeights()
    h5file['lstmB'] = lstmB.getWeights()
    h5file['softmax'] = softmax.getWeights()

if __name__ == '__main__':
    """
    Usage: python extract_wt.py 
                            -m[odel] {modelId}
                            -o[utput] {outFile}
                            [-r[esults] {resultsFolder}]
                            -t[ype] {VIS+BLSTM/}
    """
    resultsFolder = '../results'
    for i, flag in enumerate(sys.argv):
        if flag == '-m' or flag == '-model':
            modelId = sys.argv[i + 1]
        elif flag == '-o' or flag == '-output':
            outFile = sys.argv[i + 1]
        elif flag == '-r' or flag == '-results':
            resultsFolder = sys.argv[i + 1]
    modelWeightsFile = os.path.join(resultsFolder, 
        '%s/%s.w.npy' % (modelId, modelId))
    modelSpecFile = os.path.join(resultsFolder,
        '%s/%s.model.yml' % (modelId, modelId))
    weights = np.load(modelWeightsFile)
    extractWeightsVISBLSTM(modelSpecFile, weights, outFile)