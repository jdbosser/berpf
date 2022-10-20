
from berpf import BerParticleFilter, BerParticleFilterSettings
import numpy as np

def likelihood(
        particles: np.ndarray, 
        measurements: np.ndarray | None, 
        ) -> tuple[np.ndarray, np.ndarray]:
    N, p = particles.shape

    return (np.zeros(N), np.ones(N) )

def birth_model(
    measurements: np.ndarray | None, 
    Nbirth: int, 
    rng: np.random.Generator
) -> np.ndarray:
    return rng.standard_normal((Nbirth, 3))
    
def motion_model(particles: np.ndarray) -> np.ndarray:
    return particles

def test_call():
    assert isinstance(BerParticleFilter(
        likelihood_fn=likelihood, 
        birth_model =  birth_model, 
        motion_model=motion_model,
        Nsuv = 1000, 
        Nbirth=1000, 
        prob_birth=0.01, 
        prob_surv=0.99
    )(None), BerParticleFilter)
