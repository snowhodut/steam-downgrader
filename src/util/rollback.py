import requests, os, time
from src.util.logger import Logger
from src.helper.config import Config

class SteamRollback:
    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        self.session = requests.session()

    def download_rollback(self):
        # --- 추가된 코드 시작 ---
        # 롤백 툴 폴더가 존재하는지 확인하고, 없으면 생성합니다.
        if not os.path.exists(self.config.rollback_path):
            try:
                self.logger.log("ROLLBACK", f"'{self.config.rollback_path}' 폴더를 찾을 수 없습니다. 생성합니다...")
                os.makedirs(self.config.rollback_path, exist_ok=True)
                self.logger.log("ROLLBACK", f"'{self.config.rollback_path}' 폴더 생성 완료.")
            except Exception as e:
                self.logger.log("ERROR", f"롤백 툴 폴더 생성 실패: {self.config.rollback_path}. 오류: {e}")
                self.logger.exit_program() # 폴더 없으면 진행 불가
        # --- 추가된 코드 끝 ---

        self.logger.log("ROLLBACK", "Deleting old files...")
        # 이 부분이 이제 폴더 존재 확인 후 실행되므로 FileNotFoundError를 피할 수 있습니다.
        for file in os.listdir(self.config.rollback_path):
            try:
                os.remove(os.path.join(self.config.rollback_path, file))
            except Exception as e:
                self.logger.log("WARNING", f"기존 파일 '{os.path.join(self.config.rollback_path, file)}' 삭제 실패: {e}")
        
        self.logger.log("ROLLBACK", "Downloading the tool...")
        response = self.session.get(self.config.steam_rollback_url, allow_redirects=True)
        if response.content:
            with open(self.config.rollback_exe_path, "wb") as f:
                f.write(response.content)
                self.logger.log("ROLLBACK", "Successfully downloaded the rollback tool.")
                time.sleep(1)
                return True
        else:
            self.logger.log("ERROR", "Failed to download the rollback tool! Response content was empty.")
            time.sleep(1)
            return False

    def start_rollback_exe(self):
        self.logger.log("ROLLBACK", "Starting tool...")
        # os.system 호출 전에 파일 존재 여부 확인 추가
        if not os.path.exists(self.config.rollback_exe_path):
            self.logger.log("ERROR", f"롤백 실행 파일이 '{self.config.rollback_exe_path}'에 없습니다.")
            return False # 실행 파일 없으면 바로 리턴
        
        # Windows 경로의 공백 처리 및 URL 소스명 제거
        # os.system은 start 명령어를 통해 실행하므로, 경로에 공백이 있으면 따옴표로 감싸줘야 합니다.
        # 기존 코드에 이미 따옴표가 있으므로 크게 문제는 없지만, URL 소스명은 깔끔하게 제거합니다.
        os.system(f'start "" "{self.config.rollback_exe_path}"') 
        # 첫 번째 ""는 창 제목 (옵션). 두 번째 ""는 경로의 공백 처리.
        self.logger.log("INFO", "롤백 툴이 실행되었습니다. 새 창을 확인하세요.")

    def execute_rollback(self):
        self.logger.log("ROLLBACK", "Executing the rollback tool...")
        if os.path.exists(self.config.rollback_exe_path):
            self.logger.log("ROLLBACK", "Rollback tool found, executing...")
            self.start_rollback_exe()
        else:
            self.logger.log("ERROR", "Rollback tool not found, downloading...")
            download_success = self.download_rollback()
            if download_success:
                self.logger.log("ROLLBACK", "Download successful, attempting to execute again...")
                self.start_rollback_exe() # 다운로드 성공했으면 바로 실행
            else:
                self.logger.log("ERROR", "Rollback tool download failed. Cannot execute.")
                self.logger.exit_program() # 다운로드 실패 시 프로그램 종료