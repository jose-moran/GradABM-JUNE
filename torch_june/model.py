from torch.nn.parameter import Parameter
import torch
from time import time

from torch_june import InfectionPassing


def get_free_memory(i):
    r = torch.cuda.memory_reserved(i)
    a = torch.cuda.memory_allocated(i)
    f = r - a  # free inside reserved
    return f


class TorchJune(torch.nn.Module):
    def __init__(self, betas, data, infections, device="cpu"):
        super().__init__()
        self.data = data.to(device)
        self._betas_to_idcs = {name: i for i, name in enumerate(betas.keys())}
        self.device = device
        self.beta_parameters = Parameter(torch.tensor(list(betas.values())))
        self.inf_network = InfectionPassing(device=device)
        self.infections = infections

    def _get_edge_types_from_timer(self, timer):
        ret = []
        for activity in timer.activities:
            ret.append("attends_" + activity)
        return ret

    def forward(self, timer, susceptibilities):
        ret = None  # torch.empty(0)
        betas = {
            beta_n: self.beta_parameters[self._betas_to_idcs[beta_n]]
            for beta_n in self._betas_to_idcs.keys()
        }
        while timer.date < timer.final_date:
            print(get_free_memory(0))
            t1 = time()
            transmissions = self.infections.get_transmissions(time=timer.now)
            infection_probs = self.inf_network(
                data=self.data,
                edge_types=self._get_edge_types_from_timer(timer),
                betas=betas,
                delta_time=timer.duration,
                transmissions=transmissions,
                susceptibilities=susceptibilities,
            )
            new_infected = self.inf_network.sample_infected(infection_probs)
            self.infections.update(new_infected=new_infected, infection_time=timer.now)
            if ret is None:
                ret = new_infected
            else:
                ret = torch.vstack((ret, new_infected))
            next(timer)
            susceptibilities = susceptibilities - new_infected
            t2 = time()
            print(f"Time-step took {t2-t1} seconds")

        return ret
