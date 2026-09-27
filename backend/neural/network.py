"""Многослойный перцептрон с обратным распространением."""

import numpy as np
from .layers import Dense, relu, relu_grad, sigmoid


class MLP:
    """Сеть для классификации визуальных признаков."""

    def __init__(self, input_dim, hidden, output_dim, seed=7):
        h1, h2 = hidden
        self.fc1 = Dense(input_dim, h1, seed)
        self.fc2 = Dense(h1, h2, seed + 1)
        self.fc3 = Dense(h2, output_dim, seed + 2)

    def forward(self, x):
        if x.ndim == 1:
            x = x.reshape(1, -1)
        z1 = self.fc1.forward(x)
        a1 = relu(z1)
        z2 = self.fc2.forward(a1)
        a2 = relu(z2)
        logits = self.fc3.forward(a2)
        probs = sigmoid(logits)
        self._cache = (z1, a1, z2, a2)
        return probs

    def backward(self, x, y_true, lr=0.01):
        if x.ndim == 1:
            x = x.reshape(1, -1)
        probs = self.forward(x)
        grad = probs - y_true

        z1, a1, z2, a2 = self._cache
        grad = self.fc3.backward(grad)
        grad = grad * relu_grad(z2)
        grad = self.fc2.backward(grad)
        grad = grad * relu_grad(z1)
        self.fc1.backward(grad)

        for layer in (self.fc1, self.fc2, self.fc3):
            layer.W -= lr * layer.dW
            layer.b -= lr * layer.db

    def set_weights(self, w1, b1, w2, b2, w3, b3):
        self.fc1.W, self.fc1.b = w1.copy(), b1.copy()
        self.fc2.W, self.fc2.b = w2.copy(), b2.copy()
        self.fc3.W, self.fc3.b = w3.copy(), b3.copy()

    def predict(self, x):
        return self.forward(x)[0]
