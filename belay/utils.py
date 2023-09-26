import os


def env_parse_bool(env_var, default_value=False):
    if env_var in os.environ:
        env_value = os.environ[env_var].lower()
        return env_value == "true" or env_value == "1"
    else:
        return default_value
