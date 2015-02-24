import copy
import time
from stage import *
from active_func import *

class RecurrentSubstage(Stage):
    def __init__(self, name,
                 inputsStr,
                 inputDim,
                 outputDim,
                 learningRate=0.0,
                 learningRateAnnealConst=0.0,
                 momentum=0.0,
                 deltaMomentum=0.0,
                 weightClip=0.0,
                 gradientClip=0.0,
                 weightRegConst=0.0,
                 outputdEdX=True):
        Stage.__init__(self,
                 name=name,
                 learningRate=learningRate,
                 learningRateAnnealConst=learningRateAnnealConst,
                 momentum=momentum,
                 deltaMomentum=deltaMomentum,
                 weightClip=weightClip,
                 gradientClip=gradientClip,
                 weightRegConst=weightRegConst,
                 outputdEdX=outputdEdX)
        self.inputs = None
        self.inputsStr = inputsStr # Before binding with actual objects
        self.inputDim = inputDim
        self.outputDim = outputDim
        self.dEdY = 0.0
        self.dEdX = 0.0
        self.splX = None
        self.splXsize = None
        self.N = 0
        self.X = 0
        self.Yall = None
        self.Xall = None
        self.exCount = 0
        pass

    def addInput(self, stage):
        if self.inputs is None:
            self.inputs = [stage]
        else:
            self.inputs.append(stage)

    def getInput(self):
        # fetch input from each input stage
        # concatenate input into one vector
        self.splX = []
        for stage in self.inputs:
            X = stage.Y
            self.splX.append(X)
        return np.concatenate(self.splX, axis=-1)

    def sendError(self):
        # iterate over input list and send dEdX
        s = 0
        for stage in self.inputs:
            s2 = s + stage.Y.size
            stage.dEdY += (self.dEdX[s : s2])
            s = s2

    def clearError(self):
        self.dEdY = 0.0

    def getOutputError(self):
        return self.dEdY

    def setDimension(self, N):
        self.N = N
        self.exCount = 0
        self.Yall = np.zeros((self.N, self.outputDim))
        self.Xall = np.zeros((self.N, self.inputDim))

    def saveVariable(self):
        self.Yall[self.exCount] = self.Y
        self.Xall[self.exCount] = self.X

    def retrieveVariable(self):
        self.Y = self.Yall[self.exCount]
        self.X = self.Xall[self.exCount]

    def graphForward(self):
        self.X = self.getInput()
        self.Y = self.forward(self.X)
        self.saveVariable()
        self.exCount += 1

    def graphBackward(self):
        if self.exCount == self.N:
            self.exCount = 0
        self.retrieveVariable()
        self.dEdX = self.backward(self.dEdY)
        self.sendError()
        self.exCount += 1

    def forward(self, X):
        """Subclasses need to implement this"""
        pass

    def backward(self, dEdY):
        """Subclasses need to implement this"""
        pass

    def updateWeights(self):
        """Update weights is prohibited here"""
        raise Exception('Weights update not allowed in recurrent substages.')
        pass

    def updateWeightsSync(self, dEdW):
        self._updateWeights(dEdW)

class Active_Recurrent(RecurrentSubstage):
    def __init__(self,
                 inputDim,
                 activeFn,
                 inputsStr,
                 outputdEdX=True,
                 name=None):
        RecurrentSubstage.__init__(self,
                 name=name,
                 inputsStr=inputsStr,
                 inputDim=inputDim,
                 outputDim=inputDim,
                 outputdEdX=outputdEdX)
        self.activeFn = activeFn
    def forward(self, X):
        self.Y = self.activeFn.forward(X)
        return self.Y
    def backward(self, dEdY):
        self.dEdW = 0
        return self.activeFn.backward(dEdY, self.Y, 0)

class Map_Recurrent(RecurrentSubstage):
    def __init__(self,
                 inputDim,
                 outputDim,
                 activeFn,
                 inputsStr,
                 initRange=1.0,
                 initSeed=2,
                 needInit=True,
                 initWeights=0,
                 learningRate=0.0,
                 learningRateAnnealConst=0.0,
                 momentum=0.0,
                 deltaMomentum=0.0,
                 weightClip=0.0,
                 gradientClip=0.0,
                 weightRegConst=0.0,
                 outputdEdX=True,
                 name=None):
        RecurrentSubstage.__init__(self,
                 name=name,
                 inputsStr=inputsStr,
                 inputDim=inputDim + 1,
                 outputDim=outputDim,
                 learningRate=learningRate,
                 learningRateAnnealConst=learningRateAnnealConst,
                 momentum=momentum,
                 deltaMomentum=deltaMomentum,
                 weightClip=weightClip,
                 gradientClip=gradientClip,
                 weightRegConst=weightRegConst,
                 outputdEdX=outputdEdX)
        self.activeFn = activeFn
        self.random = np.random.RandomState(initSeed)

        if needInit:
            self.W = self.random.uniform(
                -initRange/2.0, initRange/2.0, (outputDim, inputDim + 1))
        else:
            self.W = initWeights
        self.X = 0
        self.Y = 0
        self.Z = 0
        self.Zall = None
        self.dEdZ = None
        pass

    def forward(self, X):
        X2 = np.concatenate((X, np.ones(1)), axis=-1)
        Z = np.inner(X2, self.W)
        Y = self.activeFn.forward(Z)
        self.X = X2
        self.Z = Z
        self.Y = Y
        return Y

    def setDimension(self, N):
        RecurrentSubstage.setDimension(self, N)
        self.Zall = np.zeros((self.N, self.outputDim))

    def saveVariable(self):
        RecurrentSubstage.saveVariable(self)
        self.Zall[self.exCount] = self.Z

    def retrieveVariable(self):
        RecurrentSubstage.retrieveVariable(self)
        self.Z = self.Zall[self.exCount]

    def graphBackward(self):
        if self.dEdZ is None:
            self.dEdZ = np.zeros(self.Yall.shape)
        RecurrentSubstage.graphBackward(self)
        if self.exCount == self.N:
            self.dEdW = np.dot(self.dEdZ.transpose(), self.Xall)

    def backward(self, dEdY):
        dEdZ = self.activeFn.backward(dEdY, self.Y, self.Z)
        self.dEdZ[self.exCount] = dEdZ
        dEdX = np.dot(dEdZ, self.W[:, :-1])
        return dEdX if self.outputdEdX else None

class Input_Recurrent(RecurrentSubstage):
    def __init__(self, name, inputDim):
        RecurrentSubstage.__init__(self, name=name, inputsStr=[], inputDim=inputDim, outputDim=inputDim)

    def setValue(self, value):
        self.Y = value

    def getInput(self):
        return self.X

    def forward(self, X):
        return X

    def backward(self, dEdY):
        return dEdY

class Output_Recurrent(RecurrentSubstage):
    def __init__(self, name, outputDim):
        RecurrentSubstage.__init__(self, name=name, inputsStr=[], inputDim=outputDim, outputDim=outputDim)
    def forward(self, X):
        return X

    def backward(self, dEdY):
        return dEdY

class Zero_Recurrent(RecurrentSubstage):
    def __init__(self, name, inputDim):
        RecurrentSubstage.__init__(self, name=name, inputsStr=[], inputDim=inputDim, outputDim=inputDim)
        self.Y = np.zeros(self.outputDim)

class ComponentProduct_Recurrent(RecurrentSubstage):
    def __init__(self, name, inputsStr, outputDim):
        RecurrentSubstage.__init__(
            self,
            name=name,
            inputsStr=inputsStr,
            inputDim=outputDim * 2,
            outputDim=outputDim)
    def forward(self, X):
        self.X = X
        return X[:X.size/2] * X[X.size/2:]
    def backward(self, dEdY):
        self.dEdW = 0.0
        return np.concatenate((self.X[self.X.size/2:] * dEdY, self.X[:self.X.size/2] * dEdY))

class Sum_Recurrent(RecurrentSubstage):
    def __init__(self, name, inputsStr, numComponents, outputDim):
        RecurrentSubstage.__init__(
            self,
            name=name,
            inputsStr=inputsStr,
            inputDim=outputDim * numComponents,
            outputDim=outputDim)
        self.numComponents = numComponents
    def forward(self, X):
        return np.sum(X.reshape(self.numComponents, X.size/self.numComponents), axis=0)
    def backward(self, dEdY):
        self.dEdW = 0.0
        return np.tile(dEdY, 2)

class Recurrent(Stage):
    """
    Recurrent container.
    Propagate through time.
    """
    def __init__(self, stages, timespan, outputStageName, inputDim, outputDim, multiOutput=True, name=None, outputdEdX=True):
        Stage.__init__(self, name=name, outputdEdX=outputdEdX)
        self.stages = []
        self.stageDict = {}
        self.timespan = timespan
        self.multiOutput = multiOutput
        self.inputDim = inputDim
        self.outputDim = outputDim
        self.Xend = 0
        self.X = 0
        for t in range(timespan):
            self.stages.append([])
            inputStage = Input_Recurrent(name='input', inputDim=inputDim)
            self.stages[t].append(inputStage)
            self.stageDict[('input-%d' % t)] = inputStage
            for stage in stages:
                if t == 0:
                    stageNew = stage
                else:
                    stageNew = copy.copy(stage)
                self.stages[t].append(stageNew)
                self.stageDict[('%s-%d' % (stage.name, t))] = stageNew
            outputStage = Output_Recurrent(name='output', outputDim=outputDim)
            self.stages[t].append(outputStage)
            self.stageDict[('output-%d' % t)] = outputStage
            outputStage.addInput(self.stageDict[('%s-%d' % (outputStageName, t))])
        for t in range(timespan):
            for stage in self.stages[t]:
                for inputStageStr in stage.inputsStr:
                    stageName = inputStageStr[:inputStageStr.index('(')]
                    stageTime = int(
                        inputStageStr[inputStageStr.index('(') + 1 : inputStageStr.index(')')])
                    if stageTime > 0:
                        raise Exception('Recurrent model definition is non-causal')
                    # stageNameTime = '%s-%d' % (stageName, stageTime)
                    if t + stageTime < 0:
                        stageInput = Zero_Recurrent(
                            name=('%s-%d'%('zero',t)),
                            inputDim=self.stageDict[stageName + '-0'].outputDim)
                    else:
                        stageInput = self.stageDict[('%s-%d' % (stageName, t + stageTime))]
                    stage.addInput(stageInput)

    def forward(self, X):
        N = X.shape[0]
        self.Xend = np.zeros(N, dtype=int) + X.shape[1]
        reachedEnd = np.sum(X, axis=-1) == 0.0
        if self.multiOutput:
            Y = np.zeros((N, self.timespan, self.outputDim))
        else:
            Y = np.zeros((N, self.outputDim))
        for n in range(N):
            for t in range(X.shape[1]):
                if reachedEnd[n, t]:
                    self.Xend[n] = t
                    break
                self.stages[t][0].setValue(X[n, t, :])
                for s in range(1, len(self.stages[t])):
                    if n == 0:
                        self.stages[t][s].setDimension(N)
                    self.stages[t][s].graphForward()
                if self.multiOutput:
                    Y[n, t, :] = self.stages[t][-1].Y
            if not self.multiOutput:
                Y[n, :] = self.stages[self.Xend[n] - 1][-1].Y
        self.Y = Y
        self.X = X
        return Y

    def backward(self, dEdY):
        self.dEdW = []
        for i in range(len(self.stages[0])):
            self.dEdW.append(0.0)

        if self.outputdEdX:
            dEdX = np.zeros(self.X.shape)
        for n in range(self.X.shape[0]):
            if not self.multiOutput:
                self.stages[self.Xend[n] - 1][-1].dEdX = dEdY[n, :]
                self.stages[self.Xend[n] - 1][-1].sendError()
            for t in reversed(range(self.Xend[n])):
                if self.multiOutput:
                    self.stages[t][-1].dEdX = dEdY[n, t, :]
                    self.stages[t][-1].sendError()
                for s in reversed(range(1, len(self.stages[0]) - 1)):
                    self.stages[t][s].graphBackward()

            # Collect input error
            if self.outputdEdX:
                for t in range(self.Xend[n]):
                    dEdX[n, t] = self.stages[t][0].dEdY

            # Clear error and ready for next example
            for t in range(self.Xend[n]):
                for stage in self.stages[t]:
                    stage.dEdY = 0.0

        for s in range(1, len(self.stages[0]) - 1):
            if type(self.stages[0][s].W) is np.ndarray:
                tmp = np.zeros((self.timespan, self.stages[0][s].W.shape[0], self.stages[0][s].W.shape[1]))
                for t in range(self.timespan):
                    tmp[t] = self.stages[t][s].dEdW
                self.dEdW[s] = np.sum(tmp, axis=0)

        # For gradient check purpose, synchronize the sum of gradient to the time=0 stage
        for s in range(1, len(self.stages[0]) - 1):
            self.stages[0][s].dEdW = self.dEdW[s]
        return dEdX if self.outputdEdX else None

    def updateWeights(self):
        for stageName in self.stages[0].keys():
            if stageName != 'input' or 'output':
                # Because all stages are "shallow copied", the weights are shared.
                self.stages[0][stageName].updateWeightsSync(self.dEdW[stageName])

    def updateLearningParams(self, numEpoch):
        for stageName in self.stages[0].keys():
            if stageName != 'input' or 'output':
                # Since only the first stage updates the weights,
                # learning params just need to update in the first stage.
                self.stages[0][stageName].updateLearningParams()

    def getWeights(self):
        weights = []
        for stageName in self.stages[0].keys():
            weights.append(self.stages[0][stageName].getWeights())
        return np.array(weights, dtype=object)

    def loadWeights(self, W):
        i = 0
        for stageName in self.stages[0].keys():
            self.stages[0][stageName].loadWeights(W[i])
            i += 1

if __name__ == '__main__':
    pass