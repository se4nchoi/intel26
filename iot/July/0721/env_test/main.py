def main():
    print("Hello from env-test!")
    for i in range(0,10):
        for j in range(1,10):
            for k in range(1,11):
                k += i*10
                print(f"{k} x {j} = ", (k)*j, end="\t")
            print("")  
        print("\n")

if __name__ == "__main__":
    main()
