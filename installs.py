class Suite(object):
    def __init__(self, parser):
        self.packages = parser.correct_freezed()
        print('Created suite', self.__dict__)



def install_from_scratch(parser):
    print('Will install all the things!')
    incorrect_freezes, freezed_notinstalled = parser.get_unresolved_requirements()
    # 10 create suite from current freezes
    suite = Suite(parser)
    # 20 delete incorrect freezes and delete all incorrect freezes deps suite.
    # 30 find versions of missed packages and install them with --no-deps
    # 40 look to the deps and install deps
    # 50 goto 30



def install_by_freeze(parser):
    incorrect_freezes, freezed_notinstalled = parser.get_unresolved_requirements()
    for dep in freezed_notinstalled:
        install_package(dep) # with --no-deps