from dataclasses import dataclass
from typing import TypeVar, Protocol, Callable, Optional, runtime_checkable, Any
import numpy as np

State = TypeVar("State")

Particles = np.ndarray
Measurements = np.ndarray



def _logsumexp(x: np.ndarray) -> np.ndarray:

    c = np.max(x)
    return c + np.log(np.sum(np.exp(x - c)))


def _weight_update(LogLt:               np.ndarray, 
                   weight_predictions:  np.ndarray) -> np.ndarray:

    # This function calculates
    # wp = Lt * wp
    # wp = wp ./ sum(wp)

    # Sometimes, I have a zero predicted weight. Need to take care of this

    non_zero = np.nonzero(weight_predictions)
    
    y = LogLt[non_zero]
    logw = np.log(weight_predictions[non_zero])
    x = y + logw
    wp = np.zeros(len(weight_predictions))
    wp[non_zero] = np.exp(x - _logsumexp(x))
    return wp

def _weight_update_prime(LogLt: np.ndarray, 
                         weight_predictions: np.ndarray) -> np.ndarray:

    # Modify LogLt so that we can go to linear domain

    c = np.max(LogLt)
    Lt = np.exp(LogLt - c)

    wn = weight_predictions * Lt
    wn = wn / np.sum(wn)

    return wn

def _update_existance_prob_linear_domain(weight_predictions: np.ndarray,
                                         LogRatio: np.ndarray, 
                                         prob_prediction: float) -> float:

    Ratio = np.exp(LogRatio)
    I = np.sum(weight_predictions * Ratio)
    if np.isfinite(I):
        q = I * prob_prediction / (1 - prob_prediction + prob_prediction * I)
        return q
    else: 
        return 1.0


def _update_existance_prob(weight_predictions:  np.ndarray,
                           LogRatio:            np.ndarray,
                           prob_prediction:     float) -> float:

    # Approximate integral (eq. 83)
    # I=wp*Ratio_Lt2Lnt;

    # Update existence probability
    # q=I*qp/((1-qp)+qp*I);
    

    # Sometimes, I have a zero predicted weight. Need to take care of this
    
    non_zero = np.nonzero(weight_predictions)


    wp = weight_predictions[non_zero]
    y = LogRatio[non_zero]

    x1 = y + np.log(wp)
    x2 = y + np.log(prob_prediction) + np.log(wp)
    x2 = np.insert(x2, 0, np.log(1 - prob_prediction))
    
    logq = _logsumexp(x1) + np.log(prob_prediction) - _logsumexp(x2)
    
    q = np.exp(logq)
    
    # Note, numerical errors may cause q to be greater than 1

    return np.min([q, 1])





def _sysresample(weights:   np.ndarray, 
                 Nsuv:      int, 
                 rng:       np.random.Generator) -> np.ndarray:
        
    # Cannot take more particles than all of them
    N = min(len(weights), Nsuv)

    if np.any(np.isnan(weights)):
        return rng.choice(len(weights), N)

    positions = (rng.random() + np.arange(N)) / N
    indices = np.zeros(N, int)

    cumsum = np.cumsum(weights)

    i,j = 0, 0

    while i < N:
        if positions[i] < cumsum[j]:
            indices[i] = j
            i = i + 1
        else:
            j = j + 1

    return indices
        




@runtime_checkable
class BerParticleFilterSettingsProtocol(Protocol):

    
    rng:            np.random.Generator

    Nsuv:           int 
    Nbirth:         int
    prob_birth:     float
    prob_surv:      float
    
    likelihood_fn: Callable[[Particles, Optional[Measurements]], tuple[np.ndarray, np.ndarray]]

    @property
    def birth_model(self) -> Callable[[Optional[Measurements], int, np.random.Generator], Particles]:
        ...

    @property
    def motion_model(self) -> Callable[[Particles], Particles]: 
        ...


@dataclass
class BerParticleFilterSettings:

    likelihood_fn : Callable[[Particles, Optional[Measurements]], tuple[np.ndarray, np.ndarray]]
    birth_model: Callable[[Optional[Measurements], int, np.random.Generator], Particles]
    motion_model: Callable[[Particles], Particles]
    Nsuv:           int 
    Nbirth:         int
    prob_birth:     float
    prob_surv:      float
    
    rng:            np.random.Generator = np.random.default_rng()


Likelihood = Callable[[Particles, Optional[Measurements]], tuple[np.ndarray, np.ndarray]]
BirthModel = Callable[[Optional[Measurements], int, np.random.Generator], Particles]
MotionModel = Callable[[Particles], Particles]


@dataclass
class BerParticleFilter:

    likelihood_fn : Likelihood
    birth_model: BirthModel
    motion_model: MotionModel

    Nsuv:           int 
    Nbirth:         int
    prob_birth:     float
    prob_surv:      float

    prob:       float
                 
    particles_surv: np.ndarray
    weights_surv:   np.ndarray
 
    particles_born: np.ndarray
    weights_born:   np.ndarray
    N_eff:          float = np.nan
    N_eff_surv:     float = np.nan
    N_eff_surv_normalized: float = np.nan
    N_eff_born:     float = np.nan
    N_eff_born_normalized: float = np.nan
    rng:            np.random.Generator = np.random.default_rng()
    
    
    @property
    def mean(self) -> np.ndarray:
        
        assert self.weights_born is not None and self.weights_born is not None 

        if len(self.weights_surv) > 0:
            return (self.weights_surv @ self.particles_surv)

        elif len(self.weights_born) > 0:

            return (self.weights_born @ self.particles_born)

        else:

            raise Exception("No particles or weights")

    @property
    def covar(self) -> np.ndarray:
        
        mean = self.mean
        d = np.subtract(self.particles_surv, mean)
        
        return np.einsum("i,id,ic->dc", self.weights_surv, d, d)

    @property 
    def maxap(self) -> np.ndarray:
        
        i = np.argmax(self.weights_surv)
        return self.particles_surv[i]
    
    
    def __init__(self, 
                    Nsuv:           int ,
                    Nbirth:         int,
                    prob_birth:     float,
                    prob_surv:      float,
                    likelihood_fn : Likelihood,
                    birth_model: BirthModel,
                    motion_model: MotionModel,
                    prob: float = 0, 
                    particles_born: np.ndarray | None = None, 
                    weights_born: np.ndarray | None = None,
                    particles_surv: np.ndarray | None = None,
                    weights_surv: np.ndarray | None = None, 
                    N_eff : float = np.nan, 
                    N_eff_surv : float = np.nan,
                    N_eff_surv_normalized : float = np.nan, 
                    N_eff_born: float = np.nan , 
                    N_eff_born_normalized : float = np.nan,
                    rng: np.random.Generator = np.random.default_rng(),
                    ) -> None:

        self.prob = prob

        if particles_born is None: 
            self.particles_born = birth_model(None, Nbirth, rng)
        else: 
            self.particles_born = particles_born
        


        if weights_born is None: 
            self.weights_born = 1/Nbirth * np.ones(Nbirth)
        else: 
            self.weights_born = weights_born

        if particles_surv is None:
            self.particles_surv = np.empty((0, self.particles_born.shape[1]))
        else: 
            self.particles_surv = particles_surv

        if weights_surv is None: 
            self.weights_surv = np.empty(0)
        else: 
            self.weights_surv = weights_surv

        self.Nsuv = Nsuv
        self.Nbirth = Nbirth
        self.prob_birth = prob_birth
        self.prob_surv = prob_surv
        self.likelihood_fn = likelihood_fn
        self.birth_model = birth_model
        self.motion_model = motion_model
        self.N_eff = N_eff
        self.N_eff_surv = N_eff_surv  
        self.N_eff_surv_normalized = N_eff_surv_normalized  
        self.N_eff_born = N_eff_born  
        self.N_eff_born_normalized = N_eff_born_normalized  
        self.rng = rng


    def __call__(self, measurements: Optional[np.ndarray]) -> 'BerParticleFilter':

        q = self.prob
        w_s = self.weights_surv
        w_b = self.weights_born


        prob_surv   = self.prob_surv
        prob_birth  = self.prob_birth
        Nsuv        = self.Nsuv
        Nbirth      = self.Nbirth
        
        motion_model    = self.motion_model
        birth_model     = self.birth_model 
        likelihood_fn   = self.likelihood_fn
    

        Ntot = Nsuv + Nbirth
        Nborn = Ntot - len(self.particles_surv)
        
        particles = np.concatenate((np.atleast_2d(self.particles_surv), self.particles_born))
        particles_p = motion_model(particles)


        q_p = prob_birth * (1-q) + prob_surv * q
        weights_p   = np.concatenate((
            prob_surv * q/q_p * self.weights_surv,
            prob_birth * (1 - q)/q_p * self.weights_born 
        ))
        weights_p = weights_p / np.sum(weights_p)
        
        LogLt, LogRatio = likelihood_fn(particles_p, measurements)

        # q = _update_existance_prob_linear_domain(weights_p, LogRatio, q_p)
        q = _update_existance_prob(weights_p, LogRatio, q_p)
        # w = _weight_update_prime(LogLt, weights_p)
        w = _weight_update(LogLt, weights_p)
        
        # Numerical errors can cause this to be larger than 1. Fix
        # by extra normalization
        w = w / np.sum(w)

        # calculate the effective number number of samples
        N_eff = 1/np.sum(w**2)

        N_eff_surv = np.nan
        N_eff_surv_normalized = np.nan
        Nsurv = len(self.particles_surv)

        # Partial weight updates, to find the effective number of samples of 
        # a subset of the particles


        if Nsurv:
            N_eff_surv = 1/np.sum(w[0:Nsurv]**2)
            N_eff_surv_normalized = 1/np.sum(
                (w[0:Nsurv]/np.sum(w[0:Nsurv]))**2
            )
        N_eff_born = 1/np.sum(w[Nsurv:]**2)
        N_eff_born_normalized = 1/np.sum(
            (w[Nsurv:]/np.sum(w[Nsurv:]))**2
        )


        indices_surv_particles = _sysresample(w, Nsuv, self.rng)
        particles_surv = particles_p[indices_surv_particles]

        # Reset the weights
        w_surv = np.ones(Nsuv)/Nsuv

        # Find some newborn particles
        particles_born = birth_model(measurements, Nbirth, self.rng)

        # Set the weights for the newborn particles
        w_born = np.ones(Nbirth)/Nbirth 

        return self.override(
                particles_born = particles_born, 
                weights_born = w_born, 
                particles_surv = particles_surv,
                weights_surv = w_surv,
                prob = q, 
                N_eff = N_eff,
                N_eff_surv = N_eff_surv,
                N_eff_surv_normalized = N_eff_surv_normalized,
                N_eff_born = N_eff_born,
                N_eff_born_normalized = N_eff_born_normalized,
        )
        
    def parameters(self) -> dict[str, Any]:

        return self.__dict__

    def override(self, **kwargs) -> "BerParticleFilter":

        new_args = dict(self.parameters(), **kwargs)
        return BerParticleFilter(**new_args)

