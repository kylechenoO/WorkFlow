## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import pandas as pd

class DataTransformer(object):
    def __init__(self, logger: object) -> None:
        self.logger = logger

    def dicts2df(self, context: dict, cfgs: dict) -> dict:
        data = cfgs['data']
        df = pd.DataFrame(data)
        return {
            'status': True,
            'data': df
        }

    def df2dicts(self, context: dict, cfgs: dict) -> dict:
        df = cfgs['data']
        data = df.to_dict(orient = 'records')
        return {
            'status': True,
            'data': data
        }
