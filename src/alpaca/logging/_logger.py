from __future__ import annotations

from datetime import datetime

class Logger():
    log_dir = "./logs/"

    def __init__(self, file: str, tag: str, log_level: str = "info") -> None:
        self.log_level = log_level
        self.file = file
        self.tag = tag

    def _line_header(self, level: str) -> str:
        date = datetime.now().strftime(f"[%d/%m %H:%M:%S]")
        return f"{date}, {level}, {self.tag}: "

    def _log(self, msg: str, level: str) -> None:
        with open(self.log_dir + self.file + ".log", 'a') as f:
            f.write(self._line_header(level) + msg + "\n")


    def log(self, msg: str):
        if self.should_log_at_level("info"):
            self._log(msg, "INF")

    def log_error(self, msg: str):
        if self.should_log_at_level("error"):
            self._log(msg, "ERR")
            with open(self.log_dir + self.file + "_err.log", 'a') as f:
                f.write(self._line_header("ERR") + msg + "\n")

    def log_debug(self, msg: str):
        if self.should_log_at_level("debug"):
            self._log(msg, "DEB")

    def raise_exception(self, msg: str):
        self.log_error(msg)
        raise Exception(msg)

    @classmethod
    def _log_level_to_int(cls, level: str):
        levels_mapping = {
            "debug": 0,
            "info": 1,
            "error": 2
        }

        return levels_mapping.get(level)

    def should_log_at_level(self, level_of_message: str):
        return self._log_level_to_int(level_of_message) >= self._log_level_to_int(self.log_level)
