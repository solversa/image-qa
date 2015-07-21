from layer import *

class Sum(Layer):
    """Stage summing first half of the input with second half."""
    def __init__(self, name, inputNames, numComponents, outputDim,
                 defaultValue=0.0):
        Layer.__init__(
            self,
            name=name,
            inputNames=inputNames,
            outputDim=outputDim,
            defaultValue=defaultValue)
        self.numComponents = numComponents
    def forward(self, inputValue):
        return np.sum(
            inputValue.reshape(inputValue.shape[0],
                self.numComponents,
                inputValue.shape[1] / self.numComponents),
            axis=1)
    def backward(self, gradientToOutput):
        self.dEdW = 0.0
        return np.tile(gradientToOutput, self.numComponents)
