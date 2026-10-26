"""Centralized random-state handling. All stochastic code must get a Generator from here."""
import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(int(seed)))


def spawn(seed: int, n: int) -> list[np.random.Generator]:
    """Independent child streams, reproducible for a given seed."""
    ss = np.random.SeedSequence(int(seed))
    return [np.random.Generator(np.random.PCG64(s)) for s in ss.spawn(n)]
