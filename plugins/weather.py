from will.plugin import WillPlugin
from will.decorators import respond_to, periodic, hear, randomly, route, rendered_template, require_settings
from will import settings
from geopy.geocoders import Nominatim
from datetime import datetime
import requests
import os
import subprocess
import forecastio
import random
FORECAST_APU_JEY = "5825cd12ed3069a9481a10659ca10554"
LINCOLN_LAT = 40.825763
LINCOLN_LNG = -96.685198
VOLUME_URL = "http://192.168.30.145:6869"

class ForecastPlugin(WillPlugin):
    def send_voice_request(self, say_string):
        use_voice = self.load("use_voice", False)
        if use_voice is True:
            if type(say_string) is not str:
                print "Must pass a string!"
                return False
            if say_string is None or say_string == "":
                print "Message cannot be empty!"
                return False
            subprocess.check_output(["ssh", "-C", "marketops", "say", say_string])
        else:
            return False

    @route("/weather/temperature")
    def http_temperature(self):
        self.current_temp_will()
        return self.load("local_temp", "Unknown")

    @respond_to("^what(?:'?s| is) the temp(?:erature)?\??(?:(?: in| for)(?P<location>.*)/??)?$")
    def current_temp_will(self, message=None, location=None):
        """what's the temperature (in _______): I know how to tell you the temperature!"""
        geolocator = Nominatim()
        if location is None:
            forecast = forecastio.load_forecast(FORECAST_API_KEY, LINCOLN_LAT, LINCOLN_LNG, units="us")
            currently = forecast.currently()
            temp = currently.temperature
            feels_like = currently.apparentTemperature
            combined = "It's currently %sF and feels like %sF here in Lincoln, NE" % (temp, feels_like)

            self.save("local_temp", combined)

            if message:
                return self.say(combined, message=message)
        else:
            geolocation = geolocator.geocode(location)
            lat = geolocation.latitude
            lng = geolocation.longitude

            forecast = forecastio.load_forecast(FORECAST_API_KEY, lat, lng, units="us")
            currently = forecast.currently()
            temp = currently.temperature
            feels_like = currently.apparentTemperature
            full_address = geolocation.address
            combined = "It's currently %s degrees and feels like %s degrees in %s" % (temp, feels_like, full_address)

            self.save(full_address+"_temp", combined)

            if message:
                self.say(combined, message=message)

    @respond_to("^weather alerts off$")
    def weather_alerts_off(self, message):
        self.save("check_weather_alerts", False)
        self.reply(message, "Not going to check for weather alerts anymore", notify=False)

    @respond_to("^weather alerts on$")
    def weather_alerts_on(self, message):
        self.save("check_weather_alerts", True)
        self.reply(message, "Going to check for weather alerts again", notify=False)

    @respond_to("^weather alerts")
    def force_check_weather(self, message):
        """weather alerts: I can manually check for weather alerts! (I already check every half hour)"""
        self.weather_alerts(True)

    @periodic(minute='30,0')
    def weather_alerts(self, forced=False):
        if not forced:
            if self.load("check_weather_alerts", False) is False:
                return False

        print "Checking for severe weather alerts"
        current_alerts = self.load("current_alerts", {})
        forecast = forecastio.load_forecast(FORECAST_API_KEY, LINCOLN_LAT, LINCOLN_LNG, units="us")
        has_alerted = False
        alerts = forecast.alerts()
        if alerts:
            for alert in alerts:
                if str(alert.uri) not in current_alerts.keys():
                    if not has_alerted:
                        self.say("Severe Weather Alert(s) have been detected.", room=self.available_rooms["Random"], color='red', alert=True)
                    alert_say = "Title: %s"\
                                "Expires: %s"\
                                "Description: %s"\
                                "More Information: %s" % (alert.title, alert.expires, alert.description, str(alert.uri))
                    current_alerts[str(alert.uri)] = alert.expires
                    self.say("/code "+alert_say, room=self.available_rooms["Random"], color='red', notify=True)
                else:
                    if current_alerts[str(alert.uri)] > time.time():
                        del current_alerts[str(alert.uri)]
                        self.save("current_alerts", current_alerts)

    @periodic(hour="6")
    def morning_weather_report(self, message=None):
        """I can give you summary for today"""
        forecast = forecastio.load_forecast(FORECAST_API_KEY, LINCOLN_LAT, LINCOLN_LNG, units="us")
        hourly = forecast.hourly().data
        day = forecast.daily().data[0]
        condition_summary = forecast.hourly().summary
        ## Temperature Data
        temperature_conditions = {
            85: ["hot", "ridiculously hot", "too hot", "very warm"],
            70: ["warm", "decent"],
            60: ["pleasant", "moderate", "temperate"],
            50: ["cool", "temperate", "moderate", "on the cooler side"],
            40: ["cool", "chilly", "a bit chilly", "a bit cool"],
            30: ["cold"],
            20: ["frigid", "very cold", "ridiculously cold", "extra cold"]
        }
        temps = {}
        for point in hourly[0:12]:
            temps[point.temperature] = point.time

        # Average Temperature
        avg_temperature = round(sum(temps.keys())/len(temps.keys()))
        for temp in sorted(temperature_conditions.keys()):
            if avg_temperature <= temp:
                temperature_avg = "It's going to be "+str(random.choice(temperature_conditions[temp]))+" today"
                break
        # Lowest Temperature
        min_temp = min(temps.keys())
        min_temp_message = "Low of "+str(round(min_temp))+" around "+str(temps[min_temp].strftime("%I:%M %p"))
        # Highest Temperature
        max_temp = max(temps.keys())
        max_temp_message = "High of "+str(round(max_temp))+" around "+str(temps[max_temp].strftime("%I:%M %p"))

        ## Precipitation Data
        rain_conditions = {
            100: ["it is definitely going to rain", "it is for sure going to rain", "it is assured to rain", "you'll need an umbrella"],
            75: ["it most likely going to rain", "it is likely going to rain", "it is very likely to rain", "you'll probably need an umbrella"],
            50: ["it may rain", "it might rain", "rain is possible", "rain is a possibility", "you may need an umbrella"],
            25: ["rain is unlikely", "rain is possible, but unlikely", "it probably won't rain", "you probably don't need an umbrella"],
            10: ["rain is very unlikely", "it's very unlikely to rain", "it probably won't rain", "we probably won't see any rain today", "you likely don't need your umbrella"]
        }
        snow_conditions = {
            100: ["it is definitely going to snow", "it is 100% going to snow", "it is assured to snow", "you'll need a coat"],
            75: ["it most likely going to snow", "it is likely going to snow", "it is very likely to snow"],
            50: ["it may snow", "it might snow", "snow is possible", "snow is a possibility"],
            25: ["snow is unlikely", "snow is possible, but unlikely", "it probably won't snow"],
            10: ["snow is very unlikely", "it's very unlikely to snow", "it probably won't snow", "we probably won't see any snow today"]
        }

        precips = {}
        precip_type = "precipitation"
        for point in hourly[0:12]:
            precips[round(float(point.precipProbability)*100)] = point.time
            if point.precipProbability > 0:
                precip_type = point.precipType

        # Highest Rain Chance
        max_precip = max(precips.keys())
        max_precip_message = "Precipitation data unknown."
        percent_chance = "% chance of "+precip_type
        # If there's a chance of precip, include the time
        if int(max_precip) > 0:
            percent_chance = "% chance of "+precip_type+" at "+str(precips[max_precip].strftime("%I:%M %p"))

        # This whole section is pretty poorly written #

        to_iter = None
        # If precipitation type is rain, set to loop over rain phrases
        if precip_type == "rain":
            to_iter = rain_conditions.keys()
        # If precipitation type is snow, set to loop over snow phrases
        elif precip_type == "snow":
            to_iter = snow_conditions.keys()
        if to_iter:
            for precip in sorted(to_iter):
                if int(max_precip) <= int(precip):
                    max_precip_message = random.choice(rain_conditions[precip]).capitalize()+". ("+str(round(max_precip))+percent_chance+")"
                    break
        else:
            max_precip_message = str(round(max_precip))+percent_chance

        # Wind
        winds = {}
        for point in hourly[0:12]:
            winds[point.windSpeed] = point.time
        avg_wind = sum(winds.keys())/len(winds.keys())
        max_wind = max(winds.keys())
        wind_message = "Average wind speed is "+str(round(avg_wind))+"MPH, with speeds peaking "+str(round(max_wind))+"MPH at "+str(winds[max_wind].strftime("%I:%M %p"))

        # Sunrise / Sunset data
        sunrise = day.sunriseTime
        sunset = day.sunsetTime
        sunrise_message = "Sunrise at "+sunrise.strftime("%I:%M %p")
        sunset_message = "Sunset at "+sunset.strftime("%I:%M %p")

        # Humidity
        humids = {}
        for point in hourly[0:12]:
            humids[float(point.humidity)*100] = point.time

        max_humid = max(humids.keys())
        avg_humid = sum(humids.keys())/len(humids.keys())
        humid_message = "Average humidity is "+str(round(avg_humid))+"%, peaking at "+str(round(max_humid))+"% at "+str(humids[max_humid].strftime("%I:%M %p"))


        # Generate message
        date = datetime.now().strftime("%A %d. %B %Y")
        if not message:
            self.say("Good morning! Here's the daily weather report.", room=self.available_rooms["Random"], color='green', alert=True)
        intro_message = "Weather Summary for "+str(date)
        return_messages = [intro_message, condition_summary, temperature_avg, min_temp_message, max_temp_message, max_precip_message, humid_message, wind_message, sunrise_message, sunset_message]
        return_string = "\n".join(return_messages)
        if message:
            self.say("/quote "+return_string, message=message)
        else:
            self.say("/quote "+return_string, room=self.available_rooms["Random"])

    # Manually calls the morning weather summary
    @respond_to("^(?:what|how)(?:'?s| is) the weather( like)? today\??$")
    def manual_summary(self, message):
        self.morning_weather_report(message=message)

    @respond_to("^(?:what|how)(?:'?s| is) the weather( like)?\??(?:(?: in| for)(?P<location>.*)/??)?$")
    def current_weather_will(self, message, location=None):
        geolocator = Nominatim()
        if location is None:
            forecast = forecastio.load_forecast(FORECAST_API_KEY, LINCOLN_LAT, LINCOLN_LNG, units="us")
        else:
            geolocation = geolocator.geocode(location)
            lat = geolocation.latitude
            lng = geolocation.longitude
            forecast = forecastio.load_forecast(FORECAST_API_KEY, lat, lng, units="us")
        currently = forecast.currently()
        summary = currently.summary
        # Attempts to get the closest storm if applicable
        try:
            nearest_storm = currently.nearestStormDistance
        except:
            nearest_storm = 0

        # If there is a nearby storm, try to get the bearing
        if nearest_storm != 0:
            try:
                nearest_storm_bearing = currently.nearestStormBearing
            except:
                nearest_storm_bearing = "unavailable"
        temp = currently.temperature
        feels_like = currently.apparentTemperature

        # Precipitation chane
        precip_prob = currently.precipProbability
        precip_intensity = currently.precipIntensity
        if precip_intensity != 0:
            precip_type = currently.precipType
        # Gathering windspeed / Windbearing
        wind_speed = currently.windSpeed
        if wind_speed != 0:
            wind_bearing = currently.windBearing

        # This is a terrible way to do this, please refactor in the future #
        try:
            cloud_cover = currently.cloudCover
        except:
            cloud_cover = "Unknown"
        try:
            humidty = currently.humidity
        except:
            humidity = "Unknown"
        try:
            pressure = currently.pressure
        except:
            pressure = "Unknown"
        try:
            visibility = currently.visibility
        except:
            visibility = "Unknown"

        # Returning a report
        return_values = [str(x) for x in [temp, feels_like, precip_prob, precip_intensity, wind_speed, cloud_cover, humidty, pressure, visibility]]
        header_sentence = "Current Conditions: "+currently.summary

        # Include the requested location if present
        if location is not None:
            header_sentence += " in "+geolocation.address
        # Populating structure with data
        return_message = header_sentence+"\n"\
            "Temperature is: "+str(temp)+" degrees\n"\
            "It feels like: "+str(feels_like)+" degrees\n"\
            "There is a "+str(precip_prob*100)+"% chance of precipitation\n"\
            "The wind is currently blowing at "+str(wind_speed)+" MPH\n"\
            "There is currently "+str(cloud_cover*100)+"% cloud cover\n"\
            "Visibilty is at "+str(visibility)+" miles\n"\
            "The pressure is at "+str(pressure)+" millibars\n"
        self.say("/code "+return_message, message=message)
        self.send_voice_request("Here\'s the Weather report you asked for")
