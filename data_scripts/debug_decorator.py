# Decorator for debugging. Put @dum_args on the line before any
# function definition to print out the arguments that have been
# passed to it

def dump_args(func):
    # The wrapper accepts any arguments
    def a_wrapper_accepting_arbitrary_arguments(*args, **kwargs):
        print ('Does '+func.__name__+' have args?:')
        print (args)
        print (kwargs)
        func(*args, **kwargs)
    return a_wrapper_accepting_arbitrary_arguments
