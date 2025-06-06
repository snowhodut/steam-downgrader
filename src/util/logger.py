import time
from sys import exit
from os import system, name
from datetime import datetime
from colorama import Fore, Style

class Logger:

    def __init__(self):
        self.log_types = {
            "INFO": Fore.CYAN,
            "OK": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ROLLBACK": Fore.YELLOW,
            "SLEEP": Fore.YELLOW,
            "ERROR": Fore.RED,
        }

    def clear(self):
        system("cls" if name in ("nt", "dos") else "clear")

    def exit_program(self):
        self.log("INFO", "Bye!")
        time.sleep(2)
        exit()


    def log(self, type, message):
        color = self.log_types.get(type, Fore.WHITE) # 정의되지 않은 타입에 대비하여 기본 색상 설정
        now = datetime.now()
        current_time = now.strftime("%d/%m/%Y - %H:%M:%S")
        print(f"{Style.DIM}{current_time} - {Style.RESET_ALL}{Style.BRIGHT}{color}[{Style.RESET_ALL}{type}{Style.BRIGHT}{color}] {Style.RESET_ALL}{Style.BRIGHT}{Fore.WHITE}{message}")