import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--is", nargs="*", default=[])
parser.add_argument("--all-is", action="store_true")
args = parser.parse_args()
if len(args.is) > 0:
    print("is")
elif args.all_is:
    print("all")
else:
    parser.print_help()
