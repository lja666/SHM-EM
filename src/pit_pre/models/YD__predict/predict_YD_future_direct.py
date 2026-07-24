# -*- coding: utf-8 -*-
"""
============================================================
YD 未来预测代码：直接加载最优模型，不训练，不贝叶斯
============================================================

你的目的：
    输入原来的监测数据，直接得到未来 YD 预测数据。

这个代码做什么：
    1. 读取历史/平台过去数据；
    2. 读取 best_model_YD_custom_m10_n3.pth；
    3. 优先从 best_model 权重形状中识别模型参数；
    4. 权重文件中识别不到的参数，使用下面 FALLBACK_PARAMS；
    5. 取最近 m+lag 行连续数据；
    6. 输出未来 n 步 YD 预测结果。

这个代码不做什么：
    1. 不做 Optuna 贝叶斯优化；
    2. 不训练模型；
    3. 不计算 R；
    4. 不计算 RMSE/MAE；
    5. 不画图；
    6. 不做测试集评价。

重要说明：
    因为你之前训练时没有额外保存 scaler_all.pkl 和 scaler_response.pkl，
    所以本代码会用“原来的训练数据”重新拟合同样的 scaler。
    这不是重新训练模型，只是为了把输入数据按训练时的方式归一化，
    并把预测结果反归一化成真实 YD 数值。

使用方式：
    1. 把本代码和 best_model_YD_custom_m10_n3.pth 放在同一个文件夹；
    2. 修改 DATA_PATH 为平台过去数据或原始数据路径；
    3. 运行：
           python predict_YD_future_direct.py
    4. 得到：
           YD_future_prediction_wide.csv
           YD_future_prediction_long.csv

输出说明：
    wide 版本：
        每一行是一个未来预测步，例如未来 3 分钟、6 分钟、9 分钟；
        每一列是一个 YD 测点的预测值。

    long 版本：
        每一行是一个“未来时间 + 测点 + 预测值”，更适合写入数据库。
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

import torch
import torch.nn as nn


# =========================================================
# 1. 需要你改的路径
# =========================================================

# 平台过去数据 / 原始历史数据路径。
# 这个数据必须是整理好的宽表：
# 每一行是一个时间点；
# 必须包含 time1；
# 建议包含 time；
# 必须包含 YD_value、XD_value、Strain_value、Pressure_value、water_value 列。
DATA_PATH = r"input_wide.csv"

# 训练好的最优模型路径。
# 默认和本代码放在同一个文件夹。
MODEL_PATH = r"./best_model_YD_custom_m10_n3.pth"

# 输出文件。
OUTPUT_WIDE_PATH = r"./YD_future_prediction_wide.csv"
OUTPUT_LONG_PATH = r"./YD_future_prediction_long.csv"


# =========================================================
# 2. 如果 best_model 中无法识别，就使用这些参数
# =========================================================
# 你提供的备用参数如下。
# 注意：
#     本代码会优先根据 best_model_YD_custom_m10_n3.pth 的权重形状识别参数；
#     识别不到的，例如 num_heads、dropout、m、lag，会使用这里的值；
#     如果权重形状和这里冲突，以权重形状为准。
FALLBACK_PARAMS = {
    "m": 10,
    "lag": 6,
    "attn_dim": 64,
    "num_heads": 4,
    "ff_hidden_dim": 128,
    "conv_hidden_dim": 64,
    "kernel_size": 7,
    "dropout": 0.055797544260816734,
    "learning_rate": 0.00027010527749605503,  # 预测时不用，只保留记录
    "batch_size": 64,                         # 预测时不用，只保留记录
}

# 固定预测步长。
# 如果 best_model 权重中能识别 n，则会覆盖这里。
FALLBACK_N = 3

# 数据采样间隔，单位分钟。
# 你的数据是 3 分钟一条，所以 n=3 表示未来 9 分钟。
TIME_STEP_MINUTES = 3

# 是否检查最近 m+lag 行 time1 连续。
CHECK_TIME1_STEP = True

# 原训练代码的 scaler 拟合范围。
# 你的训练代码是：
#   总数据前 80% 作为 train_all；
#   train_all 前 80% 作为 final_train；
#   scaler_all 和 scaler_response fit 在 final_train 上。
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

        self.trans_proj = nn.Linear(raw_trans_dim, attn_dim)

        self.transformer = TransformerEncoderLayer(
            input_dim=attn_dim,
            num_heads=num_heads,
            ff_hidden_dim=ff_hidden_dim,
            dropout=dropout
        )

        self.conv_response = Conv1dLayer(response_dim, conv_hidden_dim, kernel_size, dropout)
        self.conv_env = Conv1dLayer(env_dim, conv_hidden_dim, kernel_size, dropout)
        self.conv_trans = Conv1dLayer(attn_dim, conv_hidden_dim, kernel_size, dropout)

        self.final_conv = Conv1dLayer(conv_hidden_dim, response_dim, kernel_size, dropout)

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
# 4. 读取模型权重，并优先从权重中识别参数
# =========================================================

def load_state_dict(model_path):
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(
            f"没有找到最优模型文件：{model_path}\n"
            f"请确认 best_model_YD_custom_m10_n3.pth 和本代码在同一目录，或修改 MODEL_PATH。"
        )

    state = torch.load(model_path, map_location="cpu")

    if not isinstance(state, dict):
        raise TypeError("模型文件不是 PyTorch state_dict 格式，无法加载。")

    return state


def infer_params_from_best_model(state, fallback_params):
    """
    优先从 best_model 的权重形状识别模型结构参数。
    权重里不能识别的参数，用 fallback_params。
    """

    params = dict(fallback_params)

    # trans_proj.weight: [attn_dim, raw_trans_dim]
    if "trans_proj.weight" in state:
        params["attn_dim"] = int(state["trans_proj.weight"].shape[0])
        params["raw_trans_dim"] = int(state["trans_proj.weight"].shape[1])

    # conv_response.conv1d.weight: [conv_hidden_dim, response_dim, kernel_size]
    if "conv_response.conv1d.weight" in state:
        params["conv_hidden_dim"] = int(state["conv_response.conv1d.weight"].shape[0])
        params["response_dim"] = int(state["conv_response.conv1d.weight"].shape[1])
        params["kernel_size"] = int(state["conv_response.conv1d.weight"].shape[2])

    # conv_env.conv1d.weight: [conv_hidden_dim, env_dim, kernel_size]
    if "conv_env.conv1d.weight" in state:
        params["env_dim"] = int(state["conv_env.conv1d.weight"].shape[1])

    # transformer.self_ff.0.weight: [ff_hidden_dim, attn_dim]
    if "transformer.self_ff.0.weight" in state:
        params["ff_hidden_dim"] = int(state["transformer.self_ff.0.weight"].shape[0])

    # fc.weight: [response_dim*n, response_dim*(m*2+lag)]
    if "fc.weight" in state and "response_dim" in params:
        fc_out_dim = int(state["fc.weight"].shape[0])
        fc_in_dim = int(state["fc.weight"].shape[1])

        response_dim = int(params["response_dim"])
        params["n"] = int(fc_out_dim // response_dim)

        m2_plus_lag = int(fc_in_dim // response_dim)

        # m 和 lag 无法单独从 fc.weight 唯一确定，只能确定 2m+lag。
        # 因此优先使用 fallback 的 m 和 lag，然后检查是否匹配。
        fallback_m = int(fallback_params["m"])
        fallback_lag = int(fallback_params["lag"])

        if 2 * fallback_m + fallback_lag == m2_plus_lag:
            params["m"] = fallback_m
            params["lag"] = fallback_lag
        else:
            # 如果 fallback 不匹配，尝试保持 m，自动修正 lag。
            corrected_lag = m2_plus_lag - 2 * fallback_m
            if corrected_lag > 0:
                params["m"] = fallback_m
                params["lag"] = int(corrected_lag)
                print(
                    f"警告：fallback 的 2m+lag 不匹配模型权重，"
                    f"已根据 fc.weight 自动把 lag 改为 {corrected_lag}。"
                )
            else:
                raise ValueError(
                    f"无法根据模型权重确定 m 和 lag。\n"
                    f"模型要求 2m+lag={m2_plus_lag}，"
                    f"但 fallback m={fallback_m}, lag={fallback_lag} 不匹配。"
                )

    # num_heads 无法从权重形状唯一确定，使用 fallback。
    params["num_heads"] = int(fallback_params["num_heads"])

    # dropout 不影响 eval 预测结果，但构造模型时需要传入，使用 fallback。
    params["dropout"] = float(fallback_params["dropout"])

    # 如果权重里识别不到 n，使用 fallback。
    if "n" not in params:
        params["n"] = int(FALLBACK_N)

    return params


# =========================================================
# 5. 读取数据，并识别列
# =========================================================

def read_data_and_columns(data_path):
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

    # 这个顺序必须与原训练代码一致。
    input_cols = yd_cols + xd_cols + strain_cols + pressure_cols + water_cols

    return df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols


# =========================================================
# 6. 用原来的数据拟合 scaler
# =========================================================

def fit_scalers(df, input_cols, yd_cols):
    """
    按原训练代码的方式拟合 scaler。

    原代码逻辑：
        1. 总数据前 80% 为 df_train_all；
        2. df_train_all 前 80% 为 df_final_train；
        3. scaler_all.fit(df_final_train)
        4. scaler_response.fit(df_final_train 的 YD 列)
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
    scaler_response.fit(df_final_train[yd_cols])

    return scaler_all, scaler_response


# =========================================================
# 7. 构造最近 m+lag 行输入
# =========================================================

def build_latest_input(df, input_cols, yd_cols, water_cols, scaler_all, params):
    """
    取数据最后 m+lag 行，构造模型输入。

    训练代码中的输入对应关系：
        x_response = 最近 m 行 YD
        x_cat      = 最近 m 行 YD + XD + Strain + Pressure
        x_env      = 考虑 lag 的 water
    """

    m = int(params["m"])
    lag = int(params["lag"])

    required_rows = m + lag

    if len(df) < required_rows:
        raise ValueError(
            f"输入数据至少需要 {required_rows} 行，即 m+lag={m}+{lag}。"
            f"当前只有 {len(df)} 行。"
        )

    latest_df = df.iloc[-required_rows:].reset_index(drop=True)

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

    yd_dim = len(yd_cols)
    idx_yd_start = 0
    idx_yd_end = yd_dim

    # water 是 input_cols 最后一组。
    idx_env_start = input_cols.index(water_cols[0])
    idx_env_end = len(input_cols)

    # 对应原训练代码：
    # x_response.append(values[i:i+m, YD])
    # x_cat.append(values[i:i+m, YD+XD+Strain+Pressure])
    # x_env.append(values[i-lag+m:i+m, water])
    #
    # 对在线预测来说，latest_df 一共 m+lag 行：
    # 前 lag 行用于 water 滞后；
    # 后 m 行用于主输入。
    x_response_np = values[lag:lag + m, idx_yd_start:idx_yd_end]
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
# 8. 加载模型
# =========================================================

def build_and_load_model(state, params):
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
# 9. 整理输出
# =========================================================

def make_output(pred_inverse, yd_cols, latest_time, latest_time1, params):
    n = int(params["n"])

    wide_rows = []

    for step in range(1, n + 1):
        row = {
            "step": step,
            "future_time1": latest_time1 + step,
        }

        if latest_time is not None and not pd.isna(latest_time):
            row["future_time"] = latest_time + pd.Timedelta(minutes=TIME_STEP_MINUTES * step)

        for j, col in enumerate(yd_cols):
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

        for j, col in enumerate(yd_cols):
            long_rows.append({
                "step": step,
                "future_time": future_time,
                "future_time1": future_time1,
                "point": col,
                "YD_pred": pred_inverse[step - 1, j]
            })

    long_df = pd.DataFrame(long_rows)

    return wide_df, long_df


# =========================================================
# 10. 主程序：直接预测未来
# =========================================================

def main():
    print("当前设备：", DEVICE)

    print("\n1. 加载 best_model 权重...")
    state = load_state_dict(MODEL_PATH)

    print("2. 优先根据 best_model 权重识别模型参数...")
    params = infer_params_from_best_model(state, FALLBACK_PARAMS)

    print("最终用于预测的参数：")
    print(json.dumps(params, ensure_ascii=False, indent=4))

    print("\n3. 读取平台过去数据 / 原始数据...")
    df, yd_cols, xd_cols, strain_cols, pressure_cols, water_cols, input_cols = read_data_and_columns(DATA_PATH)

    # 检查数据列数是否与模型权重匹配
    expected_response_dim = int(params["response_dim"])
    expected_env_dim = int(params["env_dim"])
    expected_raw_trans_dim = int(params["raw_trans_dim"])

    actual_response_dim = len(yd_cols)
    actual_env_dim = len(water_cols)
    actual_raw_trans_dim = len(yd_cols) + len(xd_cols) + len(strain_cols) + len(pressure_cols)

    if actual_response_dim != expected_response_dim:
        raise ValueError(
            f"YD列数和模型不一致：数据中 {actual_response_dim} 列，"
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

    print("4. 按原训练方式拟合 scaler...")
    scaler_all, scaler_response = fit_scalers(df, input_cols, yd_cols)

    print("5. 构造最近 m+lag 行输入...")
    x_response, x_env, x_cat, latest_time, latest_time1 = build_latest_input(
        df, input_cols, yd_cols, water_cols, scaler_all, params
    )

    print("6. 构造并加载模型...")
    model = build_and_load_model(state, params)

    print("7. 开始预测未来 YD...")
    with torch.no_grad():
        pred_scaled = model(
            x_response.to(DEVICE),
            x_env.to(DEVICE),
            x_cat.to(DEVICE)
        )

    # 模型输出形状：[1, n, response_dim]
    pred_scaled_2d = pred_scaled.cpu().numpy().reshape(-1, int(params["response_dim"]))

    # 反归一化，得到真实量纲下的 YD 预测值
    pred_inverse = scaler_response.inverse_transform(pred_scaled_2d)

    wide_df, long_df = make_output(pred_inverse, yd_cols, latest_time, latest_time1, params)

    wide_df.to_csv(OUTPUT_WIDE_PATH, index=False, encoding="utf-8-sig")
    long_df.to_csv(OUTPUT_LONG_PATH, index=False, encoding="utf-8-sig")

    print("\n预测完成！")
    print("宽表预测结果：", OUTPUT_WIDE_PATH)
    print("长表预测结果：", OUTPUT_LONG_PATH)
    print("\n预测结果预览：")
    print(wide_df.head())

    return wide_df, long_df


if __name__ == "__main__":
    main()
