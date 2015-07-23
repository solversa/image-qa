from layer import *
import os
use_gpu = os.environ.get('GNUMPY_USE_GPU', 'yes') == 'yes'

class EmbeddingLayer(Layer):
    """
    Look-up table.
    WARNING: this implementation of LUT is index 1-based.
    0 will mean an all-zero entry.
    The first row of the weight matrix is one.
    """
    def __init__(self,
                 inputNames,
                 inputDim,
                 outputDim,
                 lazyInit=True,
                 initRange=1.0,
                 initSeed=2,
                 intConversion=False,
                 needInit=True,
                 initWeights=0,
                 sparse=False,
                 learningRate=0.0,
                 learningRateAnnealConst=0.0,
                 momentum=0.0,
                 deltaMomentum=0.0,
                 weightClip=0.0,
                 gradientClip=0.0,
                 weightRegConst=0.0,
                 outputdEdX=False,
                 name=None):
        Layer.__init__(self,
                 name=name,
                 inputNames=inputNames,
                 learningRate=learningRate,
                 outputDim=outputDim,
                 learningRateAnnealConst=learningRateAnnealConst,
                 momentum=momentum,
                 deltaMomentum=deltaMomentum,
                 weightClip=weightClip,
                 gradientClip=gradientClip,
                 weightRegConst=weightRegConst,
                 useGpu=False,
                 outputdEdX=outputdEdX)
        self.outputDim = outputDim
        self.inputDim = inputDim
        self.initRange = initRange
        self.random = np.random.RandomState(initSeed)
        self.needInit = needInit
        self.intConversion = intConversion

        # Zeroth rows of the weight matrix is reserved
        # for empty word at the end of a sentence.
        if needInit:
            if lazyInit:
                self.W = None
            else:
                self.initWeights()
        else:
            self.W = initWeights
            if USE_GPU and self.W.dtype != np.float32:
                self.W = self.W.astype('float32')
        self._inputValue = 0
        self._outputValue = 0
        self.sparse = sparse
        self.dEdW = 0.0

    def initWeights(self):
        self.W = self.random.uniform(
            -self.initRange/2.0, self.initRange/2.0,
            (self.inputDim, self.outputDim))
        if USE_GPU and self.W.dtype != np.float32:
            self.W = self.W.astype('float32')

    def forward(self, inputValue):
        if self.W is None: self.initWeights()
        if self.intConversion: inputValue = inputValue.astype(int)
        self._inputValue = inputValue
        inputValue = inputValue.reshape(inputValue.size)
        Y = np.zeros((inputValue.shape[0], self.outputDim), self.W.dtype)
        for n in range(0, inputValue.shape[0]):
            if self.sparse:
                if inputValue[n] != 0:
                    Y[n] = self.W[inputValue[n] - 1].todense()
            else:
                if inputValue[n] != 0:
                    Y[n] = self.W[inputValue[n] - 1]
        return Y

    def backward(self, gradientToOutput):
        X = self._inputValue
        if self.learningRate > 0.0:
            self.dEdW = np.zeros(self.W.shape, self.W.dtype)
            for n in range(0, X.shape[0]):
                self.dEdW[X[n] - 1] += gradientToOutput[n]
        if self.outputdEdX:
            return np.zeros(X.shape)
        else:
            return None

    def loadWeights(self, W):
        if self.learningRate == 0.0:
            return
        else:
            Layer.loadWeights(self, W)

    def getWeights(self):
        if self.learningRate == 0.0:
            return 0
        else:
            return self.W