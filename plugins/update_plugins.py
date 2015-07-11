from will.plugin import WillPlugin
from will.decorators import respond_to, periodic, hear, randomly, route, rendered_template, require_settings
import os
import subprocess
import sys
import json

class UpdatePluginsPlugin(WillPlugin):
    def __init__(self):
        is_restarting = self.load("is_restarting", None)
        if is_restarting is not None:
            if is_restarting["room_id"] is not None:
                for name, room in self.available_rooms.items():
                    if room == is_restarting["room_id"]:
                        self.say("Sucessfully restarted!", room=room, color='green')
                        break
            elif is_restarting["hipchat_id"] is not None:
                self.send_direct_message(is_restarting["hipchat_id"], "Sucessfully restarted!", color='green')
            self.save("is_restarting", None)

    def restart(self, message):
        """restart: Restarts will"""
        print message
        print message.sender
        print message["type"]
        room_id = sender_id = None
        if message["type"] == "groupchat":
            room_id = self.get_room_by_jid(message.getMucroom())
        elif message["type"] == "chat":
            sender_id = message.sender["hipchat_id"]
        tosave = {"room_id": room_id, "hipchat_id": sender_id}

        self.say("Attempting a restart!", message=message)
        self.save("is_restarting", tosave)
        os.execl('restart.sh', '')

    @respond_to("update plugins")
    def update_plugins_will(self, message):
        """update plugins: I know how to update my own plugins!"""
        try:
            print "Changing directory"
            os.chdir(os.path.expanduser("~/Devel/Jarvis/plugins"))
            print "Succcess! Resetting git!"
            subprocess.call(["git", "reset", "--hard", "HEAD"])
            print "Success! Pulling from git!"
            subprocess.call(["git", "pull", "origin", "master"])
            print "Success!"
        except Exception as e:
            print "Failed on update plugins!"
            print e
            self.say("Failed to update plugins! Check logs for more information.", message=message, html=False, color="red", notify=True)
            os.chdir(os.path.expanduser("~/Devel/Jarvis/"))
            return
        self.say("Sucessfully pulled Plugins folder.", message=message, html=False, color="green")
        os.chdir(os.path.expanduser("~/Devel/Jarvis/"))
        self.restart(message)
