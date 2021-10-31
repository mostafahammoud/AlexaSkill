import requests
from alexa import Alexa
import json
alexa = Alexa("Hello World")  # Setup a object for the Alexa class
response = alexa.response  # Use the Alexa response attribute to return responses

def getAlexaLocation():

    # Found this online but it requires Flask-ask and I was unable to install flask-ask on windows
    """
    URL =  "https://api.amazonalexa.com/v1/devices/{}/settings" \
           "/address".format(context.System.device.deviceId)
    TOKEN =  context.System.user.permissions.consentToken

    HEADER = {'Accept': 'application/json',
             'Authorization': 'Bearer {}'.format(TOKEN)}
    r = requests.get(URL, headers=HEADER)
    if r.status_code == 200:
        return(r.json())
    """
    location = response.session.get_user_location()
    
def getAlexaCity():
 
    location = getAlexaLocation()
    
    city = "Your City is {}! ".format(location["city"].encode("utf-8"))
    
    return location
