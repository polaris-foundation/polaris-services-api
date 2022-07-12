import dotenv

env_obj = dotenv.main.DotEnv("local.env", verbose=True, override=False)
env_obj.set_as_environment_variables()
