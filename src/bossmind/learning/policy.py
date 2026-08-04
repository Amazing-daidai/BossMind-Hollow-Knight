import torch

# bc模型
class BCPolicy(torch.nn.Module):
    def __init__(self, obs_dim: int, action_dim: int):
        super().__init__()
        # MLP模型
        self.mlp = torch.nn.Sequential()