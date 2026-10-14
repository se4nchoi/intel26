import argparse

parser = argparse.ArgumentParser(description='사각형 면적 구하는 스크립트')
parser.add_argument('-W', '--width', type=int, help='사각형의 넓이')
parser.add_argument('-H', '--height', type=int, help='사각형의 높이')
args = parser.parse_args()

if __name__ == "__main__":
    print(f"가로 {args.width}, 세로 {args.height}인 사각형의 넓이는 {args.width * args.height}입니다.")