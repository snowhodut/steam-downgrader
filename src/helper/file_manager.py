import os
from src.util.logger import Logger

defaultConfig = """
# Tool settings
username: username_here
steam_path: "C:/Program Files (x86)/Steam"
rollback_path: "src/util/rollback"
rollback_exe_path: "src/util/rollback/steam-rollback.exe"

# Github urls
steam_rollback_url: https://github.com/IMXNOOBX/steam-rollback/releases/download/steam-rollback/steam-rollback.exe
"""

class FileManager():

    def __init__(self):
        self.logger = Logger()
        # 파일 존재 여부 확인 및 생성
        self.check_input()

    def ensure_directory(self, path):
        """Ensure that a directory exists. If it doesn't, create it."""
        if not os.path.isdir(path):
            try:
                self.logger.log("INFO", f"폴더를 찾을 수 없습니다. '{path}' 폴더를 생성합니다...")
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                self.logger.log("ERROR", f"디렉토리 '{path}' 생성 실패. 오류: {e}")

    def ensure_config(self):
        """Ensure that the config file exists. If it doesn't, create it."""
        if not os.path.isfile("config.yaml"):
            self.logger.log("INFO", "config.yaml 파일을 찾을 수 없습니다. 파일을 생성합니다...")
            with open("config.yaml", "w+", encoding='utf-8') as f:
                f.write(defaultConfig)
            self.logger.log("INFO", "config.yaml 파일이 성공적으로 생성되었습니다. 내용을 채우고 다시 시도해주세요.")
            self.logger.exit_program()

    def check_input(self):
        self.ensure_config()
        self.ensure_directory("src/util/steam_rollback_tool/")