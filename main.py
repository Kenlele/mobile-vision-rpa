"""
main.py
Mobile Vision RPA Framework Entry Point (iOS Automation).
Automatically launches the iOS Simulator window and interactively prompts the user for test instructions.
"""

import sys
import os
import argparse
import logging

# Ensure project root directory is in Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)


def _auto_switch_venv():
    """Auto-detect project virtual environment and switch to it if needed."""
    venv_python = os.path.join(script_dir, "venv", "bin", "python")

    if os.path.exists(venv_python) and "PYTHON_REEXEC" not in os.environ:
        real_current_executable = os.path.realpath(sys.executable)
        real_venv_executable = os.path.realpath(venv_python)

        if real_current_executable != real_venv_executable:
            os.environ["PYTHON_REEXEC"] = "1"
            try:
                os.execv(venv_python, [venv_python] + sys.argv)
            except Exception:
                pass


_auto_switch_venv()

try:
    from core.runner import FrameworkRunner
except ModuleNotFoundError as e:
    sys.stderr.write(f"\n❌ [Error] 缺少必要的 Python 套件: {e}\n")
    sys.stderr.write("請執行以下命令以安裝與啟動虛擬環境：\n")
    sys.stderr.write("  source venv/bin/activate\n")
    sys.stderr.write("  pip install -r requirements.txt\n\n")
    sys.exit(1)



def setup_logging(verbose: bool = False):
    """Configure logging format and output level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def parse_args():
    """Parse runtime options."""
    parser = argparse.ArgumentParser(description="Mobile Vision RPA (iOS Automation)")
    parser.add_argument("--prompt", "--goal", dest="prompt", type=str, default="",
                        help="Optional single task prompt. If omitted, starts interactive prompt mode.")
    parser.add_argument("--driver", choices=["ios", "mirroring", "mock"], default=None,
                        help="Target device driver mode (default: from config.ini)")

    parser.add_argument("--udid", type=str, default=None,
                        help="iOS Simulator UDID or 'booted' (default: from config.ini)")
    parser.add_argument("--max-steps", type=int, default=None,
                        help="Maximum agent execution steps (default: from config.ini)")
    parser.add_argument("--provider", choices=["gemini", "openai", "ollama", "mock"], default=None,
                        help="Vision LLM provider (default: from config.ini)")


    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose debug logging")
    return parser.parse_args()


def main():
    """Main execution loop: launches simulator and waits for user prompt input."""
    args = parse_args()
    setup_logging(args.verbose)

    print("\n==================================================")
    print("   📱 Mobile Vision RPA (iOS Automation Test)")
    print("==================================================")

    # Instantiate runner (automatically opens iOS Simulator window)
    runner = FrameworkRunner(
        driver_mode=args.driver,
        udid=args.udid,
        provider=args.provider
    )

    max_steps = args.max_steps or 5

    # Case 1: Prompt provided directly via command line flag -> Execute initial task & keep session open
    if args.prompt:
        runner.execute(prompt=args.prompt, max_steps=max_steps)
        print("\n[連線持續中] 任務完成！您可以繼續在下方輸入下一個測試指令。")
        print("(輸入 'exit', 'quit', 'q', '結束' 或 '離開' 可結束程序)\n")

    # Continuous Interactive Prompt mode loop (stays open until user explicitly says exit/結束)
    while True:
        try:
            prompt_input = input("👉 請輸入下一個 Prompt 指示: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 結束自動化測試程序。")
            break

        if not prompt_input:
            continue

        if prompt_input.lower() in ["exit", "quit", "q", "結束", "離開"]:
            print("👋 離開自動化測試程式。")
            break

        runner.execute(prompt=prompt_input, max_steps=max_steps)





if __name__ == "__main__":
    main()
