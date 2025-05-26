import logging, pyuac
import os
import time
from src.util.logger import Logger
from src.helper.config import Config
from ssfn import SSFNHandler
from src.util.steam_downgrader import SteamDowngrader

# 로깅 시스템 설정
logging.basicConfig(handlers=[logging.FileHandler('ssfntool.log', 'w+', 'utf-8')], level=logging.ERROR, format='%(asctime)s: %(message)s')

class Main:
    def __init__(self) -> None:
        self.logger = Logger()
        self.config = Config()
        self.ssfn_handler = SSFNHandler()
        self.steam_downgrader = SteamDowngrader()

    def start(self):
        self.logger.log("INFO", f"SSFN 파일 교체 및 Steam Rollback 도구를 시작합니다. {self.config.username}님 환영합니다!")

        # --- 1. SSFN 파일 교체 로직 ---
        self.logger.log("INFO", "로컬 SSFN 파일 교체 작업을 시작합니다...")

        YOUR_SSFN_FILE_NAME = "ssfn45221453585958369" # <-- 이 부분을 당신의 실제 SSFN 파일 이름으로 변경하세요!
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        local_ssfn_filepath = os.path.join(current_script_dir, YOUR_SSFN_FILE_NAME)

        steam_installation_path = self.config.get_steam_path()

        if not steam_installation_path or not os.path.isdir(steam_installation_path):
            self.logger.log("ERROR", "Steam 설치 경로가 유효하지 않거나 설정되지 않았습니다. 'steam_installation_path' 변수를 올바르게 설정하세요.")
            self.logger.exit_program()

        self.logger.log("INFO", f"로컬 SSFN 파일 소스 경로: {local_ssfn_filepath}")
        self.logger.log("INFO", f"Steam 대상 디렉토리 경로: {steam_installation_path}")

        ssfn_copy_success = self.ssfn_handler.use_local_ssfn(local_ssfn_filepath, steam_installation_path)

        if not ssfn_copy_success:
            self.logger.log("ERROR", "SSFN 파일 교체에 실패했습니다. Steam 관련 작업에 문제가 발생할 수 있습니다. 프로그램을 종료합니다.")
            self.logger.exit_program()
        else:
            self.logger.log("INFO", "SSFN 파일이 성공적으로 Steam 디렉토리로 교체되었습니다!")
        # --- SSFN 파일 교체 로직 끝 ---

        time.sleep(2)
        self.logger.log("INFO", "Steam 클라이언트 다운그레이드 작업을 시작합니다...")

        # --- 2. Steam 클라이언트 다운그레이드 로직
        self.steam_downgrader.execute_downgrader_online()

        self.logger.log("INFO", "모든 작업이 완료되었습니다. Steam 클라이언트가 실행될 것입니다.")
        self.logger.log("INFO", "네트워크를 차단한 후 Steam 클라이언트의 동작을 확인하세요.")

        self.logger.log("INFO", "모든 작업이 완료되었습니다.")


if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        print("관리자 권한으로 다시 시작합니다! 이 창은 닫으셔도 됩니다.")
        pyuac.runAsAdmin()
    else:
        app = Main()
        app.start()
        input("모든 작업이 완료되었습니다. 창을 닫으려면 Enter를 누르세요...")