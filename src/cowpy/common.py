import logging 

def handler(self, formatter=None):
        newH = logging.StreamHandler()        
        newH.setFormatter(formatter or self._colorFormatter())
        return newH 