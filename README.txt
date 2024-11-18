Missing 2 test cases, I know the problem with test_ret2 is with returning a nil for values of 
int, string, and bool, but I couldn't find a way to fix it without affecting a large majority
of my other cases. I considered changing the values in the returns so I can differentiate
an empty return vs a nil return but I realized it caused a big issue with main when main had
a different type other than void and would cause for error when nothing was returned