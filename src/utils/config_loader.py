"""
設定檔載入器 — 支援 YAML 多層覆蓋 + 環境變數

載入順序：base.yaml → {ENV}.yaml → 環境變數
後者覆蓋前者（deep merge）。
"""
import os
from pathlib import Path
from copy import deepcopy

import yaml
from dotenv import load_dotenv


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge：override 覆蓋 base，遞迴合併巢狀字典"""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate_config(config: dict) -> None:
    """驗證 config 包含所有必要的 key"""
    required_paths = [
        ("data", "parquet_dir"),
        ("paths", "outputs"),
        ("paths", "reports"),
    ]
    missing = []
    for keys in required_paths:
        node = config
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                missing.append(".".join(keys))
                break
            node = node[k]
    if missing:
        import warnings
        warnings.warn(f"Config missing required keys: {missing}")


def load_config(config_dir: str = None, env: str = None) -> dict:
    """
    載入設定檔。

    Args:
        config_dir: 設定檔目錄路徑，預設為 src/config/
        env: 環境名稱 (dev/prod)，預設讀取 ENV 環境變數

    Returns:
        合併後的設定字典
    """
    # 載入 .env
    load_dotenv()

    if config_dir is None:
        # 從此檔案位置往上找 src/config/
        config_dir = Path(__file__).parent.parent / "config"
    else:
        config_dir = Path(config_dir)

    # Step 1: 載入 base.yaml
    base_path = config_dir / "base.yaml"
    if not base_path.exists():
        raise FileNotFoundError(f"Base config not found: {base_path}")

    with open(base_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Step 2: 載入環境設定檔（如 dev.yaml）
    env = env or os.getenv("ENV", "dev")
    env_path = config_dir / f"{env}.yaml"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, env_config)

    # Step 3: 注入 project_root（方便後續路徑解析）
    config["_project_root"] = str(config_dir.parent.parent)
    config["_env"] = env

    # Step 4: 驗證設定
    _validate_config(config)

    return config


def resolve_path(config: dict, key: str) -> Path:
    """
    將設定中的相對路徑解析為絕對路徑。

    Args:
        config: 設定字典
        key: 路徑 key（如 "data.parquet_dir"）

    Returns:
        解析後的 Path 物件
    """
    root = Path(config.get("_project_root", "."))

    # 支援 dot notation
    parts = key.split(".")
    value = config
    for part in parts:
        value = value[part]

    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path
