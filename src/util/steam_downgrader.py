import os
import time
import subprocess
from src.util.logger import Logger
from src.helper.config import Config
from src.steam.reg import SteamReg

class SteamDowngrader:

    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        self.steam_reg = SteamReg()
        self.steam_path = self.config.get_steam_path()
        self.steam_exe_path = self.steam_reg.get_steam_exe_path()


    def _kill_steam_process(self):
        """실행 중인 Steam 프로세스를 종료합니다."""
        self.logger.log("INFO", "Steam 프로세스를 종료하는 중...")
        try:
            result = subprocess.run(["taskkill", "/f", "/im", "steam.exe"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

            if result.returncode == 0:
                self.logger.log("INFO", "Steam 프로세스 종료 완료.")
            elif "프로세스 \"steam.exe\"을(를) 찾을 수 없습니다." in result.stderr or result.returncode == 128:
                self.logger.log("WARNING", f"Steam 종료 중 경고: Steam 프로세스가 실행 중이 아니었습니다.")
            else:
                self.logger.log("ERROR", f"Steam 종료 중 알 수 없는 오류 발생 (오류 코드: {result.returncode}): {result.stderr.strip()}")

            time.sleep(1)

        except Exception as e:
            self.logger.log("ERROR", f"Steam 종료 중 예상치 못한 예외 발생: {e} (관리자 권한으로 실행했는지 확인하세요.)")
            time.sleep(1)


    def _create_steam_cfg(self):
        # Steam 업데이트를 영구적으로 막는 steam.cfg 파일을 생성
        steam_cfg_path = os.path.join(self.steam_path, "steam.cfg")
        cfg_content = "BootStrapperInhibitAll=enable\n"

        try:
            with open(steam_cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg_content)
            self.logger.log("INFO", f"'{steam_cfg_path}' 파일 생성 완료. Steam 업데이트가 방지됩니다.")
        except Exception as e:
            self.logger.log("ERROR", f"'{steam_cfg_path}' 파일 생성 실패: {e}")
            self.logger.exit_program()

    def _edit_loginusers_vdf_for_offline(self):
        """
        loginusers.vdf 파일을 수정하여 특정 계정이 오프라인 모드로 자동 로그인되도록 합니다.
        이는 Steam이 로그인 창을 띄우는 대신 바로 오프라인 모드로 진입하게 할 수 있습니다.
        """
        loginusers_vdf_path = os.path.join(self.steam_path, "config", "loginusers.vdf")

        if not os.path.exists(loginusers_vdf_path):
            self.logger.log("WARNING", f"'{loginusers_vdf_path}' 파일을 찾을 수 없습니다. 오프라인 로그인 설정 건너뜀.")
            return

        try:
            with open(loginusers_vdf_path, "r+", encoding="utf-8") as f:
                content = f.read()
                f.seek(0) # 파일 포인터를 처음으로 이동

                # 모든 사용자에 대해 RememberPassword, WantsOfflineMode, SkipOfflineModeWarning, AllowAutoLogin을 "1"로 설정
                content = content.replace('"RememberPassword"		"0"', '"RememberPassword"		"1"')
                content = content.replace('"RememberPassword"		"1"', '"RememberPassword"		"1"') # 이미 1인 경우 대비

                if '"WantsOfflineMode"' not in content:
                    # WantsOfflineMode가 없는 경우, 아무 SteamID64 뒤에 추가 (정확한 위치는 아닐 수 있으나 작동 가능성)
                    self.logger.log("WARNING", "loginusers.vdf에서 'WantsOfflineMode'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"WantsOfflineMode"		"0"', '"WantsOfflineMode"		"1"')
                content = content.replace('"WantsOfflineMode"		"1"', '"WantsOfflineMode"		"1"')

                if '"SkipOfflineModeWarning"' not in content:
                    self.logger.log("WARNING", "loginusers.vdf에서 'SkipOfflineModeWarning'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"SkipOfflineModeWarning"	"0"', '"SkipOfflineModeWarning"	"1"')
                content = content.replace('"SkipOfflineModeWarning"	"1"', '"SkipOfflineModeWarning"	"1"')

                if '"AllowAutoLogin"' not in content:
                    self.logger.log("WARNING", "loginusers.vdf에서 'AllowAutoLogin'를 찾을 수 없습니다. 수동으로 추가해야 할 수도 있습니다.")
                content = content.replace('"AllowAutoLogin"		"0"', '"AllowAutoLogin"		"1"')
                content = content.replace('"AllowAutoLogin"		"1"', '"AllowAutoLogin"		"1"')

                f.truncate(0) # 기존 내용 삭제
                f.write(content)
            self.logger.log("INFO", f"'{loginusers_vdf_path}' 파일 수정 완료. 오프라인 로그인 설정 시도.")
        except Exception as e:
            self.logger.log("ERROR", f"'{loginusers_vdf_path}' 파일 수정 실패: {e}")
            # 이 오류가 발생해도 프로그램 종료 대신 경고만 출력하여 다음 단계 진행 시도
            self.logger.log("WARNING", "loginusers.vdf 수정에 실패했으나, Steam 실행은 시도합니다.")

    def execute_downgrader_online(self): # 함수 이름 변경 (오타 수정)
        self.logger.log("ROLLBACK", "Steam 클라이언트 온라인 다운그레이드 시작 (파일 다운로드 단계)...")

        # 1. Steam 강제 종료 (시작 전 혹시 모를 실행 중인 Steam 종료)
        self._kill_steam_process()
        time.sleep(2) # 종료 후 잠시 대기

        # 2. web.archive.org를 통해 구 버전 파일 다운로드 명령 실행
        wayback_date = self.config.downgrade_wayback_date
        manifest_url_base = f"http://web.archive.org/web/{wayback_date}if_/media.steampowered.com/client"
        
        # Steam 실행 명령어 구성 (구 버전 파일 다운로드 용도)
        # -textmode: GUI 없이 백그라운드에서 업데이트 진행
        # -exitsteam: 업데이트 완료 후 Steam 자동 종료 (매우 중요)
        launch_command_download = [
            f'"{self.steam_exe_path}"',
            "-forcesteamupdate",
            "-forcepackagedownload",
            f"-overridepackageurl {manifest_url_base}",
            "-textmode",
            "-exitsteam", # 다운로드 완료 후 Steam이 스스로 종료되도록 함
            "-clearbeta"
        ]
        
        self.logger.log("ROLLBACK", f"Steam 구 버전 파일 다운로드 실행 중: {' '.join(launch_command_download)}")
        self.logger.log("WARNING", "이 단계에서 Steam이 자동으로 백그라운드에서 실행될 수 있으며, 완료 후 종료됩니다.")
        
        try:
            # subprocess.run을 사용하여 외부 프로세스 실행 및 완료 대기
            # 이 단계에서는 네트워크가 연결되어 있어야 합니다.
            subprocess.run(' '.join(launch_command_download), shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.logger.log("ROLLBACK", "Steam 구 버전 파일 다운로드 프로세스 완료. Steam이 자동 종료되었을 것입니다.")
            time.sleep(5) # 다운로드 프로세스 완료 및 종료 대기 (충분히 대기)

        except subprocess.CalledProcessError as e:
            self.logger.log("ERROR", f"Steam 구 버전 파일 다운로드 실행 실패. Stderr: {e.stderr.strip()}")
            self.logger.log("ERROR", "가이드: 'Steam이 레지스트리 경로 쓰기 불가 다이얼로그를 표시했다면, Repair를 클릭하세요.'")
            self.logger.exit_program()
        except Exception as e:
            self.logger.log("ERROR", f"Steam 구 버전 파일 다운로드 중 예상치 못한 오류 발생: {e}")
            self.logger.exit_program()

        # 3. Steam 강제 종료 (다운로드 후 혹시 모를 잔여 프로세스 정리)
        self._kill_steam_process()
        time.sleep(2) # 종료 후 잠시 대기

        # --- 이 지점에서 사용자에게 네트워크를 끊으라고 명확히 안내하고 대기 ---
        self.logger.log("INFO", "=== 다음 단계 진행 전 수동 작업 필요 ===")
        self.logger.log("WARNING", "지금 바로 가상 머신의 **네트워크 연결을 완전히 차단**하세요!")
        self.logger.log("WARNING", "네트워크 차단 후 이 프롬프트에 **Enter**를 눌러 다음 단계로 진행하세요.")
        input("네트워크 차단 후 Enter를 눌러주세요...") # 사용자 입력 대기

        # 4. steam.cfg 파일 생성 (업데이트 방지)
        self._create_steam_cfg()

        # 5. loginusers.vdf 수정 (오프라인 로그인 강제)
        self._edit_loginusers_vdf_for_offline()

        # 6. 다운그레이드된 Steam 클라이언트 실행 시도 (오프라인 진입 시도)
        self.logger.log("INFO", "다운그레이드된 Steam 클라이언트 실행 시도 중 (오프라인 모드 진입)..")
        # -vgui 옵션을 추가하여 구형 UI 강제 (선택 사항이지만 도움이 될 수 있음)
        final_launch_command = [
            f'"{self.steam_exe_path}"',
            "-vgui" # 구형 UI 강제
        ]
        
        try:
            # subprocess.Popen을 사용하여 Steam을 비동기적으로 실행하고 프로그램은 계속 진행
            # 이 시점에서는 네트워크가 차단되어 있어야 합니다.
            subprocess.Popen(' '.join(final_launch_command), shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.logger.log("OK", "Steam 클라이언트가 실행될 것입니다. 오프라인 모드 진입을 확인하세요.")
            self.logger.log("INFO", "네트워크가 차단된 상태에서 Steam이 성공적으로 실행되었는지 확인하고, SSFN 파일을 통해 로그인 시도해 보세요.")
        except Exception as e:
            self.logger.log("ERROR", f"Steam 클라이언트 실행 실패: {e}")
            self.logger.exit_program()