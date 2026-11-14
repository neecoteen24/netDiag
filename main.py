import json

from modules.network_info import collect_network_info


def main():
    result = collect_network_info()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()