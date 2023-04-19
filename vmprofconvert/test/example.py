def function_a():
    for i in range(1000000):
        1
    
def function_b():
    function_a()
    function_a()

function_b()