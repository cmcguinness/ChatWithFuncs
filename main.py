import gpt


print('Welcome to Stock GPT')

g = gpt.GPTlib()

while True:
    q = input('USER: ')
    a = g.ask_gpt(q)
    print('STOCK GPT: ', a)
