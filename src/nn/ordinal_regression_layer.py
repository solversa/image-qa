from layer import *
import numpy as np


class OrdinalRegressionLayer(Layer):
    def __init__(
                    self, 
                    outputDim,
                    fixExtreme=True,
                    inputNames=None, 
                    name=None, 
                    outputdEdX=True,
                    learningRate=0.0,
                    learningRateAnnealConst=0.0,
                    momentum=0.0,
                    deltaMomentum=0.0,
                    weightClip=0.0,
                    gradientClip=0.0,
                    weightRegConst=0.0):
        Layer.__init__(
                        self, 
                        name=name,
                        inputNames=inputNames, 
                        outputDim=outputDim, 
                        outputdEdX=outputdEdX,
                        learningRate=learningRate,
                        learningRateAnnealConst=learningRateAnnealConst,
                        momentum=momentum,
                        deltaMomentum=deltaMomentum,
                        weightClip=weightClip,
                        gradientClip=gradientClip,
                        weightRegConst=weightRegConst)
        # Uniform initialization
        # mu_0 = -1
        # mu_(n-1) = 1
        # mu_i = -1 + 2 * (i / n)
        self.fixExtreme = fixExtreme
        mu = np.linspace(-1, 1, self.outputDim)
        # pi_i = 1/n
        pi = np.zeros(self.outputDim) + np.log(1 / float(self.outputDim))
        self.W = np.zeros((2, self.outputDim))
        self.W[0] = mu
        self.W[1] = pi

    def forward(self, inputValue):
        mu = self.W[0].reshape(1, self.W.shape[1])
        pi = self.W[1].reshape(1, self.W.shape[1])
        self.Xshape = inputValue.shape
        inputValue = inputValue.reshape(inputValue.shape[0], 1)
        self._inputValue = inputValue
        Z = np.exp(mu * inputValue + (pi - np.power(mu, 2) / 2))
        Y = Z / np.sum(Z, axis=-1).reshape(inputValue.shape[0], 1)
        self.Z = Z
        self._outputValue = Y
        return Y

    def backward(self, gradientToOutput):
        # Here we ignore the dEdY because this is always the last layer...
        target = gradientToOutput != 0.0
        targetInt = target.astype('int')
        targetIdx = np.nonzero(target)[1]
        mu = self.W[0]
        pi = self.W[1]
        dEdX = (-mu[targetIdx] + np.dot(self._outputValue, mu)) / float(self._inputValue.shape[0])
        dEdX = dEdX.reshape(self.Xshape)
        dEdMu = np.mean(
            (self._inputValue - mu) *
            (self._outputValue - targetInt), axis=0)
        # Fix extreme mu's
        if self.fixExtreme:
            dEdMu[0] = 0
            dEdMu[-1] = 0
        dEdPi = np.mean(self._outputValue - targetInt, axis=0)
        self.dEdW = np.zeros(self.W.shape)
        self.dEdW[0] = dEdMu
        self.dEdW[1] = dEdPi
        return dEdX

    def updateLearningParams(self, numEpoch):
        Layer.updateLearningParams(self, numEpoch)
        print 'mu:',
        for i in range(self.W.shape[-1]):
            print '%.3f' % self.W[0, i],
        print 'pi:',
        for i in range(self.W.shape[-1]):
            print '%.3f' % self.W[1, i],
        print

