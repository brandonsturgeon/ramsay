from will.plugin import WillPlugin
from will.decorators import respond_to, periodic, hear, randomly, route, rendered_template, require_settings
import requests
import subprocess
import random
import json
import time
import pprint

#AUDIO_URL = "http://192.168.30.145:6868/mopidy/rpc"
#VOLUME_URL = "http://192.168.30.145:6869"
PP = pprint.PrettyPrinter(indent=4)
class PlayMusicPlugin(WillPlugin):
    def send_voice_request(self, say_string):
        use_voice = self.load("use_voice", False)
        if use_voice:
            if type(say_string) is not str:
                return False, "Must pass a string!"
            if say_string is None or say_string == "":
                return False, "Message cannot be empty!"
            subprocess.check_output(["ssh", "-C", "marketops", "say", say_string])
        else:
            return False

    def set_volume_level(self, level):
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.mixer.set_volume", "params": {"volume": %s}}' % str(level))
        result = str(req.json()["result"])
        if result == "True":
            return True
        else:
            PP.pprint(result)
            return False

    def get_volume_level(self):
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.mixer.get_volume"}')
        result = req.json()["result"]
        return int(result)

    @respond_to('say (?P<tosay>.*)$')
    def to_say(self, message, tosay=None):
        """say _____: I know how to talk!"""
        print "I was told to say something"
        self.send_voice_request(str(tosay))

    @respond_to("^(?:what(?:'s|s| is)? (?:(?:this |that )?(?:song|playing(?:(?: right)? now)?))|what song is (?:this|that|playing(?:(?: right now)?(?: now)?)))\??$")
    def return_currently_playing(self, message):
        """what's playing: I know how to find out what's currently playing!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.get_current_track"}')
        if not req.ok:
            self.reply(message, "I wasn't able to see what's playing.", color='red')
        track_name = track_year = artist = artist_uri = album_name = album_year = album_uri = "Unknown"
        try:
            req_json = req.json()
            result = req_json["result"]
            track_name = result["name"]
            track_year = result["date"]
            artist = result["artists"][0]["name"]
            artist_uri = result["artists"][0]["uri"]
            album_name = result["album"]["name"]
            album_year = result["album"]["date"]
            album_uri = result["album"]["uri"]
        except Exception as e:
            print "Unable to get track information"
            print str(e)
        ret_string = """Track Name: %s
Year: %s
Artist: %s
Album: %s
Album Year: %s
Album URI: %s""" % (track_name, track_year, artist, album_name, album_year, album_uri)
        self.say("/quote "+ret_string, message=message)

    @respond_to('^make this my default$')
    def set_my_default(self, message):
        """make this my default: I know how to set a station to be your default!"""
        sender = message.sender["mention_name"]
        self.save(sender+"_default", self.load("currently_playing"))
        self.reply(message, "I set your default station to: "+self.load("currently_playing"))

    @respond_to('^(?:skip|next|nope|no)$')
    def skip_commercial(self, message):
        """skip|next: I know how to skip a song!"""

        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.next"}')
        if not req.ok:
            self.reply(message, "Something went wrong with the skip request")
            print "SKIP REQUEST ERROR:"
            PP.pprint(req.json())
            print ""
            return
        self.reply(message, "Skipping", color="green")
        return

    @respond_to("^(?:previous|last|)$")
    def previous_song(self, message):
        """previous|last: I know how to play the last song!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.previous"}')
        if not req.ok:
            self.reply(message, "Something went wrong with the request")
            print "PREVIOUS REQUEST ERROR:"
            PP.pprint(req.json())
            print ""
            return
        return self.reply(message, "Going back", color="green")


    @respond_to('^pause$')
    def pause_music(self, message):
        """pause: I know how to pause the current music!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.pause"}')
        if not req.ok:
            self.reply(message, "I wasn't able to pause", color='red')
            print("PAUSE ERROR")
            print(req.json())
            return False
        return True
        #rand_reply = random.choice(["Pausing the music", "On it.", "Gotcha", "Just let me know when you want to unpause", "Pausing"])
        #self.reply(message, rand_reply)

    @respond_to('^(?:un|de|dis)pause$')
    def unpause_music(self, message):
        """unpause: I know how to unpause!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.get_state"}')
        if not req.ok:
            self.reply(message, "I couldn't check the current music status", color="red")
        else:
            req_json = req.json()
            PP.pprint(req_json)
            if req_json["result"] == "paused":
                req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.play"}')
                if not req.ok:
                    self.reply(message, "I wasn't able to unpause", color='red')
                    print("PLAY ERROR")
                    print(req.json())
                    return
            elif req_json["result"] == "stopped":
                return self.reply(message, "Nothing to unpause!", color='red')
            elif req_json["result"] == "playing":
                return self.reply(message, "The music isn't paused!")
        #rand_reply = random.choice(["Unpausing the music", "On it.", "Gotcha", "Unpausing"])
        #self.reply(message, rand_reply)

    @hear('^(?:wo+ho+|ya+y+|hurray+|ho+r+a+y+|victory+)!*$')
    def play_victory_sound(self, message):
        """woohoo!: I know how to get excited!"""
        excited_message = random.choice(["Hurray!", "Yay!", "Yeah!", "Huzzah!", "I'm excited too!", "I don't know what we're happy about, but I'm on board!"])
        self.reply(message, excited_message, color="green")
        self.send_voice_request(excited_message)
        script = "beep -f 130 -l 100 -n -f 262 -l 100 -n -f 330 -l 100 -n -f 392 -l 100 -n -f 523 -l 100 -n -f 660 -l 100 -n -f 784 -l 300 -n -f 660 -l 300 -n -f 146 -l 100 -n -f 262 -l 100 -n -f 311 -l 100 -n -f 415 -l 100 -n -f 523 -l 100 -n -f 622 -l 100 -n -f 831 -l 300 -n -f 622 -l 300 -n -f 155 -l 100 -n -f 294 -l 100 -n -f 349 -l 100 -n -f 466 -l 100 -n -f 588 -l 100 -n -f 699 -l 100 -n -f 933 -l 300 -n -f 933 -l 100 -n -f 933 -l 100 -n -f 933 -l 100 -n -f 1047 -l 400".split(" ")
        subprocess.call(script)

    @respond_to('(?:stop|shut off|turn off)(?:(?:\sthe)?\smusic!*(?:\splease)?)?$')
    def stop_the_beat(self, message):
        """stop: I know how to stop the current music"""
        # Stop current playback
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.stop"}')
        if not req.ok:
            return self.reply(message, 'I could not stop the playback', color='red')

        # Clear tracklist
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.clear"}')
        if not req.ok:
            return self.reply(message, 'I could not clear the tracklist', color='red')

        self.save("currently_playing", "Nothing")
        rand_reply = random.choice(["Alright, I'm stopping the music.", "Stopping the music.", "Turning off the music", "Sure thing! Shutting it off now.", "I'm on it.", "All over it.", "right-o"])
        self.reply(message, rand_reply)
        self.send_voice_request(rand_reply)

    @respond_to('shut ?up$|sh+!*$')
    def rude_stop_the_beat(self, message):
        """shut up|shh: I know how to shut up!"""
        # Stop current playback
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.stop"}')
        if not req.ok:
            return self.reply(message, 'Very sorry, but I could not stop the playback', color='red')

        # Clear tracklist
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.clear"}')
        if not req.ok:
            return self.reply(message, 'Sorry to say, I couldn\'t clear the tracklist', color='red')

        self.save("currently_playing", "Nothing")
        rand_reply = random.choice(["Done.", "Got it.", "I'm on it.", "Sure thing."])
        self.reply(message, rand_reply)

    @respond_to('set (?:the )?volume to (?P<volume>[0-9]{1,3})?')
    def set_the_volume(self, message, volume=0):
        """set volume to ___: I know how to set the volume! Limited to 1-100"""
        try:
            vol = int(volume)
        except:
            self.reply(message, 'I wasn\'t able to figure out what you wanted me to set the volume to. Here\'s what I see:', color='red')
            return self.reply(message, '/quote '+str(volume), color='red')
        if not self.set_volume_level(str(vol)):
            return self.reply(message, 'I wasn\'t able to set the volume.', color='red')

        rand_reply = random.choice(["Done.", "Sure thing!", "Gotcha.", "All over it.", "Right-o"])
        self.reply(message, rand_reply)
        self.send_voice_request(rand_reply)

    @respond_to("^mute(?: the(?: music))?.*$")
    def mute_the_music(self, message):
        """mute the music: I know how to mute the music!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.mixer.set_mute", "params": {"mute": true}}')
        result = req.json()["result"]
        if not req.ok or result == "False":
            return self.reply(message, 'I wasn\'t able to mute.', color='red')
        rand_reply = ["Muted.", "I turned the volume off."]
        self.reply(message, random.choice(rand_reply))
        self.send_voice_request(rand_reply)

    @respond_to("^unmute(?: the(?: music))?.*$")
    def unmute_the_music(self, message):
        """unmute the music: I know how to unmute the music!"""
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.mixer.set_mute", "params": {"mute": false}}')
        result = req.json()["result"]
        if not req.ok or result == "False":
            return self.reply(message, 'I wasn\'t able to unmute.', color='red')
        rand_reply = ["Unmuted.", "I turned the volume on."]
        self.reply(message, random.choice(rand_reply))
        self.send_voice_request(rand_reply)

    @respond_to("(?:quiet|quite)(?: (?:mode|down)?(?: please)?)?$")
    def quiet_mode(self, message):
        """quet(mode|down) I can enable Quiet Mode if you're talking or something!"""
        if not self.set_volume_level("25"):
            return self.reply(message, 'I wasn\'t able to set the volume.', color='red')
        rand_reply = ["Volume down.", "Quiet mode engaged.", "Alright, I turned it down.", "I set the volume to 25/100"]
        self.reply(message, random.choice(rand_reply))
        self.send_voice_request(rand_reply)

    @respond_to("(?:turn it down|(?:it's |that's |this is )?too loud)$")
    def turn_it_down(self, message):
        """turn it down|too loud: I know how to turn down my volume!"""
        min_reached = False
        current_volume = self.get_volume_level()
        if not current_volume:
            return self.reply(message, 'I wasn\'t able to get the volume.', color='red')
        else:
            target_volume = int(current_volume) - 30
            if target_volume <= 0:
                min_reached = True
                target_volume = 1
            if not self.set_volume_level(str(target_volume)):
                return self.reply(message, 'I wasn\'t able to set the volume.', color='red')
        rand_reply = ["I set the music to "+str(target_volume)+"/100", "I turned down the music."]
        reply = random.choice(rand_reply)
        if min_reached:
            reply = reply + " Looking to mute the music? Try the 'mute' command!"
            self.reply(message, reply)
        self.send_voice_request(reply)

    @respond_to("go loud|make some noise$")
    def loud_mode(self, message):
        """go loud|make some noise: I know how to be loud!"""
        if not self.set_volume_level("75"):
            return self.reply(message, 'I wasn\'t able to set the volume.', color='red')
        rand_reply = random.choice(["Loud mode engaged.", "I turned up the music.", "All over it.", "I set the volume to 75/100"])
        self.reply(message, rand_reply)
        self.send_voice_request(rand_reply)

    @respond_to("(?:(?:turn|crank) (?:that(?: \w+\\b)?|this(?: \w+\\b)?|it) up.*$)")
    def turn_it_up(self, message):
        """turn it up: I know how to turn the music up!"""
        current_volume = self.get_volume_level()
        if not current_volume:
            return self.reply(message, 'I wasn\'t able to set the volume.', color='red')
        else:
            target_volume = int(current_volume) + 20
            if target_volume > 100:
                target_volume = 100
            if not self.set_volume_level(str(target_volume)):
                return self.reply(message, 'I wasn\'t able to set the volume.', color='red')

        rand_reply = random.choice(["Nice.", "I turned up the music.", "All over it.", "I set the volume to "+str(target_volume)+"/100"])
        self.reply(message, rand_reply)
        self.send_voice_request(rand_reply)

    @respond_to("^(?:turn |set )?repeat (?P<option>.*)$")
    def set_repeat(self, message, option=None):
        """repeat (on|off): I know how repeat the music! Only playlists right now!"""
        # Set repeat
        value = "false"
        if option.lower() in ["enable", "on"]:
            value = "true"
            rand_reply = random.choice(["Turned on repeat", "I turned repeat on", "Repeat enabled", "Repeat turned on"])
        elif option.lower() in ["disable", "off"]:
            value = "false"
            rand_reply = random.choice(["Turned off repeat", "I turned repeat off", "Repeat disabled", "Repeat turned off"])
        else:
            return self.reply(message, "I don't know how to set repeat to: %s" % str(option), color='red')

        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.set_repeat", "params": {"value": %s}}' % value)
        if not req.ok:
            self.reply(message, 'I could not set repeat', color='red')
            return PP.pprint(req.json())
        else:
            self.reply(message, rand_reply, color='green')

    @respond_to("^(?:turn |set )?shuffle (?P<option>.*)$")
    def set_shuffle(self, message, option=None):
        """shuffle (on|off): I know how to shuffle the music!"""
        # Set shuffle
        value = "false"
        if option.lower() in ["enable", "on"]:
            value = "true"
            rand_reply = random.choice(["Turned on shuffle", "I turned shuffle on", "Shuffle enabled", "Shuffle turned on"])
        elif option.lower() in ["disable", "off"]:
            value = "false"
            rand_reply = random.choice(["Turned off shuffle", "I turned shuffle off", "Shuffle disabled", "Shuffle turned off"])
        else:
            return self.reply(message, "I don't know how to set shuffle to: %s" % str(option), color='red')

        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.set_random", "params": {"value": %s}}' % value)
        if not req.ok:
            self.reply(message, 'I could not turn on shuffle', color='red')
            return PP.pprint(req.json())
        else:
            self.reply(message, rand_reply, color='green')

    @respond_to('^play (?P<url>.*)$')
    def play_the_beat(self, message, url=None):
        """play (____): I know how to play music! I accept direct stream links, YouTube links, and SoundCloud links!"""
        if url.lower() in ["previous", "last"]:
            return self.previous_song(message)

        # Stop current playback
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.stop"}')
        if not req.ok:
            return self.reply(message, 'I could not stop the playback', color='red')

        # Clear tracklist
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.clear"}')
        if not req.ok:
            return self.reply(message, 'I could not clear the tracklist', color='red')

        # Translate real words into genre
        real_words = {
            "90s" : ["90s", "some 90s", "stuff from the 90s", "1990s"],
            "mix" : ["mix", "a mix", "a mixtape"],
            "jazz" : ["jazz", "some jazz", "smooth jazz", "some smooth jazz", "a bit of jazz", "a bit of smooth jazz"],
            'country' : ["country", "some country", "country music", "some country music", "bad music", "some bad music"],
            'alternative' : ["alternative"],
            'oldies' : ["oldies"],
            '80s' : ["80s", "some 80s", "some 80s music"],
            'classic rock' : ["classic rock", "rock"],
            'hits' : ["hits"],
            'chill' : ["chill", "ambient", "relaxed", "relaxing"],
            'dubstep' : ["dubstep", "wubs", "wubwub"],
            'pop' : ["kissfm", "top40", "pop"],
            'classical' : ["classical", "classical music"],
            'folk' : ["folk"],
            'motivational' : ["motivation", "motivational", "pumped"],
            'deathmetal' : ["death metal", "deathmetal"],
            'alex' : ['alex', 'alexander', 'cylon']
        }
        # Turn genre into list of urls
        play_lists = {
            "90s": ['spotify:user:spotify:playlist:7iiRP3LZPuuoE4dBWWufkw'],
            "mix": ['http://www.977music.com/itunes/mix.pls'],
            "jazz": ['http://www.977music.com/itunes/jazz.pls'],
            "country": ['http://www.977music.com/977hicountry.pls'],
            "alternative": ['spotify:user:spotify:playlist:2YoVrFsJPvunjHQYfM12cP', 'spotify:user:spotify:playlist:4wtLaWQcPct5tlAWTxqjMD', 'spotify:user:spotify:playlist:2ikvjqFDwalfKdCHkxn79O'],
            "oldies": ['http://www.977music.com/itunes/oldies.pls'],
            "80s": ['http://www.977music.com/itunes/80s.pls'],
            "classic rock": ['spotify:user:spotify:playlist:2Qi8yAzfj1KavAhWz1gaem'],
            "hits": ['http://www.977music.com/itunes/hitz.pls'],
            "chill": ['spotify:user:kent1337:playlist:6IjDl5eRczFdgZkKYXhuHZ'],
            "pop": ['spotify:user:spotify:playlist:5FJXhjdILmRA2z5bvz4nzf'],
            "classical": ['spotify:user:spotify:playlist:1Wci2mmHVAwLLxV4cVrhNl', 'spotify:user:ulyssestone:playlist:1sK57sqzJaO2ZxilXD2KRw'],
            "folk": ['http://www.wumb.org/listenlive/wumbfast.pls'],
            "dubstep": ['spotify:user:spotify:playlist:6iFNvTHtyKvexTwEpEZwl7'],
            "motivational": ['https://www.youtube.com/playlist?list=PL6B7A4215096A229E'],
            "deathmetal": ['spotify:user:beengan:playlist:6tOAPmQEwcp9n3KOFYVIzq'],
            "alex": ["spotify:user:spennythug:playlist:2lqKhlY56sMqvZZkI9U4YR"]
        }

        # TODO: this logic is really icky and needs to be looked at again
        # If no URL is given, or the link given is an ambiguous string
        if url is None or url.lower() in ["something", "anything", "music", "tunes", "a music", "a tunes", "some music", "some tunes", "something else", "random"]:
            url = random.choice(random.choice(play_lists.values()))
        elif url.lower() in ["default", "my default"]:
            sender = message.sender["mention_name"]
            if self.load(sender+"_default", None):
                url = self.load(sender+"_default", None)
            else:
                self.reply(message, "You don't currently have a default channel set! Playing something random.")
                url = random.choice(random.choice(play_lists.values()))
        else:
            # If it's not a link given
            if "gmusic" not in url and "spotify:" not in url:
                if ".com" not in url:
                    genre = None
                    select_from = None

                    url_split = url.split(" ")

                    # One-liner dream..
                    #scores = {k: sum([i in list(set([j for x in [item.split(" ") for item in v] for j in x])) for i in url_split]) for k,v in real_words.items()}
                    scores = {}

                    # Loops through the real_words dict and gets the proper genre for what was said
                    for music_genre,words in real_words.items():
                        # If the url is found exactly in words, call it a match
                        if url in words or url == music_genre:
                            print "URL: "+str(url)
                            print "words: "+str(words)
                            print "music_genre: "+str(music_genre)
                            genre = music_genre
                            break
                        # Split all elements in words by spaces
                        split_words = [i.split(" ") for i in words]
                        # Turn them into 1 list
                        joined_words = [word for i in split_words for word in i]
                        # Give it a numerical score based on how many matching words there are
                        scores[music_genre] = sum([i in joined_words for i in url_split])
                    if genre is None:
                        # Sorts the values from least to greatest, get the last element(the greatest)
                        greatest_score = max(scores.values())

                        # Gets a list of music genres which match the greatest_score
                        possibilities = []
                        for music_genre, score in scores.items():
                            if score == greatest_score:
                                possibilities.append(music_genre)

                        # If we only have one match, play that
                        if len(possibilities) == 1:
                            genre = possibilities[0]
                        # Otherwise alert the user and play one randomly TODO: Maybe it should just error out here?
                        else:
                            self.reply(message, "I found multiple genres that could match what you're looking for. Playing one at random from: "+str(tuple(possibilities)), color='yellow')
                            genre = random.choice(possibilities)


                    # Randomly play something if we couldn't find a genre
                    #else:
                    #   self.reply(message, "I couldn't understand what you asked for, so I'll play something random.")
                        #	url = random.choice(random.choice(play_lists.values()))

                    # Randomly select a url to play for the given genre
                    if genre is not None:
                        select_from = play_lists.get(genre, None)
                    if select_from is not None:
                        url = random.choice(select_from)
                    # Shouldn't ever get here. If real_words has a key that play_lists doesn't
                    else:
                        self.reply(message, "I couldn't understand what you asked for, so I'll play something random.")
                        url = random.choice(random.choice(play_lists.values()))
            if 'youtube.com' in url and "yt:" not in url:
                # If is a youtube link add the prefix
                url = 'yt:%s' % url
            elif 'soundcloud.com' in url:
                # If is a soundcloud link add the prefix
                url = 'sc:%s' % url

        # Add new stream
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.tracklist.add", "params": {"tracks": null, "at_position": null, "uri": null, "uris": ["%s"]}}' % url)
        if not req.ok:
            return self.reply(message, 'I could not add the stream', color='red')
        try:
            track_name = req.json()['result'][0]['track'].get('name', url)
            track_name = track_name.replace("yt:", "")
            track_name = track_name.replace("sc:", "")
            track_name = track_name.replace("gmusic:", "")
            # Do some stuff here if it's an obfuscated Spotify URL or something like that
        except:
            track_name = str(url)

        # Play the beat
        req = requests.post(AUDIO_URL, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.play"}')
        if req.ok:
            return self.reply(message, '%s will be playing for you %s' % (track_name, message.sender.nick.title()))
        else:
            return self.reply(message, 'I could not play %s' % (track_name), color='red', alert=True)

