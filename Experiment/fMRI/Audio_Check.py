#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pygame
from pygame.locals import FULLSCREEN, QUIT, KEYDOWN, K_ESCAPE, K_1, K_2, K_3, K_5, K_KP1, K_KP2, K_KP3
from datetime import datetime
import time

# --- Pygame Initialization ---
try:
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(False)
    print(f"pygame {pygame.version.ver} (SDL {pygame.get_sdl_version()})")
    print("Hello from the pygame community. https://www.pygame.org/contribute.html")
except Exception as e:
    print(f"Pygameの初期化に失敗: {e}")
    sys.exit(1)

# ---- File Paths ----
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

AUDIO_CHECK_DIR = os.path.join(SCRIPT_DIR, 'audio_check')
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'static', 'NotoSansJP-Regular.ttf')

print(f"スクリプトディレクトリ: {SCRIPT_DIR}")
print(f"音声チェックディレクトリ: {AUDIO_CHECK_DIR}")

# ---- Global Variables ----
experiment_paused = False
pause_start_time = None

# ---- Audio Files List ----
AUDIO_FILES = [
    'check_1.mp3', 'check_2.mp3', 'check_3.mp3', 'check_4.mp3', 'check_5.mp3',
    'check_6.mp3', 'check_7.mp3', 'check_8.mp3', 'check_9.mp3', 'check_10.mp3',
    'check_11.mp3', 'check_12.mp3', 'check_13.mp3', 'check_14.mp3', 'check_15.mp3'
]

# ---- Logging Function ----
def log_message(message):
    """Logs a message to the console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

# ---- Check for Pause ----
def check_pause():
    """Checks if pause key combination is pressed."""
    global experiment_paused, pause_start_time
    
    keys = pygame.key.get_pressed()
    # Check for Cmd+Shift+Esc
    if (keys[pygame.K_LMETA] or keys[pygame.K_RMETA]) and keys[pygame.K_LSHIFT] and keys[pygame.K_ESCAPE]:
        if not experiment_paused:
            experiment_paused = True
            pause_start_time = time.time()
            log_message("一時停止しました。")
            return True
    return False

# ---- Handle Pause ----
def handle_pause(screen):
    """Handles pause state and waits for resume."""
    global experiment_paused, pause_start_time
    
    if not experiment_paused:
        return
    
    # Display pause message
    screen.fill((0, 0, 0))
    display_text(screen, "一時停止中...\n\n再開するにはCommand+Shift+Escを押してください", font_size=40)
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
        
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_LMETA] or keys[pygame.K_RMETA]) and keys[pygame.K_LSHIFT] and keys[pygame.K_ESCAPE]:
            if experiment_paused:
                pause_duration = time.time() - pause_start_time
                experiment_paused = False
                log_message(f"再開しました。一時停止時間: {pause_duration:.2f}秒")
                screen.fill((0, 0, 0))
                pygame.display.flip()
                pygame.mouse.set_visible(False)
                waiting = False
                pygame.time.wait(500)
        
        pygame.time.wait(50)

# ---- Screen Setup ----
def setup_screen():
    """Sets up the pygame screen in fullscreen mode."""
    try:
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h
        log_message(f"画面解像度: {screen_width}x{screen_height}")
        
        screen = pygame.display.set_mode((screen_width, screen_height), FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)
        pygame.display.set_caption('Audio Level Check')
        return screen
    except pygame.error as e:
        log_message(f"フルスクリーンモード設定エラー: {e}")
        print("フルスクリーンモードの設定に失敗しました。")
        sys.exit(1)

# ---- Text Display Function ----
def display_text(screen, text, y_offset=0, font_size=36, color=(255, 255, 255), line_spacing=1.2):
    """Displays text on screen with center alignment."""
    try:
        if os.path.exists(FONT_PATH):
            font = pygame.font.Font(FONT_PATH, font_size)
        else:
            font = pygame.font.Font(None, font_size)
        
        lines = text.split('\n')
        screen_width, screen_height = screen.get_size()
        
        rendered_lines = []
        for line in lines:
            if line.strip():
                text_surface = font.render(line.strip(), True, color)
                rendered_lines.append(text_surface)
            else:
                rendered_lines.append(None)
        
        line_height = font.get_height()
        total_height = len(rendered_lines) * line_height * line_spacing
        
        start_y = (screen_height - total_height) // 2 + y_offset
        current_y = start_y
        
        for text_surface in rendered_lines:
            if text_surface:
                text_rect = text_surface.get_rect(centerx=screen_width // 2, 
                                                 centery=current_y + line_height // 2)
                screen.blit(text_surface, text_rect)
            current_y += line_height * line_spacing
        
        pygame.display.flip()
    except Exception as e:
        log_message(f"テキスト表示エラー: {e}")

# ---- Get Participant Info ----
def get_participant_info():
    """Gets participant info."""
    print("\n=== 音声レベルチェック (情報入力) ===\n")
    
    participant_id = input("参加者ID (例: 001): ").strip()
    if not participant_id:
        participant_id = "001"
    
    print(f"\n参加者ID: {participant_id}")
    return participant_id

# ---- Show Instructions ----
def show_instructions(screen):
    """Shows experiment instructions."""
    pygame.mouse.set_visible(False)
    
    instruction_text = (
        "音声レベルチェック\n\n"
        "これから英語の文を聞いていただきます。\n\n"
        "各文の後、音量について評価してください：\n\n"
        "1: 小さい\n"
        "2: ちょうどよい\n"
        "3: 大きい\n\n"
        "スピーカーの音量を調整します\n"
        "2回連続で「ちょうどよい」が選ばれたら終了となります"
    )
    
    screen.fill((0, 0, 0))
    display_text(screen, instruction_text, font_size=36)
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_5:
                    waiting = False
    
    screen.fill((0, 0, 0))
    pygame.display.flip()
    return True

# ---- Wait for Scanner Trigger ----
def wait_for_trigger(screen):
    """Waits for scanner trigger (key '5')."""
    pygame.mouse.set_visible(False)
    
    screen.fill((0, 0, 0))
    display_text(screen, "準備中...\n\nお待ちください...", font_size=40)
    
    log_message("トリガー('5')を待機中...")
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    log_message("ESCキーが押されました: 音声チェックを中断します")
                    return False
                elif event.key == K_5:
                    log_message("スキャナートリガー受信")
                    waiting = False
    
    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.event.clear()
    
    return True

# ---- Play Audio and Get Feedback ----
def play_audio_and_get_feedback(screen, audio_file, trial_num, total_trials):
    """Plays audio and gets participant feedback."""
    screen.fill((0, 0, 0))
    
    # Display trial number
    trial_text = f"音声 {trial_num}/{total_trials}"
    display_text(screen, trial_text, y_offset=-200, font_size=32)
    
    # Display "Playing..."
    display_text(screen, "再生中...", y_offset=-50, font_size=40)
    
    # Play audio
    audio_path = os.path.join(AUDIO_CHECK_DIR, audio_file)
    
    if not os.path.exists(audio_path):
        log_message(f"警告: 音声ファイルが見つかりません: {audio_path}")
        return None
    
    try:
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        
        # Wait for audio to finish
        while pygame.mixer.music.get_busy():
            if check_pause():
                pygame.mixer.music.pause()
                handle_pause(screen)
                pygame.mixer.music.unpause()
                # Redraw screen
                screen.fill((0, 0, 0))
                display_text(screen, trial_text, y_offset=-200, font_size=32)
                display_text(screen, "再生中...", y_offset=-50, font_size=40)
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    pygame.mixer.music.stop()
                    return None
            
            pygame.time.wait(10)
        
    except pygame.error as e:
        log_message(f"音声再生エラー: {e}")
        return None
    
    # Display feedback options
    screen.fill((0, 0, 0))
    display_text(screen, trial_text, y_offset=-200, font_size=32)
    display_text(screen, "音量はどうでしたか？", y_offset=-50, font_size=40)
    display_text(screen, "1: 小さい    2: ちょうどよい    3: 大きい", y_offset=50, font_size=36)
    
    # Wait for response
    response = None
    waiting = True
    
    while waiting:
        if check_pause():
            handle_pause(screen)
            # Redraw screen
            screen.fill((0, 0, 0))
            display_text(screen, trial_text, y_offset=-200, font_size=32)
            display_text(screen, "音量はどうでしたか？", y_offset=-50, font_size=40)
            display_text(screen, "1: 小さい    2: ちょうどよい    3: 大きい", y_offset=50, font_size=36)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return None
                elif event.key in [K_1, K_KP1]:
                    response = 1
                    response_text = "小さい"
                elif event.key in [K_2, K_KP2]:
                    response = 2
                    response_text = "ちょうどよい"
                elif event.key in [K_3, K_KP3]:
                    response = 3
                    response_text = "大きい"
                
                if response:
                    # Display confirmation
                    screen.fill((0, 0, 0))
                    display_text(screen, trial_text, y_offset=-200, font_size=32)
                    display_text(screen, f"あなたの選択: {response_text}", y_offset=0, font_size=40, color=(100, 255, 100))
                    pygame.display.flip()
                    pygame.time.wait(1000)
                    waiting = False
        
        pygame.time.wait(10)
    
    return response

# ---- Show End Screen ----
def show_end_screen(screen, interrupted=False):
    """Shows end screen."""
    screen.fill((0, 0, 0))
    
    if interrupted:
        end_text = "音声チェックが中断されました。"
    else:
        end_text = "音声チェック完了\n\nありがとうございました。"
    
    display_text(screen, end_text, font_size=40)
    pygame.display.flip()
    pygame.time.wait(3000)

# ---- Main Function ----
def main():
    """Main function."""
    pygame.mouse.set_visible(False)
    
    # Get participant info
    participant_id = get_participant_info()
    log_message(f"音声レベルチェック開始: Participant {participant_id}")
    
    # Setup screen
    screen = setup_screen()
    
    # Show instructions
    if not show_instructions(screen):
        log_message("指示画面で中断されました。")
        pygame.quit()
        return
    
    # Wait for trigger
    if not wait_for_trigger(screen):
        log_message("トリガー待機中に中断されました。")
        pygame.quit()
        return
    
    # Main loop - play all audio files
    responses = []
    consecutive_good = 0  # 連続で「ちょうどよい(2)」が選ばれた回数
    
    for i, audio_file in enumerate(AUDIO_FILES):
        trial_num = i + 1
        log_message(f"Trial {trial_num}: {audio_file}")

        response = play_audio_and_get_feedback(screen, audio_file, trial_num, len(AUDIO_FILES))

        if response is None:
            log_message("終了です")
            show_end_screen(screen, interrupted=True)
            pygame.quit()
            return

        response_labels = {1: "小さい", 2: "ちょうどよい", 3: "大きい"}
        log_message(f"  Response: {response} ({response_labels[response]})")
        responses.append(response)

        # --- NEW: ちょうどよい(2) が2回連続で選ばれたら終了 ---
        if response == 2:
            consecutive_good += 1
        else:
            consecutive_good = 0

        if consecutive_good >= 2:
            log_message("\"ちょうどよい\"が2回連続で選ばれたため、音声チェックを終了します。")
            break

        # Short pause between trials (only if not breaking)
        if i < len(AUDIO_FILES) - 1:
            screen.fill((0, 0, 0))
            pygame.display.flip()
            pygame.time.wait(500)
    
    # Summary
    count_small = responses.count(1)
    count_good = responses.count(2)
    count_large = responses.count(3)
    
    log_message(f"\n=== 結果サマリー ===")
    log_message(f"小さい: {count_small}回")
    log_message(f"ちょうどよい: {count_good}回")
    log_message(f"大きい: {count_large}回")
    
    # Show end screen
    show_end_screen(screen, interrupted=False)
    
    pygame.quit()
    log_message("音声レベルチェック終了")

# ---- Entry Point ----
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        input("Enterキーを押して終了...")
    finally:
        pygame.quit()

