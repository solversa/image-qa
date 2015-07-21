import os
USE_GPU = os.environ.get('GNUMPY_USE_GPU', 'yes') == 'yes'
VERBOSE = os.environ.get('VERBOSE', 'no') == 'yes'
if USE_GPU:
    import gnumpy as gnp
import numpy as np