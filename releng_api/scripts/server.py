import argparse
from releng_api import create_app

def main():
    parser = argparse.ArgumentParser(description="run a dev instance of releng_api")
    parser.add_argument("-a", "--all-interfaces", action='store_true',
                        help='Run on all interfaces, not just localhost')
    parser.add_argument("--no-debug", action='store_true',
                        help="Don't run in debug mode")
    args = parser.parse_args()

    kwargs = {}
    if args.all_interfaces:
        kwargs['host'] = '0.0.0.0'
    kwargs['debug'] = not args.no_debug

    create_app().run(**kwargs)
