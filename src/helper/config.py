import yaml
from yaml import SafeLoader
import os
from src.steam.reg import SteamReg

class Config():
    def __init__(self):
        try:
            with open("config.yaml", "r", encoding='utf-8') as file:
                self.config = yaml.load(file, Loader=SafeLoader)

            self.build_version: str = "1.5"
            self.username: str = self.config["username"]

            # --- Steam 경로 자동 감지 로직 ---
            self.steam_reg = SteamReg()
            detected_steam_path = None # 이 변수는 임시로 사용하며, 없으면 None으로 설정
            try:
                detected_steam_path = self.steam_reg.get_steam_path()
                if detected_steam_path and not os.path.isdir(detected_steam_path):
                    detected_steam_path = None # 유효하지 않은 경로면 None으로 처리
            except Exception:
                pass # 레지스트리에서 찾지 못하거나 오류 발생 시 무시

            if detected_steam_path:
                self.steam_path = detected_steam_path
            else:
                print(f"경고: Steam 경로를 자동으로 감지하지 못했습니다.")
                print("config.yaml 파일의 'steam_path'에 Steam 설치 경로를 수동으로 입력하거나, 레지스트리 설정을 확인하세요.")
                
                self.steam_path = self.config.get("steam_path") # config.yaml에서 폴백
                if not self.steam_path or not os.path.isdir(self.steam_path):
                    raise ValueError("config.yaml에서도 유효한 Steam 경로를 찾을 수 없습니다. 경로를 설정해주세요.")

            self.downgrade_wayback_date: str = self.config["downgrade_wayback_date"] # config.yaml에서 날짜를 읽어옵니다.

            # self.rollback_path: str = self.config["rollback_path"]
            # self.rollback_exe_path: str = self.config["rollback_exe_path"]
            # self.github_url: str = self.config["github_url"]
            # self.version_github_url: str = self.config["version_github_url"]
            # self.steam_rollback_url: str = self.config["steam_rollback_url"]

        except FileNotFoundError:
            print("ERROR: config.yaml 파일을 찾을 수 없습니다. 프로젝트 루트 폴더에 있는지 확인하세요.")
            exit()
        except KeyError as e:
            print(f"ERROR: config.yaml 파일에 필수 키가 누락되었습니다: {e}. 파일을 확인하세요.")
            exit()
        except ValueError as e:
            print(f"CRITICAL ERROR: {e}")
            exit()
        except Exception as e:
            print(f"ERROR: config.yaml 로드 또는 Steam 경로 감지 중 오류 발생: {e}")
            exit()

    def get_steam_path(self) -> str:
        return self.steam_path