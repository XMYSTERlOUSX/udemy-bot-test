
import os


class VarHolder:
    def __init__(self):
        self._var_dict = dict()

    def get_var(self, variable):

        if variable in self._var_dict.keys():
            return self._var_dict[variable]

        val = ""

        # Get the variable form the env [overlap]
        envval = os.environ.get(variable)

        INTS = []
        BOOLS = []
        
        if variable in INTS:
            val = int(envval) if envval is not None else val
        elif variable in BOOLS:
            if envval is not None:
                if not isinstance(envval, bool):
                    if "true" in envval.lower():
                        val = True
                    else:
                        val = False
        else:
            val = envval if envval is not None else val

        if isinstance(val, str):
            val = val.strip()

        self._var_dict[variable] = val
        return val


    def update_var(self, name, val):
        self._var_dict[name] = val
