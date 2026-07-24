# -*- coding: utf-8 -*-
"""
============================================================
土压力类 Strain 未来预测代码：固定最优参数 + 直接预测未来
============================================================

用途：
    输入平台过去监测数据，直接得到未来 Strain 预测数据。

给平台开发人员看的最简说明：
    1. 不要运行训练代码；
    2. 不要重新贝叶斯优化；
    3. 不要重新训练；
    4. 只需要运行本文件；
    5. 把 DATA_PATH 改成平台导出的历史监测数据 CSV；
    6. 把 MODEL_PATH 改成 best_model_Strain_optuna.pth 的实际路径；
    7. 把 BEST_PARAMS_PATH 改成 best_params.json 的实际路径；
    8. 运行后会生成两个预测结果 CSV。

整体输入输出：
    输入：
        平台过去数据 CSV
        best_model_Strain_optuna.pth
        best_params.json

    输出：
        Strain_future_prediction_wide.csv
        Strain_future_prediction_long.csv

时间步说明：
    如果监测数据是 3 分钟一条：
        step=1 表示未来 3 分钟；
        step=2 表示未来 6 分钟；
        step=3 表示未来 9 分钟。

本代码适用于：
    已经训练完成的 Strain 模型：
        best_model_Strain_optuna.pth

    已经保存好的最优参数：
        best_params.json

这个代码做什么：
    1. 读取平台过去数据 / 原来的历史数据；
    2. 读取 best_params.json 中的最优参数；
    3. 加载 best_model_Strain_optuna.pth；
    4. 用最近 m+lag 行连续数据构造输入；
    5. 预测未来 n 步 Strain_value；
    6. 输出 CSV 结果。

这个代码不做什么：
    1. 不做 Optuna 贝叶斯优化；
    2. 不重新训练模型；
    3. 不计算 R；
    4. 不计算 RMSE/MAE；
    5. 不画图；
    6. 不做测试集评价。

重要说明：
    这里预测的是 Strain_value，不是 Pressure_value。

    模型输入结构仍然是：
        YD + XD + Strain + Pressure + water

    但是预测目标是：
        Strain_value

    time 和 time1 不进入模型：
        time  只用于输出 future_time；
        time1 只用于排序和连续性检查。

输出：
    Strain_future_prediction_wide.csv
    Strain_future_prediction_long.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

import torch
import torch.nn as nn


# =========================================================
# 1. 平台使用时主要修改这里
# =========================================================

# 平台过去数据 / 原始历史数据路径。
#
# 这个数据必须是整理好的宽表：
#   每一行 = 一个时间点；
#   每一列 = 一个监测变量；
#   必须包含 time1；
#   建议包含 time；
#   必须包含 YD_value、XD_value、Strain_value、Pressure_value、water_value。
#
# 程序会自动按 time1 排序，然后取最后 m+lag 行进行未来预测。
#
# 例如当前最优参数：
#   m = 10
#   lag = 3
#
# 那么平台输入数据至少需要最近 13 行连续数据。
# 当然，DATA_PATH 也可以给完整历史数据，程序会自动取最后 13 行。
DATA_PATH = r"input_wide.csv"

# 已训练好的 Strain 最优模型路径。
#
# 注意：
#   这里必须是用 Strain_value 作为目标训练出来的模型。
#   不能用 Pressure 模型替代。
#
# 推荐部署方式：
#   把本代码、best_model_Strain_optuna.pth、best_params.json
#   放在同一个文件夹里。
MODEL_PATH = r"./best_model_Strain_optuna.pth"

# Strain 模型训练时保存的最优参数。
#
# 这个文件提供：
#   fixed_m
#   fixed_n
#   lag
#   num_heads
#   dropout
#   等模型构造时需要的参数。
#
# 代码会先读取它，再结合 .pth 权重形状校正模型结构。
BEST_PARAMS_PATH = r"./best_params.json"

# 输出文件。
#
# wide:
#   一行表示一个未来预测步；
#   每列表示一个 Strain 测点预测值；
#   适合直接用 Excel 查看。
#
# long:
#   一行表示一个未来时间点下某个测点的预测值；
#   适合写入健康监测平台数据库。
OUTPUT_WIDE_PATH = r"./Strain_future_prediction_wide.csv"
OUTPUT_LONG_PATH = r"./Strain_future_prediction_long.csv"


# =========================================================
# 2. 固定参数设置
# =========================================================

# 数据采样间隔，单位：分钟。
# 如果你的数据是 3 分钟一条，则：
#   step=1 表示未来 3 分钟；
#   step=2 表示未来 6 分钟；
#   step=3 表示未来 9 分钟。
# 如果以后采样间隔不是 3 分钟，例如改成 5 分钟，
# 这里也要同步改成 5。
TIME_STEP_MINUTES = 3

# 是否检查最近 m+lag 行 time1 连续。
# 建议保持 True。
CHECK_TIME1_STEP = True

# 原训练代码中的 scaler 拟合范围。
# 训练代码逻辑：
#   总数据前 80% 作为 train_all；
#   train_all 前 80% 作为 final_train；
#   scaler_all 和 scaler_response 都 fit 在 final_train 上。
TRAIN_RATIO = 0.8
INNER_TRAIN_RATIO = 0.8

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# =========================================================
# 3. 模型结构：必须和训练代码保持一致
# =========================================================

class TransformerEncoderLayer(nn.Module):
    def __init__(self, input_dim, num_heads, ff_hidden_dim, dropout):
        super(TransformerEncoderLayer, self).__init__()

        self.self_attn = nn.MultiheadAttention(
            embed_dim=input_dim,
            num_heads=num_heads,
            batch_first=True
        )

        self.self_ff = nn.Sequential(
            nn.Linear(input_dim, ff_hidden_dim),
            nn.ReLU(),
            nn.Linear(ff_hidden_dim, input_dim)
        )

        self.norm1 = nn.LayerNorm(input_dim)
        self.norm2 = nn.LayerNorm(input_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        attn_output, _ = self.self_attn(x, x, x)
        x = self.norm1(x + self.dropout(attn_output))

        ff_output = self.self_ff(x)
        x = self.norm2(x + self.dropout(ff_output))

        return x


class Conv1dLayer(nn.Module):
    def __init__(self, input_dim, output_dim, kernel_size, dropout):
        super(Conv1dLayer, self).__init__()

        self.conv1d = nn.Conv1d(
            in_channels=input_dim,
            out_channels=output_dim,
            kernel_size=kernel_size,
            padding=kernel_size // 2
        )

        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = x.permute(0, 2, 1)
        x = self.conv1d(x)
        x = self.dropout(self.relu(x))
        x = x.permute(0, 2, 1)
        return x


class TransformerCnn(nn.Module):
    def __init__(self, response_dim, env_dim, raw_trans_dim, attn_dim,
                 num_heads, ff_hidden_dim, conv_hidden_dim,
                 kernel_size, dropout, n_steps, m, lag):
        super(TransformerCnn, self).__init__()

        self.response_dim = response_dim
        self.n_steps = n_steps

        # 多源结构输入 YD+XD+Strain+Pressure 先映射到注意力维度
        self.trans_proj = nn.Linear(raw_trans_dim, attn_dim)

        self.transformer = TransformerEncoderLayer(
            input_dim=attn_dim,
            num_heads=num_heads,
            ff_hidden_dim=ff_hidden_dim,
            dropout=dropout
        )

        # 三个 CNN 分支：
        #   conv_response: 历史 Strain
        #   conv_env     : water
        #   conv_trans   : Transformer 输出
        self.conv_response = Conv1dLayer(response_dim, conv_hidden_dim, kernel_size, dropout)
        self.conv_env = Conv1dLayer(env_dim, conv_hidden_dim, kernel_size, dropout)
        self.conv_trans = Conv1dLayer(attn_dim, conv_hidden_dim, kernel_size, dropout)

        self.final_conv = Conv1dLayer(conv_hidden_dim, response_dim, kernel_size, dropout)

        # 输出未来 n 步 Strain
        self.fc = nn.Linear(response_dim * (m * 2 + lag), response_dim * n_steps)

    def forward(self, x_response, x_env, x_cat):
        x_cat = self.trans_proj(x_cat)
        x_cat = self.transformer(x_cat)

        x_response_conv = self.conv_response(x_response)
        x_env_conv = self.conv_env(x_env)
        x_cat_conv = self.conv_trans(x_cat)

        x_concat = torch.cat([x_response_conv, x_env_conv, x_cat_conv], dim=1)

        x_final_conv = self.final_conv(x_concat)
        x_final_flat = x_final_conv.reshape(x_final_conv.size(0), -1)
        x_final_fc = self.fc(x_final_flat)

        output = x_final_fc.view(x_final_conv.size(0), self.n_steps, self.response_dim)
        return output


# =========================================================
# 4. 参数与模型加载
# =========================================================

def load_best_params(path):
    """
    读取 best_params.json。

    为什么要读 best_params？
        因为 .pth 文件只保存模型权重；
        有些结构参数不能从权重中唯一判断；
        例如 num_heads、dropout、m、lag。
        所以平台预测时需要 best_params.json 辅助构造模型。

    当前上传的 best_params.json 中包含：
        lag
        attn_dim
        num_heads
        ff_hidden_dim
        conv_hidden_dim
        kernel_size
        dropout
        learning_rate
        batch_size
        fixed_m
        fixed_n

    预测阶段不会使用 learning_rate 和 batch_size，
    它们只属于训练阶段参数。
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"没有找到 best_params.json：{path}")

    with open(path, "r", encoding="utf-8") as f:
        params = json.load(f)

    params["m"] = int(params.get("fixed_m", params.get("m", 10)))
    params["n"] = int(params.get("fixed_n", params.get("n", 3)))

    return params


def load_state_dict(model_path):
    """
    加载已训练好的 Strain 模型权重。
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"没有找到模型文件：{model_path}")

    state = torch.load(model_path, map_location="cpu")

    if not isinstance(state, dict):
        raise TypeError("模型文件不是 PyTorch state_dict 格式，无法加载。")

    return state


def infer_params_from_best_model(state, params):
    """
    从 best_model 权重形状中识别模型结构参数。

    为什么还要从权重识别？
        为了避免 best_params.json 和 best_model.pth 不一致。
        如果二者不一致，模型加载会报维度错误。
        因此这里优先用权重形状确认：
            attn_dim
            raw_trans_dim
            response_dim
            env_dim
            conv_hidden_dim
            kernel_size
            ff_hidden_dim
            n

    但以下参数无法完全从权重唯一确定：
            num_heads
            dropout
            m
            lag

    所以这些继续使用 best_params.json。

    原则：
        能从权重识别的，以权重为准；
        权重不能识别的，如 num_heads、dropout、m、lag，用 best_params.json。
    """

    if "trans_proj.weight" in state:
        params["attn_dim"] = int(state["trans_proj.weight"].shape[0])
        params["raw_trans_dim"] = int(state["trans_proj.weight"].shape[1])

    if "conv_response.conv1d.weight" in state:
        params["conv_hidden_dim"] = int(state["conv_response.conv1d.weight"].shape[0])
        params["response_dim"] = int(state["conv_response.conv1d.weight"].shape[1])
        params["kernel_size"] = int(state["conv_response.conv1d.weight"].shape[2])

    if "conv_env.conv1d.weight" in state:
        params["env_dim"] = int(state["conv_env.conv1d.weight"].shape[1])

    if "transformer.self_ff.0.weight" in state:
        params["ff_hidden_dim"] = int(state["transformer.self_ff.0.weight"].shape[0])

    if "fc.weight" in state and "response_dim" in params:
        fc_out_dim = int(state["fc.weight"].shape[0])
        fc_in_dim = int(state["fc.weight"].shape[1])

        response_dim = int(params["response_dim"])
        params["n"] = int(fc_out_dim // response_dim)

        m2_plus_lag = int(fc_in_dim // response_dim)
        m = int(params["m"])
        lag = int(params["lag"])

        # fc 只能识别 2m+lag，不能单独识别 m 和 lag。
        # 所以先使用 best_params 中的 fixed_m 和 lag，再检查是否匹配。
        if 2 * m + lag != m2_plus_lag:
            corrected_lag = m2_plus_lag - 2 * m
            if corrected_lag > 0:
                print(
                    f"警告：best_params 中的 2m+lag 与模型权重不一致，"
                    f"根据模型权重把 lag 从 {lag} 改为 {corrected_lag}。"
                )
                params["lag"] = int(corrected_lag)
            else:
                raise ValueError(
                    f"无法确定 m 和 lag：模型要求 2m+lag={m2_plus_lag}，"
                    f"当前 m={m}, lag={lag}。"
                )

    # 这两个不能唯一从权重识别，必须用 best_params。
    params["num_heads"] = int(params["num_heads"])
    params["dropout"] = float(params["dropout"])

    return params


# =========================================================
# 5. 读取数据并识别列
# =========================================================

def read_data_and_columns(data_path):
    """
    读取平台输入数据，并识别各类列。

    输入 CSV 必须包含：
        time1
        YD_value
        XD_value
        Strain_value
        Pressure_value
        water_value

    其中：
        time1 用来排序和检查连续性；
        time 如果存在，用来生成 future_time；
        time 和 time1 都不会进入模型。

    模型真正输入列顺序必须保持：
        YD + XD + Strain + Pressure + water

    这个顺序必须和训练代码一致，否则预测会错。
    """
    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(f"没有找到数据文件：{data_path}")

    df = pd.read_csv(data_path)

    if "time1" not in df.columns:
        raise ValueError("输入数据必须包含 time1 列。")

    df["time1"] = pd.to_numeric(df["time1"], errors="coerce")
    if df["time1"].isna().sum() > 0:
        raise ValueError("time1 列存在无法转换为数值的内容。")

    df = df.sort_values("time1").reset_index(drop=True)

    yd_cols = [c for c in df.columns if c.endswith("YD_value")]
    xd_cols = [c for c in df.columns if c.endswith("XD_value")]
    strain_cols = [c for c in df.columns if c.endswith("Strain_value")]
    pressure_cols = [c for c in df.columns if c.endswith("Pressure_value")]
    water_cols = [c for c in df.columns if c.endswith("water_value")]

    if len(yd_cols) == 0:
        raise ValueError("未识别到 YD_value 列。")
    if len(xd_cols) == 0:
        raise ValueError("未识别到 XD_value 列。")
    if len(strain_cols) == 0:
        raise ValueError("未识别到 Strain_value 列。")
    if len(pressure_cols) == 0:
        raise ValueError("未识别到 Pressure_value 列。")
    if len(water_cols) == 0:
        raise ValueError("未识别到 water_value 列。")

    # 这个顺序必须和训练代码一致。
    input_cols = yd_cols + xd_cols + strain_cols + pressure_cols + water_cols

    return df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols


# =========================================================
# 6. 拟合 scaler
# =========================================================

def fit_scalers(df, input_cols, strain_cols):
    """
    按训练代码方式拟合 scaler。

    注意：
        这一步不是训练模型。
        只是为了恢复训练时的数据缩放方式。

    为什么预测时还要 scaler？
        模型训练时输入数据经过 MinMaxScaler 归一化；
        因此平台预测时也必须用同样的数据尺度输入模型。
        模型输出后，还要用 scaler_response 把结果变回真实 Strain 数值。

    当前因为训练时没有单独保存 scaler_all.pkl / scaler_response.pkl，
    所以这里用原始历史数据按训练代码的同样规则重新 fit scaler。
    如果以后保存了 scaler 文件，可以改成直接加载 scaler。
    

    注意：
        这不是重新训练模型。
        只是恢复训练时的数据归一化方式。
    """

    df_model = df[input_cols].copy()

    for col in input_cols:
        df_model[col] = pd.to_numeric(df_model[col], errors="coerce")

    if df_model.isna().sum().sum() > 0:
        bad_cols = df_model.isna().sum()[df_model.isna().sum() > 0]
        raise ValueError(f"数据存在缺失或非数值，请先处理：\n{bad_cols}")

    n_samples = len(df_model)
    n_train = int(n_samples * TRAIN_RATIO)
    df_train_all = df_model.iloc[:n_train].reset_index(drop=True)

    n_final_inner = int(len(df_train_all) * INNER_TRAIN_RATIO)
    df_final_train = df_train_all.iloc[:n_final_inner].reset_index(drop=True)

    scaler_all = MinMaxScaler()
    scaler_all.fit(df_final_train)

    scaler_response = MinMaxScaler()
    scaler_response.fit(df_final_train[strain_cols])

    return scaler_all, scaler_response


# =========================================================
# 7. 构造最近 m+lag 行输入
# =========================================================

def build_latest_input(df, input_cols, strain_cols, water_cols, scaler_all, params):
    """
    用平台过去数据的最后 m+lag 行构造模型输入。

    当前参数：
        m = 10
        lag = 3

    因此至少需要最近 13 行连续数据。

    对 Strain 模型：
        x_response = 最近 m 行 Strain
        x_cat      = 最近 m 行 YD + XD + Strain + Pressure
        x_env      = water 滞后输入

    也就是说：
        Strain 是预测目标；
        Pressure 不是预测目标，但仍然作为辅助输入特征参与预测。
    

    对 Strain 模型：
        x_response = 最近 m 行 Strain
        x_cat      = 最近 m 行 YD + XD + Strain + Pressure
        x_env      = water 滞后输入
    """

    m = int(params["m"])
    lag = int(params["lag"])

    # 预测需要的最少历史行数。
    # 如果 m=10, lag=3，则 required_rows=13。
    required_rows = m + lag

    if len(df) < required_rows:
        raise ValueError(
            f"输入数据至少需要 {required_rows} 行，即 m+lag={m}+{lag}。"
            f"当前只有 {len(df)} 行。"
        )

    # 只取最后 m+lag 行。
    # 这就是“用平台过去最近一段数据预测未来”。
    latest_df = df.iloc[-required_rows:].reset_index(drop=True)

    # 检查 time1 是否连续。
    # 如果不连续，说明中间缺少某个时间步，直接预测会破坏时间序列关系。
    if CHECK_TIME1_STEP:
        diff = latest_df["time1"].diff().dropna()
        if not (diff == 1).all():
            raise ValueError(
                "最近 m+lag 行的 time1 不连续，不能直接预测。"
                "请先对数据进行时间对齐或补齐缺失行。"
            )

    model_df = latest_df[input_cols].copy()

    for col in input_cols:
        model_df[col] = pd.to_numeric(model_df[col], errors="coerce")

    if model_df.isna().sum().sum() > 0:
        bad_cols = model_df.isna().sum()[model_df.isna().sum() > 0]
        raise ValueError(f"最近 m+lag 行存在缺失或非数值：\n{bad_cols}")

    values = scaler_all.transform(model_df)

    yd_dim = len([c for c in input_cols if c.endswith("YD_value")])
    xd_dim = len([c for c in input_cols if c.endswith("XD_value")])
    strain_dim = len(strain_cols)

    idx_yd_start = 0
    idx_yd_end = idx_yd_start + yd_dim

    idx_xd_start = idx_yd_end
    idx_xd_end = idx_xd_start + xd_dim

    idx_strain_start = idx_xd_end
    idx_strain_end = idx_strain_start + strain_dim

    idx_env_start = input_cols.index(water_cols[0])
    idx_env_end = len(input_cols)

    # latest_df 总长度 m+lag：
    # 前 lag 行用于 water 滞后；
    # 后 m 行用于主输入。
    x_response_np = values[lag:lag + m, idx_strain_start:idx_strain_end]
    x_cat_np = values[lag:lag + m, 0:idx_env_start]
    x_env_np = values[m:m + lag, idx_env_start:idx_env_end]

    x_response = torch.tensor(x_response_np[None, :, :], dtype=torch.float32)
    x_cat = torch.tensor(x_cat_np[None, :, :], dtype=torch.float32)
    x_env = torch.tensor(x_env_np[None, :, :], dtype=torch.float32)

    latest_time = None
    if "time" in latest_df.columns:
        latest_time = pd.to_datetime(latest_df["time"].iloc[-1], errors="coerce")

    latest_time1 = latest_df["time1"].iloc[-1]

    return x_response, x_env, x_cat, latest_time, latest_time1


# =========================================================
# 8. 构造并加载模型
# =========================================================

def build_and_load_model(state, params):
    """
    根据参数构造 TransformerCnn 模型，并加载 best_model 权重。

    这里最容易出错的是：
        参数和 .pth 权重不一致。

    例如：
        attn_dim 不一致；
        conv_hidden_dim 不一致；
        m、lag 不一致；
        response_dim 不一致。

    一旦不一致，model.load_state_dict(state) 会报错。
    """
    model = TransformerCnn(
        response_dim=int(params["response_dim"]),
        env_dim=int(params["env_dim"]),
        raw_trans_dim=int(params["raw_trans_dim"]),
        attn_dim=int(params["attn_dim"]),
        num_heads=int(params["num_heads"]),
        ff_hidden_dim=int(params["ff_hidden_dim"]),
        conv_hidden_dim=int(params["conv_hidden_dim"]),
        kernel_size=int(params["kernel_size"]),
        dropout=float(params["dropout"]),
        n_steps=int(params["n"]),
        m=int(params["m"]),
        lag=int(params["lag"])
    ).to(DEVICE)

    model.load_state_dict(state)
    model.eval()

    return model


# =========================================================
# 9. 输出整理
# =========================================================

def make_output(pred_inverse, strain_cols, latest_time, latest_time1, params):
    """
    把模型预测结果整理成两个 CSV。

    wide_df：
        一行 = 一个未来预测步；
        每列 = 一个 Strain 测点预测值；
        适合人工查看或 Excel 打开。

    long_df：
        一行 = 某个未来时间点下某个测点的预测值；
        适合平台数据库存储。

    pred_inverse：
        已经反归一化后的真实 Strain 预测值。
    """
    n = int(params["n"])

    wide_rows = []

    for step in range(1, n + 1):
        row = {
            "step": step,
            "future_time1": latest_time1 + step,
        }

        if latest_time is not None and not pd.isna(latest_time):
            row["future_time"] = latest_time + pd.Timedelta(minutes=TIME_STEP_MINUTES * step)

        for j, col in enumerate(strain_cols):
            row[f"{col}_Pred"] = pred_inverse[step - 1, j]

        wide_rows.append(row)

    wide_df = pd.DataFrame(wide_rows)

    front_cols = ["step"]
    if "future_time" in wide_df.columns:
        front_cols.append("future_time")
    front_cols.append("future_time1")

    other_cols = [c for c in wide_df.columns if c not in front_cols]
    wide_df = wide_df[front_cols + other_cols]

    long_rows = []
    for step in range(1, n + 1):
        future_time = None
        if latest_time is not None and not pd.isna(latest_time):
            future_time = latest_time + pd.Timedelta(minutes=TIME_STEP_MINUTES * step)

        future_time1 = latest_time1 + step

        for j, col in enumerate(strain_cols):
            long_rows.append({
                "step": step,
                "future_time": future_time,
                "future_time1": future_time1,
                "point": col,
                "Strain_pred": pred_inverse[step - 1, j]
            })

    long_df = pd.DataFrame(long_rows)

    return wide_df, long_df


# =========================================================
# 10. 主程序
# =========================================================

def main():
    """
    主程序执行顺序：

        1. 读取 best_params.json；
        2. 加载 best_model_Strain_optuna.pth；
        3. 根据模型权重校正参数；
        4. 读取平台过去数据；
        5. 拟合 scaler；
        6. 取最近 m+lag 行数据；
        7. 构造模型并加载权重；
        8. 预测未来 Strain；
        9. 输出 wide 和 long 两个 CSV。

    整个过程只做预测，不做训练。
    """
    print("当前设备：", DEVICE)

    print("\n1. 读取 best_params.json...")
    params = load_best_params(BEST_PARAMS_PATH)

    print("\n2. 加载 best_model_Strain_optuna.pth...")
    state = load_state_dict(MODEL_PATH)

    print("\n3. 根据 best_model 权重校正模型结构参数...")
    params = infer_params_from_best_model(state, params)

    print("最终用于预测的参数：")
    print(json.dumps(params, ensure_ascii=False, indent=4))

    print("\n4. 读取平台过去数据 / 原始数据...")
    df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols = read_data_and_columns(DATA_PATH)

    # 检查数据维度是否和模型权重一致。
    expected_response_dim = int(params["response_dim"])
    expected_env_dim = int(params["env_dim"])
    expected_raw_trans_dim = int(params["raw_trans_dim"])

    actual_response_dim = len(strain_cols)
    actual_env_dim = len(water_cols)
    actual_raw_trans_dim = len(yd_cols) + len(xd_cols) + len(strain_cols) + len(pressure_cols)

    if actual_response_dim != expected_response_dim:
        raise ValueError(
            f"Strain列数和模型不一致：数据中 {actual_response_dim} 列，"
            f"模型需要 {expected_response_dim} 列。"
        )

    if actual_env_dim != expected_env_dim:
        raise ValueError(
            f"water列数和模型不一致：数据中 {actual_env_dim} 列，"
            f"模型需要 {expected_env_dim} 列。"
        )

    if actual_raw_trans_dim != expected_raw_trans_dim:
        raise ValueError(
            f"YD+XD+Strain+Pressure 列数和模型不一致：数据中 {actual_raw_trans_dim} 列，"
            f"模型需要 {expected_raw_trans_dim} 列。"
        )

    print("\n5. 按原训练方式拟合 scaler...")
    scaler_all, scaler_response = fit_scalers(df, input_cols, strain_cols)

    print("\n6. 构造最近 m+lag 行输入...")
    x_response, x_env, x_cat, latest_time, latest_time1 = build_latest_input(
        df, input_cols, strain_cols, water_cols, scaler_all, params
    )

    print("\n7. 构造并加载模型...")
    model = build_and_load_model(state, params)

    print("\n8. 开始预测未来 Strain...")
    with torch.no_grad():
        pred_scaled = model(
            x_response.to(DEVICE),
            x_env.to(DEVICE),
            x_cat.to(DEVICE)
        )

    pred_scaled_2d = pred_scaled.cpu().numpy().reshape(-1, int(params["response_dim"]))
    pred_inverse = scaler_response.inverse_transform(pred_scaled_2d)

    wide_df, long_df = make_output(pred_inverse, strain_cols, latest_time, latest_time1, params)

    # 保存宽表结果，适合直接查看。
    wide_df.to_csv(OUTPUT_WIDE_PATH, index=False, encoding="utf-8-sig")

    # 保存长表结果，适合平台数据库。
    long_df.to_csv(OUTPUT_LONG_PATH, index=False, encoding="utf-8-sig")

    print("\n预测完成！")
    print("宽表预测结果：", OUTPUT_WIDE_PATH)
    print("长表预测结果：", OUTPUT_LONG_PATH)
    print("\n预测结果预览：")
    print(wide_df.head())

    return wide_df, long_df


if __name__ == "__main__":
    main()
