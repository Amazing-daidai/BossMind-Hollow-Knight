import torch

from tqdm import tqdm

from bossmind.learning.dataset import get_dataloader
from bossmind.learning.actions import ACTION_KEY, PLAY_INFO, ENEMY_INFO, MAX_ENEMIES
from bossmind.paths import MODEL_DIR


class BCPolicy:

    def __init__(self, learning_rate=1e-3, epochs=100, batch_size=128):
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self._steps = None
        self._input_dim = len(PLAY_INFO) + len(ENEMY_INFO) * MAX_ENEMIES + MAX_ENEMIES
        self._output_dim = len(ACTION_KEY)
        self.model = None

    # bc模型
    class BCModel(torch.nn.Module):
        def __init__(self, input_dim: int, output_dim: int):
            super().__init__()
            # MLP模型
            self.mlp = torch.nn.Sequential(
                # 隐藏层1
                torch.nn.Linear(input_dim, 64),
                torch.nn.BatchNorm1d(64),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2),
                # 隐藏层2
                torch.nn.Linear(64, 128),
                torch.nn.BatchNorm1d(128),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2),
                # 隐藏层3
                torch.nn.Linear(128, 64),
                torch.nn.BatchNorm1d(64),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2),
                # 输出层
                torch.nn.Linear(64, output_dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.mlp(x)

    # 训练模型
    def train(self, batch_name: str):
        # 获取数据
        dataloader = get_dataloader(batch_name, self.batch_size)
        if len(dataloader) == 0:
            raise ValueError(f"未获得有效数据")
        # 计算总步数
        self._steps = len(dataloader) * self.epochs
        # 加载模型
        self.model = self.BCModel(self._input_dim, self._output_dim)
        # 损失函数
        loss_fn = torch.nn.BCEWithLogitsLoss()
        # 优化器
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)
        # 学习率调度器
        warm_up_steps = self._steps // 10
        # 预热
        warmup_scheduler = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=0.01, 
            end_factor=1.0, 
            total_iters=warm_up_steps
        )
        # 余弦退火
        cos_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, 
            T_max=self._steps - warm_up_steps, 
            eta_min=1e-5
        )
        # 组合
        scheduler = torch.optim.lr_scheduler.SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, cos_scheduler],
            milestones=[warm_up_steps],
        )
        # 训练模型
        print(f"Training model for {self.epochs} epochs...")
        self.model.train()
        for epoch in range(self.epochs):
            total_loss = 0
            i = 1
            for x, y in tqdm(dataloader, desc=f"Epoch {epoch+1}/{self.epochs}"):
                # 前向传播
                logits = self.model(x)
                # 计算损失
                loss = loss_fn(logits, y)
                # 清空梯度
                optimizer.zero_grad()
                # 反向传播
                loss.backward()
                # 更新参数
                optimizer.step()
                # 更新学习率
                scheduler.step()
                # 计算总损失
                total_loss += loss.item()
                # 日志
                if i % 10 == 0:
                    print(f"Batch {i}/{len(dataloader)} Loss: {loss.item():.4f}")
                i += 1

            # 计算平均损失
            avg_loss = total_loss / len(dataloader)
            # 日志
            print(f"Epoch {epoch + 1}/{self.epochs} Loss: {avg_loss:.4f}")

        # 保存模型
        if not MODEL_DIR.exists():
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(
            self.model.state_dict(), MODEL_DIR / "bc_model.pth"
        )
        print("模型保存完成")
