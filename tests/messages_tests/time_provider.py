class TestTimeProvider:
    def __init__(self, act_time=0):
        self.act_time = act_time

    def set_act_time(self, act_time):
        self.act_time = act_time

    def time(self):
        return self.act_time

    def inc_act_time(self):
        self.act_time += 1
