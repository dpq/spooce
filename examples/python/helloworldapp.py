class Helloworld:
    from datetime import datetime

    def main(self, appid = "NO ID PASSED!", arg = {"str" : "Hello"}):
        aaa = 9.0
        for uuu in range(50000000):
            aaa += 76.8
        self.name = appid
        for i in range(2):
            k = 0
            for j in range(10000000):
                k += 1
            dt = self.datetime.now()
            kernel.sendMessage({
                "dst"    : "/%s/%s" % ("testterminal", appid),
                "src"    : self.name,
                "action" : "write",
                "strid"  : str(i),
                "value"  : "the Message value " + str(i)
            })
	
    def mx(self, message):
        print "Me (%s) has got the message :" % self.name
        for k in message:
            print k, ":", message[k]
        return

opt.package["helloworldapp"]["1.0"] = Helloworld
