import os, sys
os.environ['PROJECT_MODE'] = 'ELEKTRIFIKASI'
if '--ta' not in sys.argv: sys.argv.append('--ta')
cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path: sys.path.insert(0, cur_dir)
from run_ta_scraper import run_platform

if __name__ == '__main__':
    run_platform('threads')
