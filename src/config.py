import os
from pathlib import Path
from typing import NamedTuple, get_type_hints


class Config(NamedTuple):
    bot_token: str
    chat_id: int


error_message = "variable %s not found in environment"


def get_config(
    prefix: str = "tg_",
    dotenv_filename: "str | os.PathLike[str]" = ".env",
) -> Config:
    load_env_file(dotenv_filename)

    config_kwargs = {}

    for field, field_type in get_type_hints(Config).items():
        env_name = f"{prefix}{field}".upper()
        raw_value = os.environ.get(env_name)
        if raw_value is None:
            if field not in Config._field_defaults:
                raise KeyError(error_message % env_name)
            config_kwargs[field] = Config._field_defaults[field]
        else:
            config_kwargs[field] = field_type(raw_value)

    return Config(**config_kwargs)


def load_env_file(filepath: "str | os.PathLike[str]") -> None:
    path = Path(filepath)
    if not path.exists():
        return

    with path.open(encoding="utf-8") as env_file:
        for line in env_file:
            if line.lstrip().startswith("#") or "=" not in line:
                continue
            key, env_val = _parse_var_line(line)
            if key not in os.environ:
                os.environ[key] = env_val


def _parse_var_line(line: str) -> "tuple[str, str]":
    key, var_val = line.split("=", 1)
    return key.strip(), var_val.strip().strip("'\"")
