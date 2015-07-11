from will.plugin import WillPlugin
from will.decorators import respond_to, periodic, hear, randomly, route, rendered_template, require_settings
import random

class VocalControlPlugin(WillPlugin):

    @respond_to("(?:(?:no|stop) talking$|don'?t (?:talk|speak))|(?:(?:turn |set )?voice off|turn off voice|(?:set )?voice disabled?|disable voice)")
    def stop_talking(self, message):
        """stop talking|turn off voice|voice off: I know how to stop speaking!"""
        try:
            self.save("use_voice", False)
        except Exception as e:
            self.reply(message, "I wasn't able to turn my voice off!", color="red", notify=True)
            self.reply(message, "/code "+str(e), color="red", notify=True)
            return
        rand_reply = random.choice(["Alright, I won't talk anymore.", "Turned off my voice.", "I won't talk anymore.", "I won't say a thing.", "Voice Disabled."])
        self.reply(message, rand_reply, color="green")

    @respond_to("(?:(?:you (?:can|may) )?(?:talk|speak) (?:again)?|voice (?:enabled?|on)|turn on voice)")
    def start_talking(self, message):
        """you can speak again|turn on voice|voice on: I know how to start speaking!"""
        try:
            self.save("use_voice", True)
        except Exception as e:
            self.reply(message, "I wasn't able to turn my voice on!", color="red", notify=True)
            self.reply(message, "/code "+str(e), color="red", notify=True)
            return
        rand_reply = random.choice(["Okay, I'll talk again.", "Alright, I'll start talking again.", "Voice Enabled.", "Ready to talk!"])
        self.reply(message, rand_reply, color="green")
