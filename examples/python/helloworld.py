class Helloworld:
    from datetime import datetime

    def main(self, appid = "NO ID PASSED!", arg = {"str" : "Hello"}):
        self.name = appid
        for i in range(2):
            k = 0
            for j in range(1000000):
                k += 1
            dt = self.datetime.now()
            kernel.sendMessage({
                "dst"    : "/%s/%s" % ("mytid", appid),
                "src"    : self.name,
                "action" : "write",
                "strid"  : str(i),
                "value"  : "by Werochka <3 " + str(i)
            })
	
    def mx(self, message):
        print "Me (%s) has got the message :" % self.name
        for k in message:
            print k, ":", message[k]
        return

opt.package["helloworld"]["1"] = Helloworld
