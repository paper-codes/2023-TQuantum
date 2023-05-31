import logging
import unittest
from os import getenv


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.logger.debug("")

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__name__)
        cls.draw = False
        level = getenv("LOG_LEVEL")
        if level:
            print(f"Got level {level}")
            logging_level = logging._nameToLevel.get(level, "ERROR")
            print(f"log level is {logging_level}")
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(module)-4s %(levelname)-8s %(funcName)-12s %(message)s"
            )
            handler.setFormatter(formatter)
            cls.logger.addHandler(handler)
            cls.logger.setLevel(logging_level)
