"""
THIS FILE WAS COPIED FROM HERE: https://github.com/njsnx/python-alexa/blob/master/alexa/__init__.py
I AM NOT THE OWNER OF THIS CODE
I FACED SOME PROBLEM WHEN TRYING TO PIP INSTALL IT SO I DECIDED TO JUST COPY AND PASTE THE CODE HER FOR TESTING

CHANGES DONE MANUALLY:
-uncommented a few line of code from get_user_location() -> not sure if this is the correct thing to do
"""

import itertools
import json
import random
import re

from datetime import datetime
from functools import partial, wraps

import requests


class Alexa():
    """Alexa Class."""

    def __init__(self, skill=None):
        """Init Method."""
        self.skill = skill  # Skill Name
        self.functions = {}  # Functions Dict, used later to run the appropriate function
        self.session = None  # Session attribute used later
        self.response = Response(skill)  # Response attribute
        self.session_attributes = {}  # Session attributes Dict
        self._intent_mappings = {}  # Intent Slot mappings
        self.request = None  # The original request
        self.launch_func = None  # Which function is associated with the LaunchRequest
        self.end_func = None  # The function associated with the SessionEndRequest

    def route(self, raw, test=False, phrases=False):
        """Route method.

        This methd deals with routing the raw request to the correct function
        It will figure out which function to run based on the requet type
        If it is an intent, it will also deal with mapping slots expected to
        function variables
        """
        self.session = Session(raw)  # Get a session object from the Session class, passing in the raw request
        self.session_attributes = self.session.attributes  # Set the session_attribute attribute to the attributes in the session

        self.request = Request(raw)  # Set the request attribute to a Request object - passing in the raw request

        if phrases:
            self.phrases = self.load_phrases(phrases)
        if test:
            self.session.location = {
                "postalCode": "WC1X 8BZ",
                "city": "London"
            }

        """Route Request."""
        # Depending on the request type, get the correct function
        if self.request.type == 'LaunchRequest':
            return partial(self.launch_func)()  # LaunchRequest Function
        elif self.request.type == 'SessionEndedRequest':
            return partial(self.end_func)()  # SessionEndRequest funciton
        elif self.request.type == 'IntentRequest':  # Intent Function
            self.current_intent = self.request.intent.name
            args = self.map_slots_to_mapping()  # Get the arguments to pass in based on mapping parameter to the decorator
            if args:  # Check if there is any args
                # Return the result of the matched function, passing in the sesison as well as the slot mappings as arguments
                return partial(
                    self.functions[self.current_intent],
                    self.session,
                    **args
                )()
            else:  # If no arguments to map
                # call the matched function with the correct session but no slot -> arguments
                return partial(
                    self.functions[self.current_intent],
                    self.session
                )()

    def assume_intent(self, intent_name):
        self.current_intent = intent_name
        args = self.map_slots_to_mapping()  # Get the arguments to pass in based on mapping parameter to the decorator
        if args:  # Check if there is any args
            # Return the result of the matched function, passing in the sesison as well as the slot mappings as arguments
            return partial(
                self.functions[self.current_intent],
                self.session,
                **args
            )()
        else:  # If no arguments to map
            # call the matched function with the correct session but no slot -> arguments
            return partial(
                self.functions[self.current_intent],
                self.session
            )()

    def map_slots_to_mapping(self):
        """Map slots to arguments.

        Deals with mapping slots to arguments - i.e DEVICE slot mapped to device argument

        """
        args = {}  # Start an empty dict to store arguments

        # Set mappings to the dict of the decorator mapping argumnet
        mappings = self._intent_mappings[self.current_intent]
        print(mappings)
        # Check there is a mapping value and that there is at least 1 key to work with
        if mappings is not None:

            # If there is, loop through them
            for to, fr in self._intent_mappings[self.current_intent].items():

                if type(fr) is str:
                    from_name = fr
                else:
                    from_name = fr['name']

                if self.request.slots and from_name in self.request.slots.keys():  # Check if the current slot has a mapping
                    # Add a key to the args dict setting it to the value of the slot
                    args[to] = self.request.slots[from_name]
                else:
                    args[to] = Slot({'name': to, 'value': None})  # If there isn't a value for that slot, set it to None

        return args  # Return the args dict

    # Define the launch functiond decorator
    def launch(self, f):
        """Launch Intent."""
        self.launch_func = f  # Set the launch function attribute to be the function using this decorator

        @wraps(f)  # Set up wrapper so that the function passed in is callable with the arguments later
        def wrapper(*args, **kwargs):
            f()
        return f  # Return the wrapped function

    # Define the session end decorator function
    def session_end(self, f):
        """Launch Intent."""
        self.end_func = f

        @wraps(f)  # Set up wrapper so that the function passed in is callable with the arguments later
        def wrapper(*args, **kwargs):
            f()
        return f  # Return the wrapped function

    # Define the intent decorator function, with mapping attribute argument
    def intent(self, name, mapping=None):
        """Intent method."""
        def decorator(f):

            self.functions[name] = f
            self._intent_mappings[name] = mapping

            @wraps(f)
            def wrapper(*args, **kwds):
                return f()

        return decorator  # Retrun wrapped function.

    def load_utterances(self, file=None, flat=False):

        with open(file) as ut:
            utterances = json.load(ut)

        utterances = self.generate_utterances(utterances)

        if flat:
            to_return = ""
            for intent, phrases in utterances.items():

                for k, utterances in phrases.items():
                    # print k, utterances
                    for utterance in utterances:
                        # for phrase in phrases
                        to_return += "{} {}\n".format(intent, utterance)
            return to_return
        return utterances

    def generate_utterances(self, utterances):

        p = re.compile("\[([^\]]+)\]")

        completed_utterances = {}

        for intent, phrases in utterances.items():
            completed_utterances[intent] = {}
            for i, phrase in enumerate(phrases):
                completed_utterances[intent]["phrase{}".format(i)] = []
                phrase_dict = {}
                x = 0
                for m in p.finditer(phrase):
                    phrase_dict["match{}".format(x)] = {
                        "match": m.group(),
                        "options": []
                    }
                    phrase = phrase.replace(
                        m.group(), "((match" + str(x) + "))"
                    )

                    phrase_dict["match{}".format(x)] = m.group()[1:-1].split(
                        ','
                    )

                    x += 1
                lsources = re.findall("\(\((.*?)\)\)", phrase)
                ldests = []
                for source in lsources:
                    ldests.append(phrase_dict[source])

                # for lproduct in itertools.product(*ldests):
                #     output = phrase
                #     for src, dest in itertools.izip(lsources, lproduct):
                #         output = output.replace("((%s))" % src, dest)

                #     completed_utterances[intent]["phrase{}".format(i)].append(
                #         output
                #     )

        return completed_utterances

    def generate_skill_config(self):

        message = "INTENT SCHEMA\n"
        message += json.dumps(self.get_intents(), indent=2)
        message += "\n\nUTTERANCES\n"
        message += self.load_utterances('./utterances.json', flat=True)

        return message

    def get_intents(self):
        map = {
            "intents": []
        }

        for intent_name, mappings in self._intent_mappings.items():

            intent_map = {
                "intent": intent_name
            }
            if self._intent_mappings[intent_name]:
                intent_map['slots'] = []

                for var, slot in mappings.items():

                    if type(slot) is str:
                        slot_name = slot
                        slot_type = "SLOT_TYPE_NOT_SET"
                    else:
                        slot_name = slot['name']
                        slot_type = slot['type']

                    intent_map['slots'].append(
                        {
                            "name": slot_name,
                            "type": slot_type

                        }
                    )
            map['intents'].append(intent_map)
        return map

    def load_phrases(self, file):
        return Phrases(self.request.locale, file)


class Phrases():

    def __init__(self, locale, phrase_file):

        self.locale = locale
        self.load_phrase_file(phrase_file)

    def load_phrase_file(self, file):

        with open(file) as f:
            self.phrases = json.load(f)
        self.phrases = self.phrases['phrases']

    def load_phrase(self, phrase_section, phrase_key, **string_args):

        section = self.phrases[phrase_section]
        phrase_variations = section[phrase_key]

        if self.locale in phrase_variations.keys():
            phrase = phrase_variations[self.locale]
        else:
            phrase = phrase_variations['default']

        if type(phrase) is list:
            return random.choice(phrase).format(**string_args)

        return phrase.format(**string_args)

    def phrase(self, phrase_section, phrase_key, **string_args):
        return self.load_phrase(phrase_section, phrase_key, **string_args)


class Session():
    """Session class.

    Used to represent both the incoming session and the session to send with a response.
    """

    def __init__(self, raw=None):
        """Init method."""
        self.attributes = {}  # Define attributes attribute as an empty dict
        self.user = None  # Define a user attribute to None to store user info later

        if raw is not None:  # Confirm a event has been passed in
            if "session" in raw.keys():  # Check if the event has a session key
                # If it does, set a raw_session attribue to the value of the event's session objet
                self.raw_session = raw['session']

                self.context = raw.get('context', None)
                if self.context:
                    self.device_id = self.context['System']['device']['deviceId']

            else:
                self.raw_session = raw  # If not, assume the whole event is a session and set the raw_Session to the whole event

            self._get_attributes()  # Parse passed in session attributes

    def _get_attributes(self):
        """Get attributes.

        Used to get the session attributes passed in with the event
        Used to get the user details passed in with the event
        """
        if self.raw_session:  # Check if there is a raw session value
            if 'attributes' in self.raw_session:  # See if the raw session has n attributes key
                if self.raw_session['attributes'] is not None:  # Check if the attributes key is not empty/None
                    # Set the attributes class attribute to the value of the session attributes
                    self.attributes = self.raw_session['attributes']
                else:
                    self.attributes = {}  # If there is an empty attributes key, set class attributes attribute to an empty dict
            else:
                self.attributes = {}  # IF there is no attributes key, set class attributes attribute to an empty dict

            # Check if there is a user key in the raw session
            if 'user' in self.raw_session:
                # If there is, set class user attribute to the value of the session object
                self.user = self.raw_session['user']
                if 'permissions' in self.user:
                    if self.user['permissions']:
                        self.permissions = self.user['permissions']
                        self.get_user_location()
        else:
            self.attributes = self.raw_session  # If there is no attributes key, assume of the raw_session is the attributes dict

    def set_attribute(self, key=None, value=None):
        """Set attributes.

        Used to set attribute values to send back to the Echo/Alexa
        Takes in a key and a value to set
        """
        if key:  # If the key is not none
            self.attributes[key] = value  # Set the value of the attribute key to the key value

    def get_user_location(self):
        
        if self.permissions:
            # if it is, check if we have a consent token
            if 'consentToken' in self.permissions:
                
                token = self.permissions['consentToken']  # Get token from the session

                # Create headers for the address API
                headers = {
                    "Authorization": "Bearer {}".format(token)
                }

                # Setup request to the Alexa Address api passing in Device Id and headers
                response = requests.get(
                     'https://api.eu.amazonalexa.com/v1/devices/{}/settings/address'.format(
                         self.device_id
                     ),
                     headers=headers
                )

            self.location = json.loads(response.text)  # Get the location from the response
            return self.location
            
        return None


class Response():
    """Response class."""

    def __init__(self, title):
        """Init Method."""
        self.skill_title = title  # Set the skill title attribute to the passed in title argument
        self.attributes = {}  # Create an empty dict for attributes
        self.session = Session()  # Create a new session to use when sending the response
        self.final_response = {  # Create start of the response object
            "version": "1.0",
            "response": {}
        }

    def link_account(self):
        self.final_response['response']['card'] = {
            "type": "LinkAccount"
        }

    def card(self, text, title=None, image=None, permissions=None,):
        """Create a card response.

        Allows a card to be sent as part of the response. This will show up in the users Alexa app
        Accepts text input at a minimum and allow images to be set

        If a single image string is provided, this will be used for both small and large settings
        Additionally, you can pass in a dict with small and large as keys with alternate URLs
        """
        # If image is set
        if not title:
            title = self.skill_title

        if permissions is not None:
            self.final_response['response']['card'] = {
                "type": "AskForPermissionsConsent",
                "permissions": [
                    "read::alexa:device:all:address"
                ]
            }

            return self.final_response

        if image:
            card_img = {}  # Create empty image dict for the respone
            if type(image) is dict:  # Check if the image argument was a dict
                if 'small' in image:  # See if small is provided in the argument
                    card_img['smallImageUrl'] = image['small']  # Set the smallImageUrl to the small value

                if 'large' in image:
                    card_img['largeImageUrl'] = image['large']  # Set the largeImageUrl to the large value
            elif type(image) is str:  # Check if the type is str
                card_img = {  # Create a dict with small and large image url set to the string value
                    "smallImageUrl": image,
                    "largeImageUrl": image
                }

            # set the response card value to the values in the image_carg
            self.final_response['response']['card'] = {
                "type": "Standard",
                "title": title,
                "text": text,
                "image": card_img
            }

        else:  # If no image is set
            # Create a response card object reflective of no image being se
            self.final_response['response']['card'] = {
                "type": "Simple",  # Card type
                "title": title,  # Card title
                "content": text  # Content dict
            }

    # Statement method
    def statement(self, raw, style='ssml'):
        """Statement class.

        Used to return a response that doesn't expect further input
        """
        styles = {
            "text": "PlainText",  # Response type PlainText
            "ssml": "SSML"  # Response type SSML
        }

        # Check if the style argument is in the styles dict
        if style in styles.keys():

            if style == 'ssml':  # If the style is SSML
                response = "<speak>{}</speak>".format(raw)  # Response is surrounded by speak tags to make it SSML
            else:
                response = raw  # Else the Response is just the input of raw
            # End session set to True as this is a statement, not a question
            self.final_response['response']['shouldEndSession'] = True

            # Create outputspeech dict with response and styl
            self.final_response['response']['outputSpeech'] = {
                "type": styles[style],  # Style value is value from styles dict using passed in style argument
                style: response  # Set key to the style passed in and the response as the value
            }

            # Set Repromt dict to None
            self.final_response['response']['reprompt'] = {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": None
                }
            }

        else:
            # If the style is invalid, return a sad face response
            self.final_response['response']['outputSpeech'] = {
                "type": "PlainText",
                "text": "There was was an issue. Sad face."
            }
        self.final_response['response']['directives'] = None
        return self.get_output()  # Get the output and return it

    def confirm(self, raw, slot, intent, style='ssml'):
        """Statement class.

        Used to return a response that doesn't expect further input
        """
        styles = {
            "text": "PlainText",  # Response type PlainText
            "ssml": "SSML"  # Response type SSML
        }

        # Check if the style argument is in the styles dict
        if style in styles.keys():

            if style == 'ssml':  # If the style is SSML
                response = "<speak>{}</speak>".format(raw)  # Response is surrounded by speak tags to make it SSML
            else:
                response = raw  # Else the Response is just the input of raw
            # End session set to True as this is a statement, not a question
            self.final_response['response']['shouldEndSession'] = True

            # Create outputspeech dict with response and styl
            self.final_response['response']['outputSpeech'] = {
                "type": styles[style],  # Style value is value from styles dict using passed in style argument
                style: response  # Set key to the style passed in and the response as the value
            }

            # Set Repromt dict to None
            self.final_response['response']['reprompt'] = {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": None
                }
            }

        else:
            # If the style is invalid, return a sad face response
            self.final_response['response']['outputSpeech'] = {
                "type": "PlainText",
                "text": "There was was an issue. Sad face."
            }

        self.final_response['response']['directives'] = [
            {
                "type": "Dialog.ConfirmSlot",
                "slotToConfirm": slot,
                "updatedIntent": intent.to_json()
            }
        ]
        self.final_response['response']['shouldEndSession'] = False
        return self.get_output()  # Get the output and return it

    def ellicit_dialog(self, raw, slot, intent, style='ssml'):
        """Statement class.

        Used to return a response that doesn't expect further input
        """
        styles = {
            "text": "PlainText",  # Response type PlainText
            "ssml": "SSML"  # Response type SSML
        }

        # Check if the style argument is in the styles dict
        if style in styles.keys():

            if style == 'ssml':  # If the style is SSML
                response = "<speak>{}</speak>".format(raw)  # Response is surrounded by speak tags to make it SSML
            else:
                response = raw  # Else the Response is just the input of raw
            # End session set to True as this is a statement, not a question
            self.final_response['response']['shouldEndSession'] = True

            # Create outputspeech dict with response and styl
            self.final_response['response']['outputSpeech'] = {
                "type": styles[style],  # Style value is value from styles dict using passed in style argument
                style: response  # Set key to the style passed in and the response as the value
            }

            # Set Repromt dict to None
            self.final_response['response']['reprompt'] = {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": None
                }
            }

        else:
            # If the style is invalid, return a sad face response
            self.final_response['response']['outputSpeech'] = {
                "type": "PlainText",
                "text": "There was was an issue. Sad face."
            }

        self.final_response['response']['directives'] = [
            {
                "type": "Dialog.ElicitSlot",
                "slotToElicit": slot,
                "updatedIntent": intent.to_json()
            }
        ]
        self.final_response['response']['shouldEndSession'] = False
        return self.get_output()  # Get the output and return it

    def dialog(self):
        """Dialog Method.

        Used to return a A Dialog Delegate directive
        """

        self.final_response['response'] = {
            'shouldEndSession': False,
            'directives': [
                {
                    "type": "Dialog.Delegate"
                }
            ]
        }

        return self.get_output()  # Get the output and return it

    # question method used to return a response that expects user input
    def question(self, raw, style='ssml'):
        """Question method."""
        styles = {
            "text": "PlainText",
            "ssml": "SSML"
        }
        # If the style is SSML
        if style in styles.keys():

            if style == 'ssml':  # If the style is SSML
                response = "<speak>{}</speak>".format(raw)  # Response is surrounded by speak tags to make it SSML
            else:
                response = raw  # Else the Response is just the input of raw
            # End session set to False as this is a question, expecting further input
            self.final_response['response']['shouldEndSession'] = False
            self.final_response['response']['outputSpeech'] = {
                "type": styles[style],  # Style value is value from styles dict using passed in style argument
                style: response  # Set key to the style passed in and the response as the value
            }

            self.final_response['response']['reprompt'] = {
                "outputSpeech": {
                    "type": "PlainText",  # Set the type to PlainText
                    "text": "How can I help?"  # Set the text to reprompt for (Need to add custom raw_input)
                }
            }

        else:
            # If the style is invalid, return a sad face response
            self.final_response['response']['outputSpeech'] = {
                "type": "PlainText",
                "text": "There was was an issue. Sad face."
            }
        self.final_response['response']['directives'] = None
        # Get the output and return it
        return self.get_output()

    def set_attribute(self, key=None, value=None):
        """Set attributes.

        Used to set attribute values to send back to the Echo/Alexa
        Takes in a ket and a value to set
        """
        if key:
            self.attributes[key] = value

    # Get output to send back
    def get_output(self):
        """Get response."""
        self.set_session(self.session)  # Sets the session to the passed in session
        return self.final_response  # Return the final response

    # Set the session to send back
    def set_session(self, session):
        """Set session method."""
        if bool(self.session.attributes):  # Check if session attributes is set
            self.final_response['sessionAttributes'] = session.attributes  # Add sesison attributes to final response


class Intent():

    def __init__(self, raw, type):

        self.raw = raw
        self.type = type

        if raw:
            self.slots = raw.get('slots', None)
            self.name = raw['name']
            self.confirmed = raw['confirmationStatus']

            if self.confirmed.lower() == "none":
                self.confirmed = None
            elif self.confirmed.lower() == "denied":
                self.confirmed = False
            elif self.confirmed.lower() == "confirmed":
                self.confirmed = True

    def to_json(self):
        return self.raw


class Slot():

    def __init__(self, raw):

        self.raw = raw
        self.name = raw.get('name', None)

        self.value = raw.get('value', None)
        self.resolutions = raw.get('resolutions', None)
        self.confirmed = raw.get('confirmationStatus', None)
        if self.confirmed:
            if self.confirmed.lower() == "none":
                self.confirmed = None
            elif self.confirmed.lower() == "denied":
                self.confirmed = False
            elif self.confirmed.lower() == "confirmed":
                self.confirmed = True

    def to_json(self):
        return self.raw


class Request():
    """Request class."""

    def __init__(self, raw):
        """Init method."""
        self.type = None  # Request type
        self.intent = None  # The intent name
        self.slots = None  # Slots provided by request
        self.user = None  # User in the request
        self.args = {}  # Empty args dict
        self.datetime_format = "%Y-%m-%dT%H:%M:%SZ"
        self.time_format = "%H:%M:%SZ"
        # Check if request is in the event
        if "request" in raw.keys():
            self.raw_request = raw['request']  # Set the request attribute to the request object in the event
            self.locale = raw['request']['locale']

            self.set_timestamp()

        else:
            self.raw_request = raw  # Else set raw_requsto entire event

        self._get_request()  # Call the get request method

    def set_timestamp(self):

        raw_time = self.raw_request['timestamp']
        self.datetime = datetime.strptime(raw_time, self.datetime_format)
        hour = self.datetime.hour

        if hour > 3 and hour < 12:
            self.time_friendly = "morning"
        elif hour >= 12 and hour <= 16:
            self.time_friendly = "afternoon"
        elif hour >= 17 and hour <= 20:
            self.time_friendly = "evening"
        else:
            self.time_friendly = "night"

    def _get_request(self):
        """Get request attributes."""
        # Check raw_request exists
        if self.raw_request:
            self.type = self.raw_request['type']  # Set type
            if self.type == 'IntentRequest':  # Check if type is IntentRequest
                self.intent = Intent(self.raw_request['intent'], self.raw_request['type'])   # Set intent to intent name
                self.slots = {}  # Set empty slots dict
                if 'slots' in self.raw_request['intent'].keys():  # Check if slots is in the request keys

                    # Loop through each slot in the request
                    for k, slot in self.raw_request[
                        'intent'
                    ]['slots'].items():
                        self.slots[slot['name']] = Slot(slot)

                    self.args['slots'] = self.slots  # Set the object args slots key to the slots
            else:
                # Set intent to request ype if it is not IntentRequest
                self.intent = Intent({}, self.raw_request['type'])

        else:
            self.attributes = self.raw_session  # Set attributes to the raw session if no raw_request