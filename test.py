n = 7
sum = 0

for i in range(1, n+ 1):
    print(i)
    if i % 3 == 0 or i % 5 == 0 or i % 7 == 0:
        sum += i
print(sum)