from will.plugin import WillPlugin
from will.decorators import respond_to, periodic, hear, randomly, route, rendered_template, require_settings
import cleverbot
import wolframalpha

cb = cleverbot.Cleverbot()
wr = wolframalpha.Client("496EX4-7KQ43EA96A")
class RealChatPlugin(WillPlugin):

    @respond_to("^\-(?P<phrase>.*)$")
    def real_chat_cb(self, message, phrase=None):
        """-.*: I know how to hold a conversation!"""
        print "Responding to cleverbot query"
        try:
            return self.say(cb.ask(phrase), message=message)
        except Exception as e:
            print e
            return self.say("Not able to come up with any real response! (Check logs)", message=message, color='red', alert=True)

    @respond_to("^_(?P<phrase>.*)$")
    def real_chat_wr(self, message, phrase=None):
        """_.*: I know how to be useful"""
        gen_str = ""
        try:
            self.say("Sure, let me think about that.", message=message, color='green')
            query = wr.query(phrase)
            for line in query:
                gen_str += (line.title if line.title != None else "")+"\n"
                gen_str += (line.text if line.text != None else"")+"\n"
                gen_str += " \n"
            if gen_str == "":
                return self.say("/code Couldn't figure out how to respond to that!", message=message, color='red')
            return self.say("/code "+gen_str, message=message, color='green')
        except Exception as e:
            print e
            return self.say("Wasn't able to get any data from that query! (Check logs)", message=message, color='red', alert=True)
