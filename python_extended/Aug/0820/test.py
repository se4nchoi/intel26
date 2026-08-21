# kw = ["제주도", "여행", "맛집"]
# text = input("문장 입력: ")

# for word in kw:
#     text = text.replace(word, f"#{word}")


# print("결과:", text)

#####  5  ####

# weather = ["맑음", "눈", "흐림", "천둥", "비"]
# weather.append("안개")

# weather.remove("천둥")
# print(weather[1:4])

#####  6  ####

# buy_list = input("구매할 물건을 쉼표(,)로 구분하여 입력: ")
# ordered_buy_list = sorted(buy_list.split(","))
# print("정렬된 쇼핑목록: ", ordered_buy_list)


num = 1
while num <= 3:
    print("hello world!")
    num += 1

while True:
    foo = input("문자열 입력 >> ")
    if foo == "종료":
        break
    elif foo == "":
        print("아무것도 입력하지 않았습니다. 다시 입력해주세요.")
        continue
    else:
        print(f"입력된 글자 수는 {len(foo)} 입니다")